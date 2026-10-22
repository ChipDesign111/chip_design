"""Small technology-independent fault-injection checks for the evidence audit.

These tests do not run EDA or validate the SoC itself. Generated fake cells and
rails exercise detection of lost pins, old coordinates, misplaced cells, PG
binding errors and modified artifacts. gdstk is required for the native-rail
portion, just as it is for the real audit.
"""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

import gdstk


spec = importlib.util.spec_from_file_location("physical_audit", Path(__file__).with_name("audit_physical.py"))
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def fixture(root, die=3400):
    units = 2000
    cfg = {"pre_io_netlist": "pre.v", "post_io_netlist": "post.v", "final_netlist": "final.v", "def": "final.def",
           "lef_files": ["cells.lef"], "native_io_gds": "io.gds", "placement_report": "place.rpt",
           "special_connectivity_report": "pg.rpt", "signal_connectivity_report": "signal.rpt", "route_drc_report": "drc.rpt"}
    masters = {"DF": ((.56, 3.92), "CORE", {"VDD": "POWER", "VSS": "GROUND"}),
               "TIEHBWP7T": ((.56, 3.92), "CORE", {"VDD": "POWER", "VSS": "GROUND"}),
               "TIELBWP7T": ((.56, 3.92), "CORE", {"VDD": "POWER", "VSS": "GROUND"}),
               "RA1SHD_2048x32M8": ((554.595, 723.85), "BLOCK", {"VDD": "POWER", "VSS": "GROUND"}),
               "PDDW0204CDG": ((60, 115), "PAD", {"VDDPST": "POWER", "VSSPST": "GROUND"}),
               "PVDD1CDG": ((60, 115), "PAD", {"VDD": "POWER"}),
               "PVSS1CDG": ((60, 115), "PAD", {"VSS": "GROUND"}),
               "PVDD2CDG": ((60, 115), "PAD", {"VDDPST": "POWER"}),
               "PVSS2CDG": ((60, 115), "PAD", {"VSSPST": "GROUND"}),
               "PCORNER": ((115, 115), "ENDCAP", {}), "PAD60LU_OBV": ((60, 73.16), "COVER", {})}
    components = []
    pad_boxes = {}
    side_pads = {s: [] for s in "NSWE"}
    for port, (pad, direction, side) in audit.SIGNALS.items():
        side_pads[side].append((pad, "PDDW0204CDG", port))
    for supply, master in (("VDD", "PVDD1CDG"), ("VSS", "PVSS1CDG"), ("VDDPST", "PVDD2CDG"), ("VSSPST", "PVSS2CDG")):
        side_pads["N"].append(("power_"+supply, master, supply))
    for side in "NSWE":
        start = 115
        for name, master, port in side_pads[side]:
            x, y = (start, 0 if side == "S" else die-115) if side in "NS" else (0 if side == "W" else die-115, start)
            orient = {"S": "N", "N": "S", "W": "E", "E": "W"}[side]
            components.append((name, master, x, y, orient))
            pad_boxes[port] = (x, y, side)
            bx, by = (start, 0 if side == "S" else die-73.16) if side in "NS" else (0 if side == "W" else die-73.16, start)
            components.append(("bond_"+name, "PAD60LU_OBV", bx, by, orient))
            start += 60
        fill = "PFILLER_"+side
        masters[fill] = ((die-115-start, 115), "PAD SPACER", {})
        x, y = (start, 0 if side == "S" else die-115) if side in "NS" else (0 if side == "W" else die-115, start)
        components.append(("fill_"+side, fill, x, y, {"S": "N", "N": "S", "W": "E", "E": "W"}[side]))
    components += [("corner_SW", "PCORNER", 0, 0, "N"), ("corner_SE", "PCORNER", die-115, 0, "FN"),
                   ("corner_NW", "PCORNER", 0, die-115, "FS"), ("corner_NE", "PCORNER", die-115, die-115, "S"),
                   ("i_mainmem/i_sram/i_macro", "RA1SHD_2048x32M8", 800, 900, "N")]
    components += [("core_"+p, "DF", 150.08+i*.56, 150.08, "N") for i, p in enumerate(audit.SIGNALS)]
    components += [("tie_H", "TIEHBWP7T", 153.44, 150.08, "N"), ("tie_L", "TIELBWP7T", 154, 150.08, "N")]
    header = "module my_soc_top(" + ",".join(audit.SIGNALS) + ");\n"
    before = header+"\n".join(f"DF core_{p} (.P({p}), .VDD(VDD), .VSS(VSS));" for p in audit.SIGNALS)+"\nendmodule\n"
    after = header
    for p, (pad, direction, side) in audit.SIGNALS.items():
        after += f"DF core_{p} (.P(core_{p}_net), .VDD(VDD), .VSS(VSS));\n"
        out = direction == "output"
        after += f"PDDW0204CDG {pad} (.PAD({p}), .C({'unused_output' if out else 'core_'+p+'_net'}), .I({'core_'+p+'_net' if out else 'low'}), .OEN({'low' if out else 'high'}), .IE({'low' if out else 'high'}), .PE(low), .DS(low));\n"
    after += "TIEHBWP7T tie_H (.Z(high));\nTIELBWP7T tie_L (.ZN(low));\n"
    # These physical supply PADs exist in DEF and must also have the explicit
    # supply connections emitted by the real physical netlist exporter.
    for supply, master in (("VDD", "PVDD1CDG"), ("VSS", "PVSS1CDG"), ("VDDPST", "PVDD2CDG"), ("VSSPST", "PVSS2CDG")):
        after += f"{master} power_{supply} (.{supply}({supply}));\n"
    after += "endmodule\n"
    (root/"pre.v").write_text(before)
    (root/"post.v").write_text(after)
    (root/"final.v").write_text(after)
    lef = "SITE core7T\n CLASS CORE ;\n SIZE .56 BY 3.92 ;\nEND core7T\n"
    for master, ((w, h), clas, pins) in masters.items():
        lef += f"MACRO {master}\n CLASS {clas} ;\n SIZE {w} BY {h} ;\n"
        lef += "".join(f" PIN {p}\n  USE {use} ;\n END {p}\n" for p, use in pins.items())
        lef += f"END {master}\n"
    (root/"cells.lef").write_text(lef)
    d = f"VERSION 5.8 ;\nDESIGN my_soc_top ;\nUNITS DISTANCE MICRONS {units} ;\n"
    for key, value in (("LL_X", 150.08), ("LL_Y", 150.08), ("UR_X", die-150.08), ("UR_Y", die-150.08)):
        d += f" DESIGN FE_CORE_BOX_{key} REAL {value} ;\n"
    d += f"DIEAREA ( 0 0 ) ( {round(die*units)} {round(die*units)} ) ;\n"
    d += "ROW row0 core7T 300160 300160 N DO 100 BY 1 STEP 1120 0 ;\n"
    d += f"COMPONENTS {len(components)} ;\n"
    for name, master, x, y, orient in components:
        d += f"- {name} {master} + FIXED ( {round(x*units)} {round(y*units)} ) {orient} ;\n"
    d += "END COMPONENTS\nPINS 10 ;\n"
    for port in list(audit.SIGNALS)+list(audit.SUPPLIES):
        x, y, side = pad_boxes[port]
        px, py = x+15, die-1.5 if side == "N" else 1.5
        direction = audit.SIGNALS[port][1].upper() if port in audit.SIGNALS else "INOUT"
        use = audit.SUPPLIES.get(port, "SIGNAL")
        d += f"- {port} + NET {port} + DIRECTION {direction} + USE {use}\n + LAYER METAL4 ( -10000 -1000 ) ( 10000 1000 ) + FIXED ( {round(px*units)} {round(py*units)} ) N ;\n"
    d += "END PINS\nNETS 12 ;\n"
    for port, (pad, direction, side) in audit.SIGNALS.items():
        d += f"- {port} ( PIN {port} ) ( {pad} PAD ) ;\n"
        d += f"- core_{port}_net ( {pad} {'I' if direction == 'output' else 'C'} ) ( core_{port} P ) ;\n"
    d += "END NETS\nSPECIALNETS 4 ;\n"
    for supply in audit.SUPPLIES:
        d += f"- {supply} ( * {supply} ) ( PIN {supply} ) + USE {audit.SUPPLIES[supply]} ;\n"
    d += "END SPECIALNETS\nEND DESIGN\n"
    (root/"final.def").write_text(d)
    (root/"place.rpt").write_text("set pchkIoOverlapList [list {i_pad_clk}]\nNumber of Unplaced Instances = 0\n")
    (root/"pg.rpt").write_text("Found no problems or warnings.\n")
    (root/"signal.rpt").write_text("Found no problems or warnings.\n")
    (root/"drc.rpt").write_text("No DRC violations were found\n")
    lib = gdstk.Library()
    for master, ((w, h), clas, pins) in masters.items():
        if master.startswith("PFILLER") or master in {"PDDW0204CDG", "PVDD1CDG", "PVSS1CDG", "PVDD2CDG", "PVSS2CDG"}:
            c = lib.new_cell(master)
            for y in (20.95, 63.92):
                c.add(gdstk.rectangle((0, y-.1), (w, y+.1), layer=31))
    corner = lib.new_cell("PCORNER")
    for y in (20.95, 63.92):
        corner.add(gdstk.rectangle((y-.1, y-.1), (115, y+.1), layer=31))
        corner.add(gdstk.rectangle((y-.1, y-.1), (y+.1, 115), layer=31))
    lib.write_gds(root/"io.gds")
    cfg["stage_artifacts"] = [{"label": n, "path": n, "sha256": audit.digest(root/n)} for n in ("pre.v", "post.v", "final.v", "final.def")]
    (root/"config.json").write_text(json.dumps(cfg))
    return cfg


class PhysicalAuditTests(unittest.TestCase):
    def setUp(self):
        self.workspace = Path(__file__).resolve().parents[1] / "work" / "physical-audit-selftest"
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=self.workspace)
        self.root = Path(self.temp.name)
        self.cfg = fixture(self.root)

    def tearDown(self):
        assert self.workspace.resolve() in self.root.resolve().parents
        self.temp.cleanup()

    def run_audit(self):
        return audit.run(self.root/"config.json")

    def change(self, file, old, new):
        path = self.root/file
        text = path.read_text()
        self.assertIn(old, text)
        path.write_text(text.replace(old, new, 1))

    def refreeze_fixture(self):
        # Only synthetic data deliberately changed by a positive test. The
        # production audit configuration and historical hashes are untouched.
        for item in self.cfg["stage_artifacts"]:
            item["sha256"] = audit.digest(self.root/item["path"])
        (self.root/"config.json").write_text(json.dumps(self.cfg))

    def hierarchical_clock_pair(self):
        before = (self.root/"pre.v").read_text().replace(
            "DF core_clk_i (.P(clk_i), .VDD(VDD), .VSS(VSS));",
            "CLOCK_BRANCH core_clk_i (.clk_i(clk_i));")
        after = (self.root/"post.v").read_text().replace(
            "DF core_clk_i (.P(core_clk_i_net), .VDD(VDD), .VSS(VSS));",
            "CLOCK_BRANCH core_clk_i (.clk_i(clk_i), .__asic_core_clk_i(core_clk_i_net));")
        before += """module CLOCK_BRANCH (clk_i);
input clk_i;
wire local_clock;
CLOCK_PASS gate (.clk_i(clk_i), .clk_o(local_clock));
DF leaf (.P(local_clock));
endmodule
"""
        after += """module CLOCK_BRANCH (clk_i, __asic_core_clk_i);
input clk_i, __asic_core_clk_i;
wire local_clock;
CLOCK_PASS gate (.clk_i(__asic_core_clk_i), .clk_o(local_clock));
DF leaf (.P(local_clock));
endmodule
"""
        transparent = """module CLOCK_PASS (clk_i, clk_o);
input clk_i;
output clk_o;
assign clk_o = clk_i;
endmodule
"""
        return before+transparent, after+transparent

    def test_complete_synthetic_evidence(self):
        result = self.run_audit()
        self.assertEqual(result["status"], "PASS", result)
        self.assertEqual(result["checks"]["IO_ring_and_bond_geometry"]["details"]["ordinary_pad_count"], 10)

    def test_different_die_and_pad_counts_do_not_reuse_template(self):
        fixture(self.root, 3600.4)
        self.assertEqual(self.run_audit()["status"], "PASS")

    def test_lost_original_core_pin_is_detected(self):
        self.change("post.v", ".P(core_clk_i_net)", ".P(disconnected)")
        result = self.run_audit()
        self.assertEqual(result["checks"]["post_IO_pin_preservation"]["status"], "FAIL")

    def test_tie_polarity_is_checked(self):
        self.change("final.v", "TIEHBWP7T tie_H (.Z(high))", "TIELBWP7T tie_H (.ZN(high))")
        self.assertEqual(self.run_audit()["checks"]["final_PAD_connections_and_ties"]["status"], "FAIL")

    def test_old_macro_hierarchy_is_rejected(self):
        self.change("final.def", "i_mainmem/i_sram/i_macro", "i_mainmem/i_mainmem")
        self.assertEqual(self.run_audit()["checks"]["core_rows_macro_and_legal_placement"]["status"], "FAIL")

    def test_ordinary_cell_overlap_is_rejected(self):
        self.change("final.def", "core_rst_ni DF + FIXED ( 301280 300160 )", "core_rst_ni DF + FIXED ( 300160 300160 )")
        self.assertEqual(self.run_audit()["checks"]["core_rows_macro_and_legal_placement"]["status"], "FAIL")

    def test_old_die_IO_coordinates_are_rejected(self):
        self.change("final.def", "DIEAREA ( 0 0 ) ( 6800000 6800000 )", "DIEAREA ( 0 0 ) ( 7000000 7000000 )")
        self.assertEqual(self.run_audit()["checks"]["IO_ring_and_bond_geometry"]["status"], "FAIL")

    def test_missing_native_rail_binding_is_rejected(self):
        self.change("final.def", "( * VDDPST )", "( missing VDDPST )")
        self.assertEqual(self.run_audit()["checks"]["DEF_signal_and_power_bindings"]["status"], "FAIL")

    def test_native_rail_gap_is_rejected(self):
        lib = gdstk.read_gds(self.root/"io.gds")
        cell = next(c for c in lib.cells if c.name == "PDDW0204CDG")
        cell.remove(*cell.polygons)
        cell.add(gdstk.rectangle((1, 20.85), (60, 21.05), layer=31))
        cell.add(gdstk.rectangle((0, 63.82), (60, 64.02), layer=31))
        lib.write_gds(self.root/"io.gds")
        self.assertEqual(self.run_audit()["checks"]["native_IO_power_rail_geometry"]["status"], "FAIL")

    def test_changed_artifact_is_rejected_even_if_still_parseable(self):
        with (self.root/"final.v").open("a") as f:
            f.write("// harmless content change still invalidates frozen identity\n")
        self.assertEqual(self.run_audit()["checks"]["frozen_stage_artifact_hashes"]["status"], "FAIL")

    def test_named_native_rail_limit_is_not_a_blanket_waiver(self):
        self.cfg["native_io_unrouted_net_allowlist"] = ["VDDPST", "VSSPST"]
        (self.root/"config.json").write_text(json.dumps(self.cfg))
        (self.root/"signal.rpt").write_text("Net VDDPST: no routing\nNet VSSPST: no routing\n2 Problem(s) (IMPVFC-98): Net has no global routing and no special routing.\n")
        self.assertEqual(self.run_audit()["status"], "PASS")
        with (self.root/"signal.rpt").open("a") as f:
            f.write("1 Problem(s) (OTHER): real disconnection\n")
        self.assertEqual(self.run_audit()["checks"]["tool_physical_reports"]["status"], "FAIL")

    def test_unused_old_formal_and_transparent_clock_wrapper_preserve_leaf(self):
        before, after = self.hierarchical_clock_pair()
        old = audit.parse_verilog(before, "my_soc_top")
        new = audit.parse_verilog(after, "my_soc_top")
        expected = {(("core_clk_i", "leaf"), "P", "DF")}
        self.assertEqual(old.leaf_pins("clk_i"), expected)
        self.assertEqual(new.leaf_pins("core_clk_i_net", exclude=("i_pad_clk",)), expected)
        self.assertEqual(new.leaf_pins("clk_i", exclude=("i_pad_clk",)), set())
        self.assertEqual(audit.audit_pad_connections(old, new, {})["clk_i"]["preserved_core_pin_count"], 1)
        audit.audit_final_pads(new, {})

    def test_renamed_formal_does_not_waive_a_real_leaf_loss(self):
        before, after = self.hierarchical_clock_pair()
        after = after.replace("DF leaf (.P(local_clock));", "DF leaf (.P(disconnected));")
        with self.assertRaisesRegex(AssertionError, "lost"):
            audit.audit_pad_connections(audit.parse_verilog(before, "my_soc_top"), audit.parse_verilog(after, "my_soc_top"), {})

    def test_same_leaf_pin_count_with_changed_leaf_identity_is_rejected(self):
        before, after = self.hierarchical_clock_pair()
        after = after.replace("DF leaf (.P(local_clock));", "DF replacement_leaf (.P(local_clock));")
        with self.assertRaisesRegex(AssertionError, "lost.*added"):
            audit.audit_pad_connections(audit.parse_verilog(before, "my_soc_top"), audit.parse_verilog(after, "my_soc_top"), {})

    def test_live_external_formal_bypasses_pad_even_when_core_side_still_works(self):
        _, after = self.hierarchical_clock_pair()
        after = after.replace("DF leaf (.P(local_clock));", "DF leaf (.P(local_clock));\nDF bypass (.P(clk_i));")
        with self.assertRaisesRegex(AssertionError, "core bypasses PAD"):
            audit.audit_final_pads(audit.parse_verilog(after, "my_soc_top"), {})

    def test_equal_local_net_names_in_distinct_modules_are_not_global_aliases(self):
        _, after = self.hierarchical_clock_pair()
        after = after.replace("endmodule", "OTHER_BRANCH unrelated (.clk_i(unrelated_clock));\nendmodule", 1)
        after += """module OTHER_BRANCH (clk_i);
input clk_i;
wire local_clock;
assign local_clock = clk_i;
DF extra (.P(local_clock));
endmodule
"""
        parsed = audit.parse_verilog(after, "my_soc_top")
        self.assertEqual(parsed.leaf_pins("core_clk_i_net", exclude=("i_pad_clk",)), {(("core_clk_i", "leaf"), "P", "DF")})

    def test_constant_equal_formals_do_not_merge_independent_parent_wires(self):
        text = """module my_soc_top (first, second);
DUAL_CONSTANT wrapper (.a(first), .b(second));
endmodule
module DUAL_CONSTANT (a, b);
input a, b;
assign a = 1'b0;
assign b = 1'b0;
endmodule
"""
        parsed = audit.parse_verilog(text, "my_soc_top")
        _, find = parsed
        self.assertNotEqual(find("first"), find("second"))

    def test_duplicate_instance_or_pin_is_rejected(self):
        for body in ("DF same (.P(a));\nDF same (.P(b));", "DF same (.P(a), .P(b));"):
            with self.subTest(body=body), self.assertRaisesRegex(AssertionError, "Duplicate"):
                audit.parse_verilog("module my_soc_top (a, b);\n"+body+"\nendmodule", "my_soc_top")

    def test_leaf_library_stub_does_not_hide_physical_endpoints(self):
        before, after = self.hierarchical_clock_pair()
        stub = "module DF (P, VDD, VSS);\ninput P, VDD, VSS;\nendmodule\n"
        old, new = [audit.parse_verilog(text+stub, "my_soc_top") for text in (before, after)]
        old.leaf_masters = new.leaf_masters = {"DF"}
        self.assertEqual(audit.audit_pad_connections(old, new, {})["clk_i"]["preserved_core_pin_count"], 1)

    def test_selected_vector_connection_is_rejected_in_scalar_leaf_trace(self):
        _, after = self.hierarchical_clock_pair()
        after = after.replace("DF leaf (.P(local_clock));", "DF leaf (.P(local_clock[0]));")
        with self.assertRaisesRegex(AssertionError, "Cannot safely trace"):
            audit.audit_final_pads(audit.parse_verilog(after, "my_soc_top"), {})

    def test_antenna_overlay_preserves_ring_macro_class_bond_and_pg_use(self):
        self.change("cells.lef", "MACRO RA1SHD_2048x32M8\n CLASS BLOCK", "MACRO RA1SHD_2048x32M8\n CLASS RING")
        self.change("cells.lef", "MACRO PAD60LU_OBV\n CLASS COVER", "MACRO PAD60LU_OBV\n CLASS BLOCK")
        overlay = """MACRO RA1SHD_2048x32M8
 PIN VDD
  ANTENNAGATEAREA 0.12 ;
 END VDD
END RA1SHD_2048x32M8
MACRO PVDD2CDG
 PIN VDDPST
  ANTENNAGATEAREA 0.12 ;
 END VDDPST
END PVDD2CDG
"""
        (self.root/"antenna.lef").write_text(overlay)
        self.cfg["lef_files"].append("antenna.lef")
        (self.root/"config.json").write_text(json.dumps(self.cfg))
        macros, _ = audit.parse_lefs([(self.root/"cells.lef").read_text(), overlay])
        self.assertEqual(macros["RA1SHD_2048x32M8"]["class"], "RING")
        self.assertEqual(macros["RA1SHD_2048x32M8"]["pins"]["VDD"], "POWER")
        self.assertEqual(macros["PVDD2CDG"]["class"], "PAD")
        self.assertEqual(macros["PVDD2CDG"]["pins"]["VDDPST"], "POWER")
        self.assertEqual(self.run_audit()["status"], "PASS")

    def test_conflicting_overlay_size_class_or_use_is_rejected(self):
        base = (self.root/"cells.lef").read_text()
        for declaration, reason in (("SIZE 1 BY 1 ;", "size mismatch"),
                                    ("CLASS CORE ;", "class mismatch"),
                                    ("PIN VDD\n USE GROUND ;\n END VDD", "USE mismatch")):
            with self.subTest(declaration=declaration):
                overlay = f"MACRO RA1SHD_2048x32M8\n {declaration}\nEND RA1SHD_2048x32M8\n"
                with self.assertRaisesRegex(AssertionError, reason):
                    audit.parse_lefs([base, overlay])

    def test_ring_sram_does_not_allow_an_extra_real_block(self):
        self.change("cells.lef", "MACRO RA1SHD_2048x32M8\n CLASS BLOCK", "MACRO RA1SHD_2048x32M8\n CLASS RING")
        self.change("final.def", "END COMPONENTS", "- extra_sram RA1SHD_2048x32M8 + FIXED ( 2000000 2000000 ) N ;\nEND COMPONENTS")
        result = self.run_audit()
        self.assertIn("Wrong block instances", result["checks"]["core_rows_macro_and_legal_placement"]["error"])

    def test_required_macro_halo_is_not_waived_by_classification_fix(self):
        self.change("final.def", "i_mainmem/i_sram/i_macro RA1SHD_2048x32M8 + FIXED ( 1600000 1800000 )",
                    "i_mainmem/i_sram/i_macro RA1SHD_2048x32M8 + FIXED ( 300160 1800000 )")
        failed = self.run_audit()["checks"]["core_rows_macro_and_legal_placement"]
        self.assertEqual(failed["status"], "FAIL")
        self.assertIn("Macro halo outside core", failed["error"])

    def test_only_configured_bond_master_is_excluded_from_core_blocks(self):
        self.change("cells.lef", "MACRO PAD60LU_OBV\n CLASS COVER", "MACRO PAD60LU_OBV\n CLASS BLOCK")
        self.cfg["bond_master"] = "SOME_OTHER_BOND"
        (self.root/"config.json").write_text(json.dumps(self.cfg))
        self.assertEqual(self.run_audit()["checks"]["core_rows_macro_and_legal_placement"]["status"], "FAIL")

    def test_nets_specialnets_merge_retains_native_supply_terminals(self):
        self.change("final.def", "END NETS", "- VDDPST ( power_VDDPST VDDPST ) ;\nEND NETS")
        data = audit.parse_def((self.root/"final.def").read_text())
        net = data["nets"]["VDDPST"]
        self.assertEqual(set(net["sections"]), {"NETS", "SPECIALNETS"})
        self.assertIn(("power_VDDPST", "VDDPST"), net["connections"])
        self.assertIn(("*", "VDDPST"), net["connections"])
        self.refreeze_fixture()
        self.assertEqual(self.run_audit()["status"], "PASS")

    def test_same_section_duplicate_net_is_rejected(self):
        self.change("final.def", "END NETS", "- clk_i ( PIN clk_i ) ;\nEND NETS")
        with self.assertRaisesRegex(AssertionError, "Duplicate net entry"):
            audit.parse_def((self.root/"final.def").read_text())

    def test_native_signal_supply_requires_def_and_matching_final_hdl(self):
        self.change("cells.lef", "MACRO PVDD2CDG\n CLASS PAD ;\n SIZE 60 BY 115 ;\n PIN VDDPST\n  USE POWER", "MACRO PVDD2CDG\n CLASS PAD ;\n SIZE 60 BY 115 ;\n PIN VDDPST\n  USE SIGNAL")
        self.refreeze_fixture()
        self.assertEqual(self.run_audit()["status"], "PASS")
        self.change("final.v", "PVDD2CDG power_VDDPST (.VDDPST(VDDPST));", "PVDD2CDG power_VDDPST (.VDDPST(VDD));")
        failed = self.run_audit()["checks"]["DEF_signal_and_power_bindings"]
        self.assertEqual(failed["status"], "FAIL")
        self.assertIn("Native IO supply mismatch", failed["error"])

    def test_native_supply_pad_missing_from_final_hdl_is_rejected(self):
        self.change("final.v", "PVDD2CDG power_VDDPST (.VDDPST(VDDPST));", "")
        failed = self.run_audit()["checks"]["DEF_signal_and_power_bindings"]
        self.assertEqual(failed["status"], "FAIL")
        self.assertIn("Native IO supply mismatch", failed["error"])

    def test_missing_explicit_native_supply_in_both_def_sections_is_rejected(self):
        # Isolate the supply PAD's explicit SIGNAL endpoint from unrelated
        # conventional PG pins, then use the real split DEF representation.
        for master in ("PDDW0204CDG", "PVDD2CDG"):
            self.change("cells.lef", f"MACRO {master}\n CLASS PAD ;\n SIZE 60 BY 115 ;\n PIN VDDPST\n  USE POWER",
                        f"MACRO {master}\n CLASS PAD ;\n SIZE 60 BY 115 ;\n PIN VDDPST\n  USE SIGNAL")
        self.change("final.def", "END NETS", "- VDDPST ( power_VDDPST VDDPST ) ;\nEND NETS")
        self.change("final.def", "( * VDDPST )", "( PIN VDDPST )")
        # The native endpoint is kept only in NETS and must remain visible.
        self.refreeze_fixture()
        self.assertEqual(self.run_audit()["status"], "PASS")
        self.change("final.def", "- VDDPST ( power_VDDPST VDDPST ) ;\n", "")
        failed = self.run_audit()["checks"]["DEF_signal_and_power_bindings"]
        self.assertEqual(failed["status"], "FAIL")
        self.assertIn("PG not bound in DEF", failed["error"])
        self.assertIn("power_VDDPST", failed["error"])


if __name__ == "__main__":
    unittest.main()
