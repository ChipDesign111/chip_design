"""Pure-Python post-route SDF binding regressions; no EDA/PDK required.

Run: python -m unittest discover -s eda/pnr -p test_postroute_inputs.py -v
These tests check rejected/accepted input contracts, not simulation behavior.
"""
import importlib.util
from pathlib import Path
import tempfile
import unittest


SPEC = importlib.util.spec_from_file_location("postroute_runner", Path(__file__).with_name("run_postroute.py"))
RUNNER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RUNNER)

MODELS = """
module RA1SHD_2048x32M8(A,Q); input [10:0] A; output [31:0] Q; endmodule
module PDDW0204CDG(PAD,C); inout PAD; output C; endmodule
module ANTENNABWP7T(I); input I; endmodule
module LEAF(D,Y); input [1:0] D; output Y; endmodule
"""
NETLIST = """
module chip(clk_i,rst_ni,tck_i,tms_i,td_i,td_o);
input clk_i,rst_ni,tck_i,tms_i,td_i; output td_o;
wire [10:0] addr; wire [31:0] data;
RA1SHD_2048x32M8 ram(.A(addr),.Q(data));
PDDW0204CDG p0(.PAD(clk_i));
PDDW0204CDG p1(.PAD(rst_ni));
PDDW0204CDG p2(.PAD(tck_i));
PDDW0204CDG p3(.PAD(tms_i));
PDDW0204CDG p4(.PAD(td_i));
PDDW0204CDG p5(.PAD(td_o),.C(td_o));
ANTENNABWP7T diode(.I(data[7]));
child u_sub(.A(data[1:0]));
endmodule
module child(A); input [1:0] A; LEAF leaf(.D(A)); endmodule
"""
SDF = r"""
(DELAYFILE (SDFVERSION "3.0") (DIVIDER /)
 (CELL (CELLTYPE "chip") (INSTANCE)
  (DELAY (ABSOLUTE
   (INTERCONNECT clk_i p0/PAD (0.1:0.1:0.1))
   (INTERCONNECT ram/Q\[7\] diode/I (0.1:0.1:0.1))
   (INTERCONNECT ram/Q\[0\] u_sub/leaf/D\[1\] (0.1:0.1:0.1))
   (INTERCONNECT p5/C td_o (0.1:0.1:0.1)))))
 (CELL (CELLTYPE "RA1SHD_2048x32M8") (INSTANCE ram)
  (DELAY (ABSOLUTE (IOPATH A[0] Q[0] (0.1:0.1:0.1)))))
 (CELL (CELLTYPE "child") (INSTANCE u_sub)
  (DELAY (ABSOLUTE
   (INTERCONNECT A\[0\] leaf/D\[0\] (0.1:0.1:0.1)))))
)
"""


class PostrouteBindingTests(unittest.TestCase):
    def audit(self, netlist=NETLIST, sdf=SDF):
        scratch = Path(__file__).resolve().parents[1] / "work/postroute-input-selftest"
        scratch.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="binding-", dir=str(scratch)) as folder:
            base = Path(folder)
            self.assertEqual(base.resolve().parent, scratch.resolve())
            net, delay, model = (base/name for name in ("chip.v", "chip.sdf", "cells.v"))
            net.write_text(netlist)
            delay.write_text(sdf)
            model.write_text(MODELS)
            return RUNNER.structural_audit(net, delay, [model], "chip")

    def with_instances(self, instances):
        return NETLIST.replace("\nendmodule", "\n" + instances + "\nendmodule", 1)

    def with_targets(self, *targets):
        original = "(INTERCONNECT clk_i p0/PAD (0.1:0.1:0.1))"
        return SDF.replace(original, "\n".join("(INTERCONNECT clk_i " + target + " (0.1:0.1:0.1))" for target in targets))

    def test_actual_port_scalar_vector_and_nested_scope_bindings(self):
        result = self.audit()
        bound = result["sdf_interconnect_binding"]
        self.assertEqual(bound["status"], "PASS")
        self.assertEqual(bound["records"], 5)
        self.assertEqual(bound["root_records"], 4)
        self.assertEqual(bound["verified_endpoints"], 10)
        self.assertEqual(bound["root_top_port_endpoints"], 2)

    def test_excluded_antenna_endpoint_is_rejected(self):
        # Historical Lab4 had this exact failure shape: no antenna CELL record,
        # but root INTERCONNECT still pointed at an excluded diode instance.
        with self.assertRaisesRegex(ValueError, "INTERCONNECT endpoint binding failed"):
            self.audit(netlist=NETLIST.replace("ANTENNABWP7T diode(.I(data[7]));", ""))

    def test_unknown_leaf_port_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "INTERCONNECT endpoint binding failed"):
            self.audit(sdf=SDF.replace("diode/I", "diode/UNKNOWN"))

    def test_existing_but_unconnected_model_port_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "INTERCONNECT endpoint binding failed"):
            self.audit(netlist=NETLIST.replace("diode(.I(data[7]))", "diode(.I())"))

    def test_out_of_range_sram_bit_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "INTERCONNECT endpoint binding failed"):
            self.audit(sdf=SDF.replace(r"ram/Q\[7\]", r"ram/Q\[32\]"))

    def test_unknown_root_port_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "INTERCONNECT endpoint binding failed"):
            self.audit(sdf=SDF.replace("INTERCONNECT clk_i ", "INTERCONNECT unknown_top "))

    def test_unknown_hierarchical_scope_endpoint_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "INTERCONNECT endpoint binding failed"):
            self.audit(sdf=SDF.replace(r"leaf/D\[0\]", r"missing/D\[0\]"))

    def test_unparsed_arc_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Unparsed SDF INTERCONNECT syntax"):
            self.audit(sdf=SDF.replace("INTERCONNECT clk_i p0/PAD", "INTERCONNECT clk_i"))

    def test_dot_divider_preserves_escaped_literal_dot(self):
        self.assertEqual(RUNNER.sdf_path(r"parent.leaf\.name.D\[0\]", "."), ["parent", "leaf.name", "D[0]"])

    def test_literal_slash_endpoint_cannot_bind_hierarchical_instance(self):
        net = self.with_instances("child wrong(.A(data[1:0]));")
        with self.assertRaisesRegex(ValueError, "INTERCONNECT endpoint binding failed"):
            self.audit(net, self.with_targets(r"wrong\/leaf/D\[0\]"))

    def test_hierarchical_endpoint_cannot_bind_literal_slash_instance(self):
        net = self.with_instances(r"LEAF \wrong/leaf (.D(data[1:0]));")
        with self.assertRaisesRegex(ValueError, "INTERCONNECT endpoint binding failed"):
            self.audit(net, self.with_targets(r"wrong/leaf/D\[0\]"))

    def test_correct_hierarchical_and_literal_slash_endpoints_bind(self):
        for instance, target in (("child wrong(.A(data[1:0]));", r"wrong/leaf/D\[0\]"),
                                 (r"LEAF \wrong/leaf (.D(data[1:0]));", r"wrong\/leaf/D\[0\]")):
            with self.subTest(target=target):
                self.assertEqual(self.audit(self.with_instances(instance), self.with_targets(target))["status"], "PASS")

    def test_hierarchical_and_literal_slash_instances_can_coexist(self):
        net = self.with_instances("child wrong(.A(data[1:0]));\n" + r"LEAF \wrong/leaf (.D(data[1:0]));")
        sdf = self.with_targets(r"wrong/leaf/D\[0\]", r"wrong\/leaf/D\[0\]")
        # CELL instance identity must preserve the same boundary distinction.
        extra = r"""
 (CELL (CELLTYPE "LEAF") (INSTANCE wrong/leaf)
  (DELAY (ABSOLUTE (IOPATH D[0] Y (0.1:0.1:0.1)))))
 (CELL (CELLTYPE "LEAF") (INSTANCE wrong\/leaf)
  (DELAY (ABSOLUTE (IOPATH D[0] Y (0.1:0.1:0.1)))))
"""
        sdf = sdf.rsplit(")", 1)[0] + extra + ")"
        result = self.audit(net, sdf)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["sdf_interconnect_binding"]["root_records"], 5)

    def test_cell_instance_cannot_cross_literal_slash_boundary(self):
        for instance, wrong in (("child wrong(.A(data[1:0]));", r"wrong\/leaf"),
                                (r"LEAF \wrong/leaf (.D(data[1:0]));", "wrong/leaf")):
            extra = '(CELL (CELLTYPE "LEAF") (INSTANCE ' + wrong + '))'
            sdf = SDF.rsplit(")", 1)[0] + extra + ")"
            with self.subTest(wrong=wrong):
                with self.assertRaisesRegex(ValueError, "SDF CELLTYPE/INSTANCE mismatches"):
                    self.audit(self.with_instances(instance), sdf)

    def test_literal_slash_cell_scope_keeps_relative_endpoint_segments(self):
        net = self.with_instances("child wrong(.A(data[1:0]));\n" + r"child \wrong/leaf (.A(data[1:0]));")
        extra = r"""
 (CELL (CELLTYPE "child") (INSTANCE wrong\/leaf)
  (DELAY (ABSOLUTE (INTERCONNECT A\[0\] leaf/D\[0\] (0.1:0.1:0.1)))))
"""
        sdf = SDF.rsplit(")", 1)[0] + extra + ")"
        self.assertEqual(self.audit(net, sdf)["sdf_interconnect_binding"]["records"], 6)

    def test_ansi_vector_binding_does_not_admit_undeclared_bit(self):
        ports = RUNNER.binding_ports("module ansi(input wire [3:1] D, input EN, output Y); endmodule")["ansi"]
        self.assertTrue({"D", "D[1]", "D[2]", "D[3]", "EN", "Y"}.issubset(ports))
        self.assertNotIn("D[0]", ports)


if __name__ == "__main__":
    unittest.main()
