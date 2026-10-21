"""Fault-injection tests of report interpretation; no EDA or SoC runs."""
import gzip
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


spec = importlib.util.spec_from_file_location("timing_audit", Path(__file__).with_name("audit_timing.py"))
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def summary(mode, slack):
    rows = [f"| {mode.title()} mode | all | reg2reg |", f"| WNS (ns):| {slack} | {slack} |",
            "| TNS (ns):| 0.000 | 0.000 |", "| Violating Paths:| 0 | 0 |", "| All Paths:| 100 | 100 |"]
    if mode == "setup":
        rows += ["| max_cap | 0 (0) | 0.000 | 0 (0) |", "| max_tran | 0 (0) | 0.000 | 0 (0) |",
                 "| max_fanout | 0 (0) | 0 | 0 (0) |", "| max_length | 0 (0) | 0 | 0 (0) |"]
    return "timeDesign Summary\n"+"\n".join(rows)+"\n"


def connectivity(message="Found no problems or warnings."):
    return "Verify Connectivity Report is created on synthetic-test\nBegin Summary\n"+message+"\nEnd Summary\n"


def fixture(root):
    (root/"outputs").mkdir()
    (root/"reports/final_setup").mkdir(parents=True)
    (root/"reports/final_hold").mkdir(parents=True)
    sdc = "current_design my_soc_top\n"
    for name, (period, port) in audit.EXPECTED_CLOCKS.items():
        sdc += f"create_clock -name {name} -period {period} -waveform {{0 {period/2}}}"+(f" [get_ports {{{port}}}]" if port else "")+"\n"
    sdc += "set_propagated_clock [get_clocks {sys_clk jtag_clk}]\n"
    for name in audit.EXPECTED_CLOCKS:
        setup, hold = (.42, .42) if name == "virtual_jtag_tck" else (.52, .2)
        sdc += f"set_clock_uncertainty {setup} -setup [get_clocks {{{name}}}]\nset_clock_uncertainty {hold} -hold [get_clocks {{{name}}}]\n"
    (root/"outputs/my_soc_top.sdc").write_text(sdc)
    (root/"outputs/my_soc_top_path_adjust.tcl").write_text("")
    for mode, slack in (("setup", .1), ("hold", .02)):
        with gzip.open(root/"reports"/("final_"+mode)/("design_"+mode+".summary.gz"), "wt") as handle:
            handle.write(summary(mode, slack))
        (root/"reports"/("final_"+mode+"_paths.rpt")).write_text(
            f"Path 1: MET {mode.title()} Check with Pin core/a/CP\nEndpoint: core/a/D\nBeginpoint: core/b/Q\n  Slack Time {slack}\n")
    for kind in ("signal", "power", "io_power"):
        (root/"reports"/("final_"+kind+"_connectivity.rpt")).write_text(connectivity())
    (root/"reports/final_drc.rpt").write_text("No DRC violations were found\n")
    (root/"reports/final_antenna.rpt").write_text("No Violations Found\n")
    (root/"reports/final_welltap.rpt").write_text("VerifyWellTap report created on synthetic-test\nFound 0 violations in total\n")
    (root/"reports/final_placement.rpt").write_text("Number of Placed Instances = 123456\nNumber of Unplaced Instances = 0\n")
    identity = {"source_revision": "synthetic-fixture-only", "netlist_sha256": "0"*64, "sdc_sha256": "1"*64}
    (root/"input_identity.json").write_text(json.dumps(identity))
    inv = root/"invocations/20260101T000000Z-init"
    inv.mkdir(parents=True)
    stages = ["init", "floorplan", "io", "power", "place", "cts", "route", "finish", "export"]
    record = {"status": "COMPLETED", "exit_code": 0, "identity": identity, "stages": stages, "completed_stages": stages, "errors": []}
    (inv/"manifest.json").write_text(json.dumps(record))
    (inv/"console.log").write_text("\n".join("PNR_STAGE_COMPLETE "+s for s in stages)+"\nPNR_INVOCATION_COMPLETE\n")


class TimingAuditTests(unittest.TestCase):
    def setUp(self):
        self.workspace = Path(__file__).resolve().parents[1]/"work/timing-audit-selftest"
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=self.workspace)
        self.root = Path(self.temp.name)
        fixture(self.root)

    def tearDown(self):
        assert self.workspace.resolve() in self.root.resolve().parents
        self.temp.cleanup()

    def run_audit(self):
        return audit.run(self.root)

    def change(self, path, before, after):
        p = self.root/path
        text = p.read_text()
        self.assertIn(before, text)
        p.write_text(text.replace(before, after, 1))

    def test_complete_positive_evidence(self):
        result = self.run_audit()
        self.assertEqual(result["status"], "PASS", result)
        self.assertGreater(len(result["input_sha256"]), 10)

    def test_changed_period_is_rejected(self):
        self.change("outputs/my_soc_top.sdc", "-period 20.0", "-period 25.0")
        self.assertEqual(self.run_audit()["checks"]["final_clock_contract"]["status"], "FAIL")

    def test_ideal_physical_clock_is_rejected(self):
        self.change("outputs/my_soc_top.sdc", "set_propagated_clock", "set_ideal_clock")
        self.assertEqual(self.run_audit()["checks"]["final_clock_contract"]["status"], "FAIL")

    def test_propagated_virtual_clock_is_rejected(self):
        with (self.root/"outputs/my_soc_top.sdc").open("a") as handle:
            handle.write("set_propagated_clock [get_clocks virtual_jtag_tck]\n")
        self.assertEqual(self.run_audit()["checks"]["final_clock_contract"]["status"], "FAIL")

    def test_relaxed_uncertainty_is_rejected(self):
        self.change("outputs/my_soc_top.sdc", "0.52 -setup", "0.47 -setup")
        self.assertEqual(self.run_audit()["checks"]["final_clock_contract"]["status"], "FAIL")

    def test_extra_path_adjustment_is_rejected(self):
        (self.root/"outputs/my_soc_top_path_adjust.tcl").write_text("set_path_adjust 2 [get_pins core/D]\n")
        self.assertEqual(self.run_audit()["checks"]["no_path_adjustments"]["status"], "FAIL")

    def test_empty_or_missing_reports_never_pass(self):
        (self.root/"reports/final_antenna.rpt").write_text("")
        self.assertEqual(self.run_audit()["checks"]["final_antenna"]["status"], "INCOMPLETE")
        (self.root/"reports/final_hold_paths.rpt").unlink()
        self.assertEqual(self.run_audit()["checks"]["final_hold_paths"]["status"], "INCOMPLETE")

    def test_negative_hold_is_rejected(self):
        p = self.root/"reports/final_hold/design_hold.summary.gz"
        with gzip.open(p, "wt") as handle:
            handle.write(summary("hold", -.001))
        self.assertEqual(self.run_audit()["checks"]["final_hold_summary"]["status"], "FAIL")

    def test_unknown_summary_format_is_incomplete(self):
        p = self.root/"reports/final_hold/design_hold.summary.gz"
        with gzip.open(p, "wt") as handle:
            handle.write("Something else: all is good\n")
        self.assertEqual(self.run_audit()["checks"]["final_hold_summary"]["status"], "INCOMPLETE")

    def test_summary_vs_path_disagreement_is_rejected(self):
        self.change("reports/final_setup_paths.rpt", "Slack Time 0.1", "Slack Time 0.2")
        self.assertEqual(self.run_audit()["checks"]["summary_path_WNS_consistency"]["status"], "FAIL")

    def test_nonzero_drv_is_rejected(self):
        p = self.root/"reports/final_setup/design_setup.summary.gz"
        with gzip.open(p, "wt") as handle:
            handle.write(summary("setup", .1).replace("max_cap | 0 (0)", "max_cap | 1 (1)"))
        self.assertEqual(self.run_audit()["checks"]["final_timing_DRVs"]["status"], "FAIL")

    def test_native_IO_warnings_require_geometry(self):
        text = connectivity("Net VDDPST: no routing\nNet VSSPST: no routing\n2 Problem(s) (IMPVFC-98): Net has no global routing and no special routing.")
        (self.root/"reports/final_io_power_connectivity.rpt").write_text(text)
        result = self.run_audit()
        self.assertEqual(result["status"], "INCOMPLETE")
        self.assertIn("REQUIRES_GEOMETRY", result["checks"]["final_io_power_connectivity"]["reason"])

    def test_real_core_PG_problem_is_failure(self):
        (self.root/"reports/final_power_connectivity.rpt").write_text(connectivity("1 Problem(s) (SOME): unconnected pin"))
        self.assertEqual(self.run_audit()["checks"]["final_power_connectivity"]["status"], "FAIL")

    def test_nonzero_welltap_is_failure(self):
        self.change("reports/final_welltap.rpt", "Found 0 violations", "Found 3 violations")
        self.assertEqual(self.run_audit()["checks"]["final_welltap"]["status"], "FAIL")

    def test_uncompleted_export_never_passes(self):
        manifest = self.root/"invocations/20260101T000000Z-init/manifest.json"
        data = json.loads(manifest.read_text())
        data["status"] = "RUNNING"
        manifest.write_text(json.dumps(data))
        self.assertEqual(self.run_audit()["checks"]["completed_stage_provenance"]["status"], "INCOMPLETE")

    def test_failed_old_invocation_is_preserved_without_poisoning_new_completion(self):
        folder = self.root/"invocations/20200101T000000Z-init"
        folder.mkdir()
        (folder/"manifest.json").write_text(json.dumps({"status": "FAIL", "exit_code": 2, "errors": ["FATAL: old attempt"]}))
        self.assertEqual(self.run_audit()["status"], "PASS")

    def test_new_CTS_without_fresh_route_export_is_incomplete(self):
        old = json.loads((self.root/"invocations/20260101T000000Z-init/manifest.json").read_text())
        old.update(stages=["cts"], completed_stages=["cts"])
        folder = self.root/"invocations/20260102T000000Z-cts"
        folder.mkdir()
        (folder/"manifest.json").write_text(json.dumps(old))
        (folder/"console.log").write_text("PNR_STAGE_COMPLETE cts\nPNR_INVOCATION_COMPLETE\n")
        self.assertEqual(self.run_audit()["checks"]["completed_stage_provenance"]["status"], "INCOMPLETE")


if __name__ == "__main__":
    unittest.main()
