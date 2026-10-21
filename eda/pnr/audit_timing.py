#!/usr/bin/env python3
"""Independently audit completed post-route timing and verification exports.

Read-only, Python 3.8 standard library. No EDA process is started. Missing or
unrecognised evidence is INCOMPLETE, never an assumed zero. Native IO supply
warnings require the separate physical/native-GDS audit and are not PG PASS.
"""
import argparse
from datetime import datetime, timezone
import fnmatch
import gzip
import hashlib
import json
from pathlib import Path
import re
import sys
import tarfile


NUMBER = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"
EXPECTED_CLOCKS = {"sys_clk": (20.0, "clk_i"), "jtag_clk": (100.0, "tck_i"), "virtual_jtag_tck": (1000.0, None)}
ORDERED_STAGES = ("init", "floorplan", "io", "power", "place", "cts", "route", "finish", "export")
REQUIRED_STAGES = set(ORDERED_STAGES)
# Explicit evidence for the one historical init runner that hashed its sources
# but did not create invocation/source/. This already-preserved archive was
# independently read and matched to the original manifest, not reconstructed.
LEGACY_INIT_SOURCE = {
    "invocation": "20261021T055907515732Z-init",
    "archive": "accepted_init_source.tar",
    "archive_sha256": "a96e02af90582a8403d54fc12a1419e64896dc36b56e9783244336c558c5d82c",
    "main_member": "eda/pnr/main.tcl",
    "main_sha256": "d2a319d67d3ef2d376a5dbd002c19db083723938d4d496c6c7a773b07ef7c491",
}


class Incomplete(Exception):
    pass


class Violation(Exception):
    pass


def sha(path):
    result = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1048576), b""):
            result.update(block)
    return result.hexdigest()


class Evidence:
    def __init__(self, directory):
        self.directory = directory.resolve()
        self.hashes = {str(Path(__file__).resolve()): sha(Path(__file__))}
        self.checks = {}

    def read(self, relative, empty_ok=False):
        path = Path(relative)
        if not path.is_absolute():
            path = self.directory / path
        if not path.is_file():
            raise Incomplete("Missing file: " + str(path))
        self.hashes[str(path.resolve())] = sha(path)
        if path.suffix == ".gz":
            with gzip.open(str(path), "rt", errors="replace") as handle:
                text = handle.read()
        else:
            text = path.read_text(errors="replace")
        if not empty_ok and not text.strip():
            raise Incomplete("Empty report: " + str(path))
        return text

    def check(self, name, function):
        try:
            result = function()
            self.checks[name] = {"status": "PASS", "details": result}
        except Violation as error:
            self.checks[name] = {"status": "FAIL", "reason": str(error)}
        except (Incomplete, OSError, ValueError, KeyError, IndexError) as error:
            self.checks[name] = {"status": "INCOMPLETE", "reason": str(error)}


def require(condition, message):
    if not condition:
        raise Violation(message)


def known(condition, message):
    if not condition:
        raise Incomplete(message)


def reject_report_errors(text):
    require(not re.search(r"\*\*ERROR|\bPNR_STAGE_FAILED\b|\bFATAL\b", text), "Raw tool error in verification report")


def tcl_commands(text):
    """Split exported SDC without evaluating Tcl or obeying embedded code."""
    text = re.sub(r"\\\r?\n", " ", text)
    commands, current = [], []
    depth_brace = depth_bracket = 0
    quoted = escaped = False
    for line in text.splitlines(True):
        if not current and line.lstrip().startswith("#"):
            continue
        for char in line:
            if escaped:
                current.append(char)
                escaped = False
                continue
            if char == "\\":
                current.append(char)
                escaped = True
                continue
            if char == '"' and depth_brace == 0:
                quoted = not quoted
            elif not quoted:
                if char == "{":
                    depth_brace += 1
                elif char == "}":
                    depth_brace -= 1
                elif char == "[" and depth_brace == 0:
                    depth_bracket += 1
                elif char == "]" and depth_brace == 0:
                    depth_bracket -= 1
            known(depth_brace >= 0 and depth_bracket >= 0, "Unbalanced exported Tcl")
            if char in "\n;" and depth_brace == 0 and depth_bracket == 0 and not quoted:
                command = "".join(current).strip()
                if command and not command.startswith("#"):
                    commands.append(command)
                current = []
            else:
                current.append(char)
    known(depth_brace == 0 and depth_bracket == 0 and not quoted, "Truncated exported Tcl")
    if "".join(current).strip():
        commands.append("".join(current).strip())
    return commands


def tcl_words(command):
    words, current = [], []
    braces = brackets = 0
    quoted = escaped = False
    for char in command:
        if escaped:
            current.append(char)
            escaped = False
            continue
        if char == "\\":
            current.append(char)
            escaped = True
            continue
        if char == '"' and braces == 0:
            quoted = not quoted
        elif not quoted:
            if char == "{": braces += 1
            elif char == "}": braces -= 1
            elif char == "[" and braces == 0: brackets += 1
            elif char == "]" and braces == 0: brackets -= 1
        if char.isspace() and braces == 0 and brackets == 0 and not quoted:
            if current:
                words.append("".join(current))
                current = []
        else:
            current.append(char)
    if current:
        words.append("".join(current))
    return words


def unquote(word):
    if len(word) >= 2 and (word[0], word[-1]) in {("{", "}"), ('"', '"')}:
        return word[1:-1]
    return word


def collection(word, command):
    match = re.fullmatch(r"\[\s*" + re.escape(command) + r"\s+(.+)\]", word, re.S)
    if not match:
        return None
    tokens = tcl_words(match[1])
    names = []
    for token in tokens:
        if token == "-quiet":
            continue
        known(not token.startswith("-") and not re.search(r"[\[\]$]", token), "Unsupported " + command + " collection: " + word)
        names += unquote(token).split()
    return names


def audit_sdc(evidence):
    commands = tcl_commands(evidence.read("outputs/my_soc_top.sdc"))
    clocks, propagated, uncertainty = {}, {}, {}
    for command in commands:
        words = tcl_words(command)
        known(words, "Empty active SDC command")
        op = words[0]
        require(not re.search(r"path_?adjust", op, re.I), "Active path adjustment in final SDC: " + op)
        if op == "create_clock":
            known("-name" in words and "-period" in words, "Unrecognised exported create_clock: " + command)
            name = unquote(words[words.index("-name")+1])
            period = float(words[words.index("-period")+1])
            require(name not in clocks, "Repeated/overwritten clock: " + name)
            sources = [collection(w, "get_ports") for w in words if w.startswith("[") and "get_ports" in w]
            known(all(s is not None for s in sources), "Cannot determine clock source: " + command)
            source_names = [n for s in sources for n in s]
            known(len(source_names) <= 1, "Multiple clock source ports: " + command)
            if "-waveform" in words:
                waveform = [float(x) for x in unquote(words[words.index("-waveform")+1]).split()]
                require(len(waveform) == 2 and abs(waveform[0]) <= 1e-9 and abs(waveform[1]-period/2) <= 1e-9, "Clock waveform changed: " + name)
            clocks[name] = {"period_ns": period, "source_port": source_names[0] if source_names else None}
            propagated[name] = False
        elif op in {"set_propagated_clock", "set_ideal_clock"}:
            names = []
            for token in words[1:]:
                selected = collection(token, "get_clocks")
                if selected is not None:
                    for pattern in selected:
                        matches = [n for n in clocks if fnmatch.fnmatchcase(n, pattern)]
                        known(matches, "Unknown propagated/ideal clock pattern: " + pattern)
                        names += matches
                    continue
                ports = collection(token, "get_ports")
                if ports is not None:
                    for port in ports:
                        matches = [n for n, data in clocks.items() if data["source_port"] == port]
                        known(matches, "Unknown propagated/ideal source: " + port)
                        names += matches
                    continue
                if re.fullmatch(r"\[\s*all_clocks\s*\]", token):
                    names += list(clocks)
                    continue
                raise Incomplete("Unsupported propagated/ideal target: " + token)
            for name in names:
                propagated[name] = op == "set_propagated_clock"
        elif op == "set_clock_uncertainty":
            numeric = [float(w) for w in words[1:] if re.fullmatch(NUMBER, w)]
            targets = [collection(w, "get_clocks") for w in words[1:] if w.startswith("[")]
            known(len(numeric) == 1 and targets and all(t is not None for t in targets), "Unsupported clock uncertainty: " + command)
            known(not any(w in words for w in ("-from", "-to", "-rise_from", "-fall_from", "-rise_to", "-fall_to")), "Cross-clock uncertainty requires explicit parser support")
            modes = [m for m in ("setup", "hold") if "-"+m in words] or ["setup", "hold"]
            for name in [n for target in targets for n in target]:
                for mode in modes:
                    uncertainty[(name, mode)] = numeric[0]
        elif op == "set_units" and "-time" in words:
            require(words[words.index("-time")+1] in {"ns", "1ns"}, "Final SDC is not expressed in ns")
    require(set(clocks) == set(EXPECTED_CLOCKS), "Unexpected/missing final clocks: " + repr(clocks))
    for name, (period, port) in EXPECTED_CLOCKS.items():
        require(abs(clocks[name]["period_ns"]-period) <= 1e-9 and clocks[name]["source_port"] == port, "Clock period/source changed: " + name)
        require(propagated[name] == (port is not None), "Final propagated/ideal state wrong: " + name)
        for mode in ("setup", "hold"):
            expected = (.52 if mode == "setup" else .2) if port else .42
            known((name, mode) in uncertainty, "Missing final " + mode + " uncertainty: " + name)
            require(abs(uncertainty[(name, mode)]-expected) <= 1e-9, "Clock uncertainty changed: " + repr((name, mode, uncertainty[(name, mode)], expected)))
        clocks[name]["propagated"] = propagated[name]
        clocks[name]["setup_uncertainty_ns"] = uncertainty[(name, "setup")]
        clocks[name]["hold_uncertainty_ns"] = uncertainty[(name, "hold")]
    return {"clocks": clocks, "evidence": "Final write_sdc export: explicit propagated physical clocks; unpropagated source-free virtual clock remains ideal"}


def audit_path_adjustments(evidence):
    candidates = [evidence.directory/"outputs"/n for n in ("my_soc_top_path_adjust.tcl", "path_adjust.tcl")]
    existing = [p for p in candidates if p.is_file()]
    known(existing, "Missing exported path_adjust Tcl")
    records = []
    for path in existing:
        text = evidence.read(path, empty_ok=True)
        active = tcl_commands(text)
        require(not active, "Extra active path adjustments: " + str(path) + " " + repr(active[:5]))
        records.append({"path": str(path), "bytes": path.stat().st_size, "active_commands": 0})
    return records


def parse_summary(text, mode):
    reject_report_errors(text)
    lines = text.splitlines()
    header_indices = [i for i, line in enumerate(lines) if re.search(r"\|\s*" + mode + r" mode\s*\|", line, re.I)]
    known(len(header_indices) == 1, "Unrecognised/ambiguous timeDesign " + mode + " summary table")
    start = header_indices[0]
    columns = [x.strip() for x in lines[start].split("|")[2:-1]]
    known(columns and columns[0] == "all", "timeDesign summary lacks all-path column")
    values = {}
    for label, key in ((r"WNS\s*\(ns\)", "wns_ns"), (r"TNS\s*\(ns\)", "tns_ns"), (r"Violating Paths", "violating_paths"), (r"All Paths", "all_paths")):
        matches = [line for line in lines[start+1:] if re.search(r"\|\s*"+label+r"\s*:\s*\|", line)]
        known(len(matches) == 1, "Missing/unknown summary row: " + key)
        tokens = [x.strip() for x in matches[0].split("|")[2:-1]]
        known(len(tokens) == len(columns), "Summary column mismatch: " + key)
        known(all(re.fullmatch(NUMBER, x) for x in tokens), "Non-numeric/unanalysed summary cells: " + key)
        values[key] = [float(x) if key.endswith("_ns") else int(x) for x in tokens]
    for i, name in enumerate(columns):
        require(values["wns_ns"][i] >= 0 and values["tns_ns"][i] == 0 and values["violating_paths"][i] == 0,
                mode + " violation in " + name + ": " + repr({k: v[i] for k, v in values.items()}))
    known(values["all_paths"][0] > 0, "Vacuous timing summary: zero analysed paths")
    return {"mode": mode, "groups": {name: {k: v[i] for k, v in values.items()} for i, name in enumerate(columns)},
            "violating_endpoints_proved_zero": True,
            "endpoint_count_note": "Tool row is named Violating Paths; zero violations proves zero violating endpoints. Nonzero path counts are not recast as unique endpoints."}


def audit_summaries(evidence, mode):
    folder = evidence.directory/"reports"/("final_"+mode)
    paths = sorted(p for p in folder.rglob("*") if p.is_file() and re.search(r"\.summary(?:\.gz)?$", p.name)) if folder.exists() else []
    known(paths, "Missing final " + mode + " timeDesign summary files")
    output = []
    for path in paths:
        parsed = parse_summary(evidence.read(path), mode)
        output.append({"path": str(path), **parsed})
    return output


def audit_drv(evidence):
    folder = evidence.directory/"reports/final_setup"
    paths = sorted(p for p in folder.rglob("*") if p.is_file() and re.search(r"\.summary(?:\.gz)?$", p.name)) if folder.exists() else []
    known(paths, "Missing final setup summary for DRV")
    results = []
    for path in paths:
        text = evidence.read(path)
        if "max_cap" not in text:
            continue
        rows = {}
        for name in ("max_cap", "max_tran", "max_fanout", "max_length"):
            match = re.search(r"\|\s*"+name+r"\s*\|\s*(\d+)\s*\((\d+)\)\s*\|\s*("+NUMBER+r")\s*\|\s*(\d+)\s*\((\d+)\)\s*\|", text)
            known(match, "Unknown/missing DRV row: " + name)
            numbers = list(map(float, match.groups()))
            require(all(x == 0 for x in numbers), "Nonzero final DRV " + name + ": " + repr(numbers))
            rows[name] = {"real_nets": 0, "real_terms": 0, "worst_violation": 0, "total_nets": 0, "total_terms": 0}
        results.append({"path": str(path), "rows": rows})
    known(results, "No positive final DRV table evidence")
    return results


def audit_path_report(evidence, mode):
    text = evidence.read("reports/final_"+mode+"_paths.rpt")
    reject_report_errors(text)
    starts = list(re.finditer(r"(?m)^Path\s+(\d+):\s+(MET|VIOLATED)\s+(.+?)\s+Check\b", text))
    known(starts, "Unrecognised final report_timing path format for " + mode)
    paths = []
    for i, match in enumerate(starts):
        block = text[match.start(): starts[i+1].start() if i+1 < len(starts) else len(text)]
        slacks = re.findall(r"(?m)^\s*(?:=\s*)?Slack Time\s+("+NUMBER+r")\s*$", block)
        known(len(slacks) == 1, "Missing/ambiguous Slack Time in path " + match[1])
        slack = float(slacks[0])
        require(match[2] == "MET" and slack >= 0, mode + " report_timing violation: path " + match[1] + " slack=" + str(slack))
        known(re.search(r"\bEndpoint:", block) and re.search(r"\bBeginpoint:", block), "Path endpoints not identified")
        paths.append({"number": int(match[1]), "check": match[3], "slack_ns": slack})
    actual_modes = [p["check"].lower() for p in paths]
    known(any(mode in check for check in actual_modes), "No " + mode + " checks in the named path report")
    return {"reported_path_count": len(paths), "worst_reported_slack_ns": min(p["slack_ns"] for p in paths),
            "paths": paths, "scope": "Limited reported worst-path sample, not the complete endpoint count"}


def audit_summary_vs_paths(evidence):
    result = {}
    for mode in ("setup", "hold"):
        summaries = audit_summaries(evidence, mode)
        paths = audit_path_report(evidence, mode)
        worst = min(s["groups"]["all"]["wns_ns"] for s in summaries)
        require(abs(worst-paths["worst_reported_slack_ns"]) <= .0011,
                mode + " summary/path WNS differ: " + repr((worst, paths["worst_reported_slack_ns"])))
        result[mode] = {"summary_wns_ns": worst, "sample_wns_ns": paths["worst_reported_slack_ns"]}
    return result


def problem_counts(text):
    return [(int(n), code, message.strip()) for n, code, message in re.findall(r"(\d+)\s+Problem\(s\)\s*\(([^)]+)\):\s*([^\n]+)", text)]


def audit_connectivity(evidence, kind):
    text = evidence.read("reports/final_"+kind+"_connectivity.rpt")
    reject_report_errors(text)
    known("Verify Connectivity Report" in text and "Begin Summary" in text and "End Summary" in text,
          "Missing complete verifyConnectivity report structure for " + kind)
    counts = problem_counts(text)
    no_route = re.findall(r"(?m)^Net\s+(\S+): no routing\s*$", text)
    if "Found no problems or warnings." in text and not any(n for n, _, _ in counts) and not no_route:
        return {"reported_problems": 0, "positive_evidence": "Found no problems or warnings."}
    if no_route and set(no_route) <= {"VDDPST", "VSSPST"} and len(no_route) == len(set(no_route)):
        native_only = len(counts) == 1 and counts[0][0] == len(no_route) and counts[0][1] == "IMPVFC-98" and "no global routing and no special routing" in counts[0][2]
        if native_only and kind in {"io_power", "signal"}:
            raise Incomplete("REQUIRES_GEOMETRY: " + kind + " report contains " + str(len(no_route)) + " native IO rail no-routing problems for " + repr(sorted(no_route)) + "; not PG/connection PASS. Separate native GDS + complete IO abutment audit required.")
    if counts or no_route:
        raise Violation(kind + " connectivity problems: " + repr({"problems": counts, "no_routing": no_route}))
    raise Incomplete("No recognised positive zero-connectivity evidence for " + kind)


def audit_zero_report(evidence, kind):
    names = {"DRC": "final_drc.rpt", "antenna": "final_antenna.rpt", "welltap": "final_welltap.rpt"}
    text = evidence.read("reports/"+names[kind])
    reject_report_errors(text)
    patterns = {"DRC": r"No DRC violations were found", "antenna": r"No Violations Found", "welltap": r"Found\s+0\s+violations in total"}
    nonzero = re.findall(r"\b([1-9]\d*)\s+(?:DRC\s+)?violations?\b", text, re.I)
    require(not nonzero, kind + " report has nonzero violation evidence: " + repr(nonzero))
    known(re.search(patterns[kind], text, re.I), "No recognised positive zero-violation evidence for " + kind)
    return {"reported_violations": 0, "positive_evidence_pattern": patterns[kind],
            "scope": "Innovus report, not independent foundry signoff"}


def audit_placement(evidence):
    text = evidence.read("reports/final_placement.rpt")
    reject_report_errors(text)
    placed = re.findall(r"Number of Placed Instances\s*=\s*(\d+)", text)
    unplaced = re.findall(r"Number of Unplaced Instances\s*=\s*(\d+)", text)
    known(placed and unplaced, "Missing placement count summary")
    require(all(int(n) > 0 for n in placed) and all(int(n) == 0 for n in unplaced), "Missing placed cells or nonzero unplaced cells")
    lists = {}
    for name, contents in re.findall(r"set\s+(pchk\w+List)\s+\[list(.*?)\]", text, re.S):
        entries = re.findall(r"\{([^}]+)\}", contents)
        if entries:
            lists[name] = entries
    unexpected = {name: entries for name, entries in lists.items() if "IoOverlap" not in name}
    require(not unexpected, "Placement violation lists: " + repr(unexpected))
    if lists:
        raise Incomplete("REQUIRES_GEOMETRY: tool IO-overlap list must be reconciled with one aligned Bond overlay per ordinary PAD and no ordinary-PAD overlaps: " + repr({n: len(v) for n, v in lists.items()}))
    return {"placed_instances": int(placed[-1]), "unplaced_instances": 0, "nonempty_violation_lists": {}}


def invocation_stamp(path, record):
    stages = record.get("stages", [])
    known(stages, "Invocation has no requested stages: " + str(path))
    suffix = "-"+stages[0]
    known(path.parent.name.endswith(suffix), "Invocation directory does not identify its first stage: " + str(path))
    stamp = path.parent.name[:-len(suffix)]
    known(re.fullmatch(r"\d{8}T\d{6,12}Z", stamp), "Unknown timestamped checkpoint naming scheme: " + stamp)
    return stamp


def resume_checkpoint_key(value):
    known(isinstance(value, str) and value, "Missing recorded resume checkpoint")
    parts = value.replace("\\", "/").rstrip("/").split("/")
    known(len(parts) >= 2 and parts[-2] == "backup" and parts[-1].endswith(".enc.dat"),
          "Resume does not reference this flow's timestamped backup checkpoint: " + value)
    return parts[-1]


def check_invocation_record(evidence, path, record, identity):
    """Validate a complete invocation or only its explicitly completed prefix."""
    require(record.get("identity") == identity, "Invocation uses different physical input identity: " + str(path))
    requested = record.get("stages", [])
    completed = record.get("completed_stages", [])
    known(requested and completed and set(requested) <= REQUIRED_STAGES, "Missing/unknown requested/completed stages: " + str(path))
    require(requested == sorted(set(requested), key=ORDERED_STAGES.index), "Invalid requested stage order/duplicates: " + str(path))
    require(all(ORDERED_STAGES.index(b) == ORDERED_STAGES.index(a)+1 for a, b in zip(requested, requested[1:])),
            "Invocation skips a predecessor stage: " + str(path))
    require(completed == requested[:len(completed)], "Completed stages are not the exact requested prefix: " + str(path))
    console = evidence.read(path.parent/"console.log")
    markers = list(re.finditer(r"(?m)^PNR_STAGE_COMPLETE\s+(\w+)\s*$", console))
    require([m[1] for m in markers] == completed, "Manifest/console completed prefix differs: " + str(path))
    if record.get("status") == "COMPLETED":
        require(record.get("exit_code") == 0 and completed == requested and not record.get("errors"), "Inconsistent successful invocation: " + str(path))
        require("PNR_INVOCATION_COMPLETE" in console and not re.search(r"\*\*ERROR|PNR_STAGE_FAILED|\bFATAL\b", console),
                "Error/missing completion marker in successful invocation: " + str(path))
        return {"manifest": str(path), "classification": "COMPLETED", "completed_stages": completed}
    known(record.get("status") == "FAIL", "Selected ancestor invocation is not finished: " + str(path))
    require(isinstance(record.get("exit_code"), int) and record["exit_code"] != 0,
            "Failed partial invocation lacks a nonzero process exit: " + str(path))
    require(len(completed) < len(requested), "Failed invocation is not an isolated later-stage failure: " + str(path))
    expected_failure = requested[len(completed)]
    failures = list(re.finditer(r"(?m)^PNR_STAGE_FAILED\s+(\w+)\s*:", console))
    require(len(failures) == 1 and failures[0][1] == expected_failure and failures[0].start() > markers[-1].end(),
            "Failure is not confined to the next uncompleted stage: " + str(path))
    require(not re.search(r"\*\*ERROR|PNR_STAGE_FAILED|\bFATAL\b", console[:markers[-1].end()]),
            "Tool error predates a claimed completed checkpoint: " + str(path))
    # Driver-only integrity failures (changed Tcl/library/input inventory) are
    # not a schema failure in the later Tcl stage and invalidate this branch.
    require(all(isinstance(error, str) and error in console for error in record.get("errors", [])),
            "Out-of-band integrity error in partially completed invocation: " + str(path))
    return {"manifest": str(path), "classification": "COMPLETED_PREFIX_BEFORE_LATER_FAILURE",
            "completed_stages": completed, "failed_stage_not_accepted": expected_failure,
            "overall_invocation_status": record.get("status"), "overall_exit_code": record.get("exit_code")}


def checkpoint_main_source(evidence, node):
    """Return frozen main bytes from a normal snapshot or one pinned init tar.

    Nothing is extracted or created. A missing non-init snapshot never falls
    back to an archive, nor can an arbitrary archive be self-approved by a new
    digest. Every manifest-listed source in the pinned tar is checked as well.
    """
    source = node["path"].parent/"source/main.tcl"
    scripts = node["record"].get("scripts_sha256", {})
    expected = [value for name, value in scripts.items() if name.replace("\\", "/").endswith("/pnr/main.tcl")]
    known(len(expected) == 1, "Missing frozen main.tcl identity for checkpoint source: " + str(node["path"]))
    if source.is_file():
        main = evidence.read(source)
        actual = sha(source)
        require(actual == expected[0], "Saved main.tcl snapshot SHA mismatch: " + str(source))
        return main, {"kind": "invocation_source_snapshot", "path": str(source), "main_sha256": actual}
    legacy = LEGACY_INIT_SOURCE
    record = node["record"]
    known(node["stage"] == "init" and node["path"].parent.name == legacy["invocation"],
          "Missing frozen source/main.tcl; no approved legacy source for: " + str(node["path"]))
    require(record.get("stages") == ["init"] and record.get("completed_stages") == ["init"] and
            record.get("resume") in {None, ""} and record.get("status") == "COMPLETED" and
            record.get("exit_code") == 0 and not record.get("errors"),
            "Pinned legacy archive is permitted only for the successful standalone initial init")
    require(expected[0] == legacy["main_sha256"], "Legacy init manifest main.tcl identity differs from independently verified source")
    archive = node["path"].parent/legacy["archive"]
    known(archive.is_file(), "Missing previously preserved legacy init source archive: " + str(archive))
    actual_archive = sha(archive)
    evidence.hashes[str(archive.resolve())] = actual_archive
    require(actual_archive == legacy["archive_sha256"], "Preserved legacy init source archive SHA mismatch: " + str(archive))
    try:
        with tarfile.open(str(archive), "r:*") as handle:
            members = handle.getmembers()
            require(len({m.name for m in members}) == len(members), "Duplicate member names in legacy init source archive")
            require(all(m.isfile() and m.name.startswith("eda/pnr/") and not m.name.startswith("/") and
                        ".." not in m.name.split("/") and "\\" not in m.name for m in members),
                    "Unexpected path/type in legacy init source archive")
            contents = {m.name: handle.extractfile(m).read() for m in members}
    except tarfile.TarError as error:
        raise Incomplete("Cannot read pinned legacy init source archive: " + str(error))
    known(legacy["main_member"] in contents, "Pinned legacy init archive lacks its exact main member")
    member_hashes = {name: hashlib.sha256(data).hexdigest() for name, data in contents.items()}
    require(member_hashes[legacy["main_member"]] == expected[0], "Legacy archive main member differs from original manifest")
    required_scripts = {name: value for name, value in scripts.items() if name.startswith("eda/pnr/")}
    known(required_scripts, "Legacy init manifest has no source identities")
    require(all(name in member_hashes and member_hashes[name] == value for name, value in required_scripts.items()),
            "Legacy source archive does not match every original manifest-listed PNR source")
    return contents[legacy["main_member"]].decode("utf-8"), {
        "kind": "explicit_pinned_legacy_init_source_tar", "invocation": legacy["invocation"],
        "archive": str(archive), "archive_sha256": actual_archive,
        "main_member": legacy["main_member"], "main_sha256": member_hashes[legacy["main_member"]],
        "manifest_listed_sources_verified": len(required_scripts),
        "manifest_member_sha256": {name: member_hashes[name] for name in required_scripts},
        "note": "Previously preserved archive read in place; no historical source/ snapshot is fabricated or extracted"}


def bind_saved_checkpoint(evidence, node, checked):
    """Bind a resume source to its saved DB, context and frozen save protocol.

    Absolute server paths can be audited from a copied output tree: matching is
    confined to the uniquely timestamped backup basename derived from the source
    invocation, never an arbitrary same-named file elsewhere.
    """
    key = node["checkpoint"]
    if key in checked:
        return checked[key]
    database = evidence.directory/"backup"/key
    known(database.is_dir(), "Missing saved checkpoint directory: " + str(database))
    files = sorted(p for p in database.rglob("*") if p.is_file())
    known(files and any(p.stat().st_size > 0 for p in files), "Saved checkpoint DB is empty: " + str(database))
    main, source_provenance = checkpoint_main_source(evidence, node)
    naming = re.search(r"set\s+checkpoint\s+\[file\s+join\s+\$output_root\s+backup\s+\$\{stage\}-\$\{invocation_id\}\.enc\]", main)
    save = re.search(r"\bsaveDesign\s+\$checkpoint\b", main)
    marker = re.search(r'puts\s+"PNR_STAGE_COMPLETE\s+\$stage"', main)
    known(naming and save and marker and naming.start() < save.start() < marker.start(),
          "Frozen main.tcl does not prove checkpoint save precedes completion marker")
    context = evidence.directory/"backup"/(key[:-4]+".context.tcl")
    context_record = None
    if context.is_file():
        known(evidence.read(context).strip(), "Saved checkpoint context is empty: " + str(context))
        context_save = re.search(r"save_physical_tcl_context\s+\$\{checkpoint\}\.context\.tcl", main)
        known(context_save and save.start() < context_save.start() < marker.start(),
              "Frozen main.tcl does not prove context save precedes completion marker")
        context_record = {"path": str(context), "sha256": evidence.hashes[str(context.resolve())]}
    else:
        # The production restore protocol explicitly permits legacy init DBs
        # without helper state. Floorplan and every later DB require context.
        known(node["stage"] == "init", "Missing saved non-init checkpoint context: " + str(context))
    loader = Path(str(database)[:-4])
    if loader.is_file():
        evidence.hashes[str(loader.resolve())] = sha(loader)
    tree = hashlib.sha256()
    total_bytes = 0
    for path in files:
        value = sha(path)
        evidence.hashes[str(path.resolve())] = value
        total_bytes += path.stat().st_size
        tree.update((path.relative_to(database).as_posix()+"\0"+value+"\n").encode())
    result = {"stage": node["stage"], "source_manifest": str(node["path"]), "database": str(database),
              "database_file_count": len(files), "database_total_bytes": total_bytes,
              "database_tree_sha256": tree.hexdigest(), "context": context_record,
              "saved_main_tcl_sha256": source_provenance["main_sha256"],
              "main_source_provenance": source_provenance,
              "hash_scope": "Observed immutable timestamped DB files at audit time; producer did not record a historical creation-time DB hash"}
    checked[key] = result
    return result


def audit_completed_provenance(evidence):
    identity = json.loads(evidence.read("input_identity.json"))
    paths = sorted((evidence.directory/"invocations").glob("*/manifest.json"))
    known(paths, "Missing recorded Innovus invocations")
    records = [(path, json.loads(evidence.read(path))) for path in paths]
    latest_path, latest = records[-1]
    known(latest.get("status") not in {"RUNNING", "PREPARED"}, "Latest physical invocation is not finished: " + str(latest_path))
    require(latest.get("status") == "COMPLETED" and latest.get("exit_code") == 0, "Latest physical invocation failed: " + str(latest_path))
    known(latest.get("completed_stages") and latest["completed_stages"][-1] == "export",
          "Latest completed invocation has not completed fresh downstream export")
    nodes = {}
    for path, record in records:
        completed = record.get("completed_stages", [])
        if not completed:
            continue
        stamp = invocation_stamp(path, record)
        for stage in completed:
            key = stage+"-"+stamp+".enc.dat"
            require(key not in nodes, "Ambiguous timestamped checkpoint identity: " + key)
            nodes[key] = {"stage": stage, "path": path, "record": record, "checkpoint": key}
    final_key = "export-"+invocation_stamp(latest_path, latest)+".enc.dat"
    known(final_key in nodes, "Final export checkpoint has no completion record")
    current = nodes[final_key]
    chain, links, validated, checked = [], [], {}, {}
    seen = set()
    while current:
        key, stage, record, path = current["checkpoint"], current["stage"], current["record"], current["path"]
        require(key not in seen, "Cycle in saved physical resume chain")
        seen.add(key)
        if str(path) not in validated:
            validated[str(path)] = check_invocation_record(evidence, path, record, identity)
        classification = validated[str(path)]["classification"]
        if classification == "COMPLETED_PREFIX_BEFORE_LATER_FAILURE":
            bind_saved_checkpoint(evidence, current, checked)
        chain.append({"stage": stage, "checkpoint": key, "manifest": str(path), "classification": classification})
        index = ORDERED_STAGES.index(stage)
        if index == 0:
            require(record.get("resume") in {None, ""}, "Init stage unexpectedly resumes another design")
            current = None
            continue
        predecessor = ORDERED_STAGES[index-1]
        completed = record["completed_stages"]
        position = completed.index(stage)
        if position > 0:
            parent_key = predecessor+"-"+invocation_stamp(path, record)+".enc.dat"
        else:
            parent_key = resume_checkpoint_key(record.get("resume"))
            known(parent_key in nodes and nodes[parent_key]["stage"] == predecessor,
                  "Resume does not identify a completed immediate predecessor of "+stage+": "+str(record.get("resume")))
            require(nodes[parent_key]["path"] < path, "Resume source is not an earlier invocation")
            binding = bind_saved_checkpoint(evidence, nodes[parent_key], checked)
            links.append({"consumer_manifest": str(path), "first_stage": stage, "recorded_resume": record["resume"],
                          "completed_predecessor": predecessor, "checkpoint": parent_key,
                          "database_tree_sha256": binding["database_tree_sha256"]})
        known(parent_key in nodes, "Missing completed predecessor checkpoint: " + parent_key)
        current = nodes[parent_key]
    chain.reverse()
    require([item["stage"] for item in chain] == list(ORDERED_STAGES), "Final export does not descend from a complete ordered stage chain")
    return {"completed_stages": list(ORDERED_STAGES), "selected_stage_chain": chain, "resume_links": links,
            "selected_invocations": list(validated.values()), "saved_checkpoint_bindings": list(checked.values()),
            "input_identity": identity,
            "note": "Only the actual final-export ancestry counts. A saved completed prefix before a later failure is accepted only when its DB/context and exact downstream resume link are verified; the failed stage is never accepted."}


def audit_unchanged_inputs(evidence):
    changed = [path for path, expected in evidence.hashes.items() if not Path(path).is_file() or sha(path) != expected]
    require(not changed, "Inputs changed while audit was reading them: " + repr(changed))
    return {"bound_files_rechecked": len(evidence.hashes), "changed_files": []}


def run(directory):
    evidence = Evidence(directory)
    evidence.check("final_clock_contract", lambda: audit_sdc(evidence))
    evidence.check("no_path_adjustments", lambda: audit_path_adjustments(evidence))
    for mode in ("setup", "hold"):
        evidence.check("final_"+mode+"_summary", lambda mode=mode: audit_summaries(evidence, mode))
        evidence.check("final_"+mode+"_paths", lambda mode=mode: audit_path_report(evidence, mode))
    evidence.check("summary_path_WNS_consistency", lambda: audit_summary_vs_paths(evidence))
    evidence.check("final_timing_DRVs", lambda: audit_drv(evidence))
    for kind in ("signal", "power", "io_power"):
        evidence.check("final_"+kind+"_connectivity", lambda kind=kind: audit_connectivity(evidence, kind))
    for kind in ("DRC", "antenna", "welltap"):
        evidence.check("final_"+kind, lambda kind=kind: audit_zero_report(evidence, kind))
    evidence.check("final_placement", lambda: audit_placement(evidence))
    evidence.check("completed_stage_provenance", lambda: audit_completed_provenance(evidence))
    evidence.check("inputs_unchanged_during_audit", lambda: audit_unchanged_inputs(evidence))
    statuses = {value["status"] for value in evidence.checks.values()}
    status = "FAIL" if "FAIL" in statuses else "INCOMPLETE" if "INCOMPLETE" in statuses else "PASS"
    return {"schema": "chip-design-postroute-timing-audit-v1", "generated_utc": datetime.now(timezone.utc).isoformat(),
            "pnr_directory": str(evidence.directory), "status": status, "checks": evidence.checks,
            "input_sha256": evidence.hashes,
            "limits": ["Single TT IO timing view and native course RC flow; no multi-corner signoff claim",
                       "Limited report_timing path samples supplement complete timeDesign aggregate counts",
                       "Clockless endpoint coverage, reset timing checks and SDF dynamic correctness require their own audits",
                       "Native IO rail no-routing and Bond-overlay reports require independent physical/native-GDS reconciliation",
                       "No independent foundry DRC/LVS, full CDC, ESD or IR/EM signoff"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pnr", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.pnr)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2)+"\n")
    print(json.dumps({"status": result["status"], "checks": {k: v["status"] for k, v in result["checks"].items()}, "output": str(args.out)}))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
