"""Failure injection against the real frozen audit triplet; no EDA/DB access.

Set JOINT_AUDIT_EVIDENCE to a downloaded evidence directory. Without those
licensed/private evidence files this integration test is explicitly skipped.
"""
import copy
import json
import os
from pathlib import Path
import unittest

from audit_joint import Joint, Violation, native_connectivity, placement


class JointAuditFaults(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = Path(os.environ.get("JOINT_AUDIT_EVIDENCE", str(Path(__file__).resolve().parents[1]/"work/pnr-20261021-3400")))
        files = [cls.directory/name for name in ("timing_audit.json", "physical_audit_fixed.json", "frozen_artifacts.json")]
        if not all(path.is_file() for path in files):
            raise unittest.SkipTest("Downloaded original frozen timing/physical audit evidence was not supplied")
        cls.documents = [json.loads(path.read_text()) for path in files]

    def join(self, timing=None, physical=None, frozen=None, **kwargs):
        inputs = [copy.deepcopy(document) for document in self.documents]
        for index, override in enumerate((timing, physical, frozen)):
            if override:
                override(inputs[index])
        return Joint(*inputs, **kwargs).run()

    def test_real_evidence_reconciles_only_three_nonzero_native_reports(self):
        result = self.join()
        self.assertEqual(result["status"], "PASS")
        resolved = {name for name, check in result["timing_checks"].items() if "geometry_resolution" in check}
        self.assertEqual(resolved, {"final_signal_connectivity", "final_io_power_connectivity", "final_placement"})
        self.assertEqual(len(result["locally_rehashed_exception_reports"]), 3)
        for name, count_key, count in (("final_signal_connectivity", "reported_problems", 2),
                                      ("final_io_power_connectivity", "reported_problems", 2),
                                      ("final_placement", "tool_IO_overlap_count", 34)):
            check = result["timing_checks"][name]
            self.assertEqual(check["original"]["status"], "INCOMPLETE")
            self.assertEqual(check["geometry_resolution"]["original_native_report"][count_key], count)

    def test_timing_fail_and_unrelated_incomplete_cannot_be_waived(self):
        for name, status, reason in (("final_clock_contract", "FAIL", "clock mismatch"),
                                     ("final_signal_connectivity", "FAIL", self.documents[0]["checks"]["final_signal_connectivity"]["reason"]),
                                     ("unrelated_geometry", "INCOMPLETE", "REQUIRES_GEOMETRY: some other issue")):
            with self.subTest(name=name, status=status):
                def mutate(document):
                    document["checks"][name] = {"status": status, "reason": reason}
                    document["status"] = status
                result = self.join(timing=mutate)
                self.assertEqual(result["status"], status)
                self.assertEqual(result["timing_checks"][name]["status"], status)
                self.assertNotIn("geometry_resolution", result["timing_checks"][name])

    def test_failed_or_missing_native_geometry_is_not_accepted(self):
        for state in ("FAIL", "missing"):
            with self.subTest(state=state):
                def mutate(document):
                    if state == "missing":
                        del document["checks"]["native_IO_power_rail_geometry"]
                    else:
                        document["checks"]["native_IO_power_rail_geometry"] = {"status": "FAIL", "error": "rail gap"}
                        document["status"] = "FAIL"
                result = self.join(physical=mutate)
                self.assertNotEqual(result["status"], "PASS")
                self.assertEqual(result["timing_checks"]["final_signal_connectivity"]["status"], "INCOMPLETE")

    def test_frozen_hash_mismatch_and_missing_raw_report_fail_closed(self):
        def corrupt(document):
            document["files"]["reports/final_signal_connectivity.rpt"]["sha256"] = "0"*64
        self.assertEqual(self.join(frozen=corrupt)["status"], "FAIL")
        result = self.join(physical_root=self.directory/"does-not-exist")
        self.assertEqual(result["status"], "INCOMPLETE")
        self.assertNotIn("geometry_resolution", result["timing_checks"]["final_signal_connectivity"])

    def test_extra_native_net_or_core_overlap_cannot_use_the_geometry_exception(self):
        baseline = self.join()
        signal = baseline["timing_checks"]["final_signal_connectivity"]["geometry_resolution"]["original_native_report"]["original_report_text"]
        with self.assertRaises(Violation):
            native_connectivity(signal.replace("Begin Summary", "Net BROKEN: no routing\nBegin Summary"))
        raw = baseline["timing_checks"]["final_placement"]["geometry_resolution"]["original_native_report"]["original_report_text"]
        with self.assertRaises(Violation):
            placement(raw+"\nset pchkOverlapList [list {some/core_reg[7]}]\n")


if __name__ == "__main__":
    unittest.main()
