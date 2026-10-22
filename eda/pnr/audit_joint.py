#!/usr/bin/env python3
"""Join timing and physical audits without waiving any other incomplete/fail.

Only three named native-tool geometry cases can be reconciled. The original
checks, nonzero native diagnostics and their hashes remain in the result.
This reads JSON and three small reports; it never starts EDA or needs local DBs.
"""
import argparse
import ast
import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys

from audit_timing import Incomplete, Violation, tcl_commands, tcl_words, unquote


TIMING_REQUIRED = {
    "final_clock_contract", "no_path_adjustments", "final_setup_summary", "final_setup_paths",
    "final_hold_summary", "final_hold_paths", "summary_path_WNS_consistency", "final_timing_DRVs",
    "final_signal_connectivity", "final_power_connectivity", "final_io_power_connectivity",
    "final_DRC", "final_antenna", "final_welltap", "final_placement", "completed_stage_provenance",
    "inputs_unchanged_during_audit",
}
PHYSICAL_REQUIRED = {
    "post_IO_pin_preservation", "final_PAD_connections_and_ties", "core_rows_macro_and_legal_placement",
    "IO_ring_and_bond_geometry", "DEF_signal_and_power_bindings", "native_IO_power_rail_geometry",
    "tool_physical_reports", "frozen_stage_artifact_hashes",
}
ARTIFACTS = {
    "final-routed-DEF": "outputs/my_soc_top.def",
    "final-physical-netlist": "outputs/my_soc_top_final_physical.v",
    "final-SDC": "outputs/my_soc_top.sdc",
    "PNR-input-identity": "input_identity.json",
    "final-native-IO-PG-report": "reports/final_io_power_connectivity.rpt",
    "final-signal-report": "reports/final_signal_connectivity.rpt",
    "final-placement-report": "reports/final_placement.rpt",
    "final-core-PG-report": "reports/final_power_connectivity.rpt",
    "final-route-DRC-report": "reports/final_drc.rpt",
}
NATIVE_NETS = {"VDDPST", "VSSPST"}
RESOLVABLE = {"final_signal_connectivity", "final_io_power_connectivity", "final_placement"}


def sha(path):
    value = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1048576), b""):
            value.update(block)
    return value.hexdigest()


def require(condition, message):
    if not condition:
        raise Violation(message)


def known(condition, message):
    if not condition:
        raise Incomplete(message)


def normal(path):
    return str(path).replace("\\", "/").rstrip("/")


def digest(value):
    known(isinstance(value, str) and re.fullmatch(r"[a-fA-F0-9]{64}", value), "Missing/invalid SHA256 identity")
    return value.lower()


def aggregate(statuses):
    statuses = list(statuses)
    if "FAIL" in statuses:
        return "FAIL"
    return "PASS" if statuses and all(s == "PASS" for s in statuses) else "INCOMPLETE"


def native_connectivity(text):
    known(all(x in text for x in ("Verify Connectivity Report", "Begin Summary", "End Summary")), "Truncated native connectivity report")
    require(not re.search(r"\*\*ERROR|\bFATAL\b|unconnected terminal|dangling Wire|routing with opens", text, re.I), "Unexpected native connectivity diagnostic")
    diagnostics = [line for line in text.splitlines() if line.startswith("Net ")]
    no_route = []
    for line in diagnostics:
        match = re.fullmatch(r"Net\s+(\S+): no routing\s*", line)
        require(match is not None, "Additional native connectivity diagnostic: " + line)
        no_route.append(match[1])
    require(len(no_route) == 2 and set(no_route) == NATIVE_NETS, "Only the two named native IO rails may be reconciled")
    problems = [(int(n), code, message.strip()) for n, code, message in re.findall(r"(\d+)\s+Problem\(s\)\s*\(([^)]+)\):\s*([^\n]+)", text)]
    require(len(problems) == 1 and problems[0][0] == 2 and problems[0][1] == "IMPVFC-98" and
            problems[0][2] == "Net has no global routing and no special routing.", "Unexpected native connectivity summary")
    require(re.search(r"\b2 total info\(s\) created\.", text) is not None, "Missing complete native problem count")
    return {"reported_problems": 2, "no_routing_nets": sorted(no_route), "problem_summary": problems,
            "native_diagnostics": diagnostics, "original_report_text": text}


def placement(text):
    known(re.search(r"#\s*Command:\s*checkPlace\b", text) is not None, "Missing native checkPlace header")
    placed = re.findall(r"Number of Placed Instances\s*=\s*(\d+)", text)
    unplaced = re.findall(r"Number of Unplaced Instances\s*=\s*(\d+)", text)
    known(len(placed) == len(unplaced) == 1, "Missing/ambiguous native placement counts")
    require(int(placed[0]) > 0 and int(unplaced[0]) == 0, "Missing placed cells/nonzero unplaced cells")
    lists = {}
    for command in tcl_commands(text):
        words = tcl_words(command)
        known(len(words) == 3 and words[0] == "set" and re.fullmatch(r"pchk\w+List", words[1]), "Unknown placement-report body")
        rhs = words[2]
        known(rhs.startswith("[list") and rhs.endswith("]"), "Unknown native placement list syntax")
        entries = tcl_words(rhs[1:-1])
        known(entries and entries[0] == "list", "Unknown native placement list expression")
        entries = [unquote(word) for word in entries[1:]]
        if entries:
            require(words[1] not in lists, "Repeated native placement violation list")
            lists[words[1]] = entries
    require(set(lists) == {"pchkIoOverlapList"}, "Non-Bond placement violations or missing expected native list")
    require(len(lists["pchkIoOverlapList"]) == len(set(lists["pchkIoOverlapList"])) == 34, "Expected exactly 34 unique native PAD/Bond overlap entries")
    return {"placed_instances": int(placed[0]), "unplaced_instances": 0, "tool_IO_overlap_count": 34,
            "tool_IO_overlap_lists": lists, "original_report_text": text}


class Joint:
    def __init__(self, timing, physical, frozen, physical_root=None):
        self.timing, self.physical, self.frozen = timing, physical, frozen
        self.physical_root = Path(physical_root) if physical_root else None
        self.checks, self.bindings, self.local_hashes = {}, None, {}

    def check(self, name, function):
        try:
            self.checks[name] = {"status": "PASS", "details": function()}
        except Violation as error:
            self.checks[name] = {"status": "FAIL", "reason": str(error)}
        except (Incomplete, OSError, ValueError, TypeError, KeyError, IndexError) as error:
            self.checks[name] = {"status": "INCOMPLETE", "reason": str(error)}

    def input_contract(self):
        for document, schema, required in ((self.timing, "chip-design-postroute-timing-audit-v1", TIMING_REQUIRED),
                                            (self.physical, "chip-design-physical-audit-v1", PHYSICAL_REQUIRED)):
            known(document.get("schema") == schema, "Unsupported/missing audit schema: " + schema)
            checks = document.get("checks")
            known(isinstance(checks, dict) and required <= set(checks), "Missing required source audit checks: " + repr(sorted(required-set(checks or {}))))
            known(all(isinstance(c, dict) and c.get("status") in {"PASS", "FAIL", "INCOMPLETE", "NOT_CHECKED"} for c in checks.values()), "Unknown source check status")
            require(document.get("status") == aggregate(c["status"] for c in checks.values()), "Source audit overall status contradicts its checks")
        known(self.frozen.get("status") == "FROZEN_TOOL_EXPORT" and isinstance(self.frozen.get("files"), dict), "Missing original frozen export manifest")
        return {"timing_checks": len(self.timing["checks"]), "physical_checks": len(self.physical["checks"]),
                "policy": "Only the three named INCOMPLETE/REQUIRES_GEOMETRY records are resolvable; FAIL is never changed."}

    def pass_details(self, name):
        check = self.physical["checks"].get(name, {})
        known(check.get("status") == "PASS", "Corresponding physical check is not PASS: " + name)
        known(isinstance(check.get("details"), dict), "Missing positive physical detail: " + name)
        return check["details"]

    def bind(self):
        root = normal(self.timing.get("pnr_directory", ""))
        known(root, "Missing original timing PNR directory")
        timing_hashes = {normal(path): digest(value) for path, value in self.timing.get("input_sha256", {}).items()}
        known(timing_hashes, "Missing timing input identities")
        files = self.frozen["files"]
        mapped = []
        # Exact PNR-root-relative names only: no filename/basename fallback,
        # no use of query-restored/GLS files as original frozen exports.
        for path, value in timing_hashes.items():
            if path.startswith(root+"/"):
                relative = path[len(root)+1:]
                if relative in files:
                    require(value == digest(files[relative]["sha256"]), "Timing input differs from original frozen export: " + relative)
                    mapped.append(relative)
        for relative in ("outputs/my_soc_top.sdc", "reports/final_signal_connectivity.rpt",
                         "reports/final_io_power_connectivity.rpt", "reports/final_placement.rpt",
                         "reports/final_power_connectivity.rpt", "reports/final_drc.rpt", "reports/final_antenna.rpt"):
            known(relative in mapped, "Required timing evidence is not bound to original frozen export: " + relative)
        artifacts = self.pass_details("frozen_stage_artifact_hashes").get("artifacts", [])
        by_label = {}
        for artifact in artifacts:
            label = artifact.get("label")
            require(label not in by_label, "Repeated physical artifact label: " + str(label))
            by_label[label] = artifact
        physical_hashes = {normal(path): digest(value) for path, value in self.physical.get("sha256", {}).items()}
        bindings, roots = {}, set()
        for label, relative in ARTIFACTS.items():
            known(label in by_label and relative in files, "Missing frozen physical artifact: " + label)
            artifact = by_label[label]
            path = normal(artifact["path"])
            require(path.endswith("/"+relative), "Physical artifact is not the explicitly mapped original file: " + label)
            roots.add(path[:-len(relative)-1])
            expected = digest(files[relative]["sha256"])
            require(digest(artifact["sha256"]) == physical_hashes.get(path) == expected, "Physical/frozen recorded SHA mismatch: " + relative)
            bindings[relative] = {"physical_recorded_path": artifact["path"], "sha256": expected,
                                  "frozen_bytes": files[relative]["bytes"], "label": label}
        require(len(roots) == 1, "Physical artifacts were collected from different original output roots")
        self.bindings = bindings
        return {"original_timing_PNR_root": root, "physical_recorded_root": next(iter(roots)),
                "timing_to_frozen_relative_paths": sorted(mapped), "shared_artifacts": bindings,
                "scope": "Recorded SHA identities compared against original frozen manifest. Only three small exception reports are rehashed locally; no claim of local DB re-verification."}

    def raw_report(self, relative):
        known(self.bindings is not None, "Original frozen evidence binding is not established")
        binding = self.bindings[relative]
        path = self.physical_root/relative if self.physical_root else Path(binding["physical_recorded_path"])
        known(path.is_file(), "Missing local exception report: " + str(path))
        data = path.read_bytes()
        actual = hashlib.sha256(data).hexdigest()
        require(actual == binding["sha256"] and len(data) == binding["frozen_bytes"], "Local raw report differs from original frozen export: " + relative)
        self.local_hashes[str(path.resolve())] = actual
        return data.decode(errors="replace")

    def geometry(self, need_native):
        ring = self.pass_details("IO_ring_and_bond_geometry")
        self.pass_details("core_rows_macro_and_legal_placement")
        bindings = self.pass_details("DEF_signal_and_power_bindings")
        require(ring.get("bond_count") == ring.get("ordinary_pad_count") == 34 and len(ring.get("corners", [])) == 4, "Positive 34 PAD/Bond and four-corner geometry evidence missing")
        sides = ring.get("side_component_counts", {})
        require(set(sides) == {"N", "S", "E", "W"} and all(isinstance(n, int) and n > 0 for n in sides.values()), "Complete four-side abutment evidence missing")
        require(bindings.get("top_pin_count") == 10 and bindings.get("six_PAD_nets_have_no_bypass") is True, "Physical pin/electrical binding evidence missing")
        names = ["IO_ring_and_bond_geometry", "core_rows_macro_and_legal_placement", "DEF_signal_and_power_bindings", "tool_physical_reports", "frozen_stage_artifact_hashes"]
        if need_native:
            native = self.pass_details("native_IO_power_rail_geometry")
            require(set(native.get("rail_samples_um", {})) == NATIVE_NETS and "PCORNER" in native.get("native_masters_checked", []), "Positive proof of both native power rails and corners missing")
            require(all(bindings.get("explicit_native_IO_supply_pin_counts", {}).get(net, 0) > 0 for net in NATIVE_NETS), "Native IO supply bindings missing")
            names.append("native_IO_power_rail_geometry")
        self.pass_details("tool_physical_reports")
        return names

    def resolve(self, name):
        original = self.timing["checks"][name]
        known(original.get("status") == "INCOMPLETE", "Only original INCOMPLETE can be reconciled")
        reason = original.get("reason", "")
        kind = "signal" if name == "final_signal_connectivity" else "io_power"
        if name == "final_placement":
            prefix = "REQUIRES_GEOMETRY: tool IO-overlap list must be reconciled with one aligned Bond overlay per ordinary PAD and no ordinary-PAD overlaps: "
            known(reason.startswith(prefix), "Unrecognised placement incomplete reason")
            known(ast.literal_eval(reason[len(prefix):]) == {"pchkIoOverlapList": 34}, "Only the exact 34-entry Bond diagnostic is resolvable")
            proof = self.geometry(False)
            native = placement(self.raw_report("reports/final_placement.rpt"))
            physical = self.pass_details("tool_physical_reports")["placement"]
            require(physical.get("unplaced_instances") == 0 and physical.get("tool_IO_overlap_lists") == native["tool_IO_overlap_lists"], "Timing/physical overlap identities differ")
        else:
            expected = "REQUIRES_GEOMETRY: " + kind + " report contains 2 native IO rail no-routing problems for ['VDDPST', 'VSSPST']; not PG/connection PASS. Separate native GDS + complete IO abutment audit required."
            known(reason == expected, "Only the exact two named native IO no-routing diagnostics are resolvable")
            proof = self.geometry(True)
            native = native_connectivity(self.raw_report("reports/final_"+kind+"_connectivity.rpt"))
            physical = self.pass_details("tool_physical_reports")["signal_connectivity"]
            require(physical.get("reported_problems") == 2 and set(physical.get("accepted_native_rail_unrouted_nets", [])) == NATIVE_NETS, "Physical report reconciliation describes different native rails")
        return {"resolution": "RECONCILED_BY_INDEPENDENT_GEOMETRY", "physical_checks": proof,
                "original_native_report": native, "note": "Original tool counts/diagnostics remain nonzero. This is geometric reconciliation, not a zero native connectivity/overlap report."}

    def run(self):
        self.check("source_audit_contract", self.input_contract)
        self.check("original_frozen_artifact_binding", self.bind)
        merged = {}
        timing_checks = self.timing.get("checks", {})
        physical_checks = self.physical.get("checks", {})
        timing_checks = timing_checks if isinstance(timing_checks, dict) else {}
        physical_checks = physical_checks if isinstance(physical_checks, dict) else {}
        for name, original in timing_checks.items():
            if not isinstance(original, dict):
                merged[name] = {"status": "INCOMPLETE", "original": copy.deepcopy(original)}
                continue
            item = {"status": original.get("status", "INCOMPLETE"), "original": copy.deepcopy(original)}
            if name in RESOLVABLE and original.get("status") == "INCOMPLETE" and str(original.get("reason", "")).startswith("REQUIRES_GEOMETRY:"):
                key = "geometry_resolution_"+name
                self.check(key, lambda name=name: self.resolve(name))
                if self.checks[key]["status"] == "PASS":
                    item["status"] = "PASS"
                    item["geometry_resolution"] = self.checks[key]["details"]
            merged[name] = item
        status = aggregate([c["status"] for c in self.checks.values()] + [c["status"] for c in merged.values()] +
                           [c.get("status", "INCOMPLETE") if isinstance(c, dict) else "INCOMPLETE" for c in physical_checks.values()])
        return {"schema": "chip-design-joint-postroute-audit-v1", "generated_utc": datetime.now(timezone.utc).isoformat(),
                "status": status, "scope": "Joint static timing/physical export reconciliation; excludes SDF simulation, foundry DRC/LVS, formal CDC, ESD and IR/EM signoff",
                "checks": self.checks, "timing_checks": merged, "physical_checks": copy.deepcopy(physical_checks),
                "original_overall_statuses": {"timing": self.timing.get("status"), "physical": self.physical.get("status")},
                "locally_rehashed_exception_reports": self.local_hashes,
                "limits": self.timing.get("limits", []) + [self.physical.get("scope", "")]}


def run(timing_path, physical_path, frozen_path, physical_root=None):
    paths = {"timing": Path(timing_path), "physical": Path(physical_path), "original_frozen_manifest": Path(frozen_path)}
    try:
        documents = {name: json.loads(path.read_text()) for name, path in paths.items()}
        known(all(isinstance(document, dict) for document in documents.values()), "Source audit JSON must be an object")
        hashes = {name: {"path": str(path.resolve()), "sha256": sha(path)} for name, path in paths.items()}
        result = Joint(documents["timing"], documents["physical"], documents["original_frozen_manifest"], physical_root).run()
        for name, path in paths.items():
            require(sha(path) == hashes[name]["sha256"], "Source audit changed during joint audit: " + name)
        result["input_audits"] = hashes
        result["auditor_sha256"] = {str(Path(__file__).resolve()): sha(__file__),
                                    str(Path(__file__).with_name("audit_timing.py").resolve()): sha(Path(__file__).with_name("audit_timing.py"))}
        return result
    except Violation as error:
        return {"schema": "chip-design-joint-postroute-audit-v1", "status": "FAIL", "reason": str(error)}
    except (OSError, ValueError, TypeError, KeyError, Incomplete) as error:
        return {"schema": "chip-design-joint-postroute-audit-v1", "status": "INCOMPLETE", "reason": str(error)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timing", type=Path, required=True)
    parser.add_argument("--physical", type=Path, required=True)
    parser.add_argument("--frozen", type=Path, required=True)
    parser.add_argument("--physical-root", type=Path, help="Explicit relocation of the original physical bundle root; raw report SHA still must match")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.timing, args.physical, args.frozen, args.physical_root)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2)+"\n")
    print(json.dumps({"status": result["status"], "out": str(args.out),
                      "resolved": [name for name, c in result.get("timing_checks", {}).items() if "geometry_resolution" in c]}))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
