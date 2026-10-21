#!/usr/bin/env python3
"""Audit Genus and external-pin Xcelium evidence, without running EDA tools.

Python 3.8+, standard library only. Missing stages remain INCOMPLETE. PASS here
means the recorded synthesis/front-end simulation matrix passed; it is not
place-and-route, formal equivalence, CDC, DFT, or foundry signoff.
"""
import argparse
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
NUMBER = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"
IDENT = r"(?:\\[^\s]+|[a-zA-Z_$][\w$]*)"
TIME_NS = {"s": 1e9, "ms": 1e6, "us": 1e3, "ns": 1., "ps": .001, "fs": .000001}


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def read(path):
    if not path.is_file():
        return ""
    if path.suffix == ".gz":
        with gzip.open(str(path), "rt", errors="replace") as handle:
            return handle.read()
    return path.read_text(errors="replace")


def issue(stage, message, failure=False):
    stage["issues"].append({"severity": "FAIL" if failure else "INCOMPLETE", "message": message})


def status(stage):
    levels = [item["severity"] for item in stage["issues"]]
    stage["status"] = "FAIL" if "FAIL" in levels else "INCOMPLETE" if levels else "PASS"
    return stage


def load_json(path, stage):
    if not path.is_file():
        issue(stage, "Missing " + str(path))
        return {}
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError) as exc:
        issue(stage, "Unreadable JSON " + str(path) + ": " + str(exc), True)
        return {}


def source_key(name):
    name = name.replace("\\", "/")
    for marker in ("rtl/", "eda/"):
        if name.startswith(marker):
            return name
        if "/" + marker in name:
            return marker + name.split("/" + marker, 1)[1]
    return name


def source_map(values):
    return {source_key(name): value for name, value in values.items()}


def complete_rtl_tree(stage, values, label):
    """Compare the whole tree, including includes and filelists, not a subset."""
    recorded = {key: value for key, value in source_map(values).items() if key.startswith("rtl/")}
    current = {path.relative_to(ROOT).as_posix(): sha(path) for path in (ROOT / "rtl").rglob("*") if path.is_file()}
    missing = sorted(set(current) - set(recorded))
    extra = sorted(set(recorded) - set(current))
    changed = sorted(key for key in set(current) & set(recorded) if current[key] != recorded[key])
    stage[label] = {"current_files": len(current), "recorded_files": len(recorded),
                    "missing": missing, "extra": extra, "changed": changed}
    if not recorded:
        issue(stage, "Complete RTL source snapshot is missing")
    elif missing or extra or changed:
        issue(stage, "Complete RTL tree differs from " + label, True)
    return recorded


def option_values(command, option):
    return [str(command[index + 1]) for index, value in enumerate(command[:-1]) if value == option]


def parameter_value(command, parameter):
    prefix = "tb_soc_pins." + parameter + "="
    return [value[len(prefix):] for value in option_values(command, "-defparam") if value.startswith(prefix)]


def quoted_path(value):
    return value.strip().strip('"').replace('\\"', '"')


def check_sources(stage, values):
    missing, changed, checked = [], [], 0
    for name, expected in values.items():
        key = source_key(name)
        if not key.startswith(("rtl/", "eda/")):
            continue  # Licensed simulator/library inputs can live only on the server.
        path = ROOT / key
        if not path.is_file():
            missing.append(key)
        elif sha(path) != expected:
            changed.append(key)
        else:
            checked += 1
    stage["current_project_sources"] = {"matched": checked, "missing": missing, "changed": changed}
    if not checked:
        issue(stage, "No project input hashes could be checked")
    if missing:
        issue(stage, "Project inputs unavailable: " + ", ".join(missing[:10]))
    if changed:
        issue(stage, "Project inputs differ from run hashes: " + ", ".join(changed[:10]), True)


def raw_errors(text):
    """Actual diagnostics, not message-count tables or zero-error summaries."""
    return [line for line in text.splitlines()
            if re.search(r"^\s*(?:Error|Fatal)\s*:|\*[EF],[A-Za-z0-9_]+", line, re.I)
            and not re.search(r"\b(?:errors?|fatals?)\s*:\s*0\b", line, re.I)]


def hierarchy(text, top="my_soc_top"):
    text = re.sub(r"/\*.*?\*/|//[^\n]*", "", text, flags=re.S)
    modules = {}
    for match in re.finditer(r"\bmodule\s+(" + IDENT + r")\s*(.*?);(.*?)\bendmodule\b", text, re.S):
        name = match[1].lstrip("\\")
        instances = {}
        for statement in match[3].split(";"):
            instance = re.match(r"\s*(" + IDENT + r")\s+(" + IDENT + r")\s*\((.*)\)\s*$", statement, re.S)
            if instance and re.search(r"\." + IDENT + r"\s*\(", instance[3]):
                master, inst = instance[1].lstrip("\\"), instance[2].lstrip("\\")
                if inst in instances:
                    raise ValueError("Duplicate instance " + name + "/" + inst)
                instances[inst] = master
        modules[name] = instances
    if top not in modules:
        raise ValueError("Mapped netlist has no top module " + top)
    paths = {}

    def walk(module, prefix="", ancestors=()):
        if module in ancestors:
            raise ValueError("Recursive netlist hierarchy at " + prefix)
        for inst, master in modules[module].items():
            name = prefix + inst
            paths[name] = master
            if master in modules:
                walk(master, name + "/", ancestors + (module,))

    walk(top)
    return modules, paths


def sdf_hierarchy(stage, netlist, sdf):
    modules, paths = hierarchy(netlist)
    macros = {name: master for name, master in paths.items() if master == "RA1SHD_2048x32M8"}
    stage["mapped_hierarchy"] = {"modules": len(modules), "instances": len(paths), "sram_instances": macros}
    if len(macros) != 1:
        issue(stage, "Expected exactly one RA1SHD_2048x32M8 SRAM macro, got " + str(len(macros)), True)
    divider = re.search(r"\(DIVIDER\s+(\S+)\s*\)", sdf)
    divider = divider[1] if divider else "/"
    cells = re.findall(r'\(CELLTYPE\s+"([^\"]+)"\)\s*\(INSTANCE\s*([^)]*)\)', sdf)
    mismatches, matched = [], 0
    for master, instance in cells:
        # In Genus SDF DIVIDER='.', escaped '\\.' is part of an instance
        # identifier, while an unescaped '.' separates hierarchy components.
        # Replacing all dots after removing escapes corrupts generate names.
        name, position, original = "", 0, instance.strip()
        while position < len(original):
            char = original[position]
            if char == "\\" and position + 1 < len(original):
                position += 1
                name += original[position]
            else:
                name += "/" if char == divider else char
            position += 1
        if not name:
            if master != "my_soc_top":
                mismatches.append([name, master, "my_soc_top"])
            continue
        if paths.get(name) != master:
            mismatches.append([name, master, paths.get(name)])
        else:
            matched += 1
    arcs = len(re.findall(r"\(IOPATH\b|\(INTERCONNECT\b", sdf))
    stage["sdf_structure"] = {"cell_records": len(cells), "matched_instances": matched,
                              "delay_arc_records": arcs, "mismatches": mismatches[:30]}
    if not matched or not arcs:
        issue(stage, "SDF has no matched instance timing data", True)
    if mismatches:
        issue(stage, "SDF instances/cell types disagree with mapped netlist", True)


def parse_reports(stage, folder):
    area, setup, clocks, units = (read(folder / (name + ".rpt")) for name in ("area", "setup", "clocks", "units"))
    match = re.search(r"(?m)^my_soc_top\s+(?:\S+\s+)?(\d+)\s+(" + NUMBER + r")\s+(" + NUMBER + r")", area)
    if match:
        stage["area"] = {"cell_count": int(match[1]), "cell_area_um2": float(match[2]),
                         "net_area_um2": float(match[3]), "scope": "Genus physical-library area estimate, not die area"}
    else:
        issue(stage, "Could not parse top-level physical area report")
    slacks = re.findall(r"Path\s+\d+:\s+(MET|VIOLATED)\s*\(\s*(" + NUMBER + r")\s*(fs|ps|ns|us)\s*\)\s+Setup", setup, re.I)
    if slacks:
        values = [(-abs(float(value)) if met.upper() == "VIOLATED" else float(value)) * TIME_NS[unit.lower()]
                  for met, value, unit in slacks]
        stage["setup"] = {"worst_reported_slack_ns": min(values), "reported_paths": len(values),
                          "scope": "Worst paths reported by Genus; estimated pre-layout interconnect"}
        if min(values) < 0:
            issue(stage, "Genus setup timing has a negative reported slack", True)
        unit = slacks[0][2].lower()
    else:
        issue(stage, "No explicit-unit Genus setup path could be parsed")
        unit = None
    stage["units_report_raw"] = units
    if not re.search(r"Time_unit\s*:", units):
        issue(stage, "Missing library units report")
    periods = {}
    for clock in ("sys_clk", "jtag_clk", "virtual_jtag_tck"):
        match = re.search(r"(?m)^\s*\S+\s+" + clock + r"\s+(" + NUMBER + r")\s+" + NUMBER + r"\s+" + NUMBER, clocks)
        if match and unit:
            periods[clock] = float(match[1]) * TIME_NS[unit]
    stage["clock_periods_ns"] = periods
    for clock, expected in (("sys_clk", 20.), ("jtag_clk", 100.), ("virtual_jtag_tck", 1000.)):
        if clock not in periods:
            issue(stage, "Cannot verify period of " + clock)
        elif abs(periods[clock] - expected) > 1e-6:
            issue(stage, clock + " period differs from fixed baseline", True)


def synthesis(folder, snapshot_path=None):
    stage = {"directory": str(folder) if folder else None, "issues": []}
    if not folder or not folder.is_dir():
        issue(stage, "Synthesis evidence directory missing")
        return status(stage), {}
    manifest = load_json(folder / "manifest.json", stage)
    stage["manifest"] = manifest
    if "exit_code" not in manifest:
        issue(stage, "Genus has no recorded process exit code")
    elif manifest["exit_code"] != 0:
        issue(stage, "Genus process failed", True)
    console = read(folder / "console.log")
    if not re.search(r"(?m)^ASIC_SYNTHESIS_FINISHED\s*$", console):
        issue(stage, "Genus completion marker absent")
    stage["raw_errors"] = raw_errors(console)
    if stage["raw_errors"]:
        issue(stage, "Raw Genus Error/Fatal diagnostics found", True)
    check = read(folder / "reports/check_final.rpt")
    stage["final_link_check"] = [line for line in check.splitlines() if re.search(r"unresolved|empty module", line, re.I)]
    for term in ("unresolved references", "empty modules"):
        if not re.search(r"No\s+" + term + r"\s+in design", check, re.I):
            issue(stage, "Final check does not establish no " + term, bool(check))
    values = manifest.get("source_sha256", {})
    check_sources(stage, values)
    full_sources = complete_rtl_tree(stage, values, "synthesis_complete_rtl_tree")
    snapshot = load_json(snapshot_path, stage) if snapshot_path else manifest.get("source_snapshot")
    if snapshot is not None:
        stage["archival_source_snapshot"] = snapshot
        if snapshot.get("status") != "PASS":
            issue(stage, "Archival source snapshot did not pass", True)
        if source_map(snapshot.get("source_sha256", {})) != full_sources:
            issue(stage, "Archival source snapshot differs from this synthesis RTL", True)
        if snapshot.get("source_revision") != manifest.get("source_revision"):
            issue(stage, "Source snapshot label differs from synthesis revision label", True)
        if not re.fullmatch(r"[0-9a-f]{64}", snapshot.get("archive_sha256", "")):
            issue(stage, "Archival source snapshot has no valid source-archive SHA256", True)
    parse_reports(stage, folder / "reports")
    stage["outputs"] = {}
    for path in sorted((folder / "outputs").glob("*")):
        if path.is_file():
            stage["outputs"][path.name] = {"bytes": path.stat().st_size, "sha256": sha(path)}
    for name in ("my_soc_top_postsyn.v", "my_soc_top_tt.sdf", "my_soc_top.sdc"):
        if not stage["outputs"].get(name, {}).get("bytes"):
            issue(stage, "Missing/nonempty synthesis output: " + name)
    try:
        if all((folder / "outputs" / name).is_file() for name in ("my_soc_top_postsyn.v", "my_soc_top_tt.sdf")):
            sdf_hierarchy(stage, read(folder / "outputs/my_soc_top_postsyn.v"), read(folder / "outputs/my_soc_top_tt.sdf"))
    except (ValueError, OSError) as exc:
        issue(stage, "Mapped netlist/SDF audit: " + str(exc), True)
    return status(stage), source_map(values)


def simulation(folder, mode, syn_sources, syn_stage, firmware):
    stage = {"directory": str(folder) if folder else None, "issues": [], "cases": []}
    if not folder or not folder.is_dir():
        issue(stage, mode + " evidence directory missing")
        return status(stage)
    results = load_json(folder / "results.json", stage)
    stage["recorded_status"] = results.get("status")
    if results.get("status") != "PASS":
        issue(stage, "Runner status is not PASS", results.get("status") == "FAIL")
    if results.get("mode") != mode:
        issue(stage, "Simulation mode does not match requested stage", True)
    for key, expected in (("sys_period_ns", 20.), ("tck_period_ns", 100.)):
        if results.get(key) != expected:
            issue(stage, key + " differs from fixed baseline", True)
    values = results.get("sources_sha256", {})
    check_sources(stage, values)
    normalized = source_map(values)
    if mode == "rtl":
        complete_rtl_tree(stage, values, "simulation_complete_rtl_tree")
        unmatched = [key for key, value in syn_sources.items() if normalized.get(key) != value]
        stage["synthesis_rtl_source_comparison"] = {"compared": len(syn_sources), "mismatches": unmatched}
        if not syn_sources:
            issue(stage, "Synthesis RTL hash set unavailable for cross-stage comparison")
        elif unmatched:
            issue(stage, "RTL simulation and synthesis did not use identical RTL", True)
    else:
        net_hash = syn_stage.get("outputs", {}).get("my_soc_top_postsyn.v", {}).get("sha256")
        if not net_hash:
            issue(stage, "Synthesis netlist hash unavailable")
        elif net_hash not in values.values():
            issue(stage, "Gate simulation did not use this synthesis netlist hash", True)
        if mode == "sdf":
            sdf_hash = syn_stage.get("outputs", {}).get("my_soc_top_tt.sdf", {}).get("sha256")
            if not sdf_hash:
                issue(stage, "Synthesis SDF hash unavailable")
            elif sdf_hash not in values.values():
                issue(stage, "Timed simulation did not use this synthesis SDF hash", True)
            annotated_copy = folder / "annotate.sdf"
            if not annotated_copy.is_file():
                issue(stage, "Actual annotation SDF copy missing")
            else:
                stage["annotated_sdf_sha256"] = sha(annotated_copy)
                if sdf_hash and stage["annotated_sdf_sha256"] != sdf_hash:
                    issue(stage, "Actual annotation SDF differs from the synthesis output", True)
            compiled = folder / "annotate.sdf.X"
            compile_record = results.get("sdf_compile", {})
            compile_command = compile_record.get("command", [])
            stage["sdf_compile"] = compile_record
            if compile_record.get("status") != "PASS" or compile_record.get("exit_code") != 0:
                issue(stage, "SDF compiler did not record successful completion", True)
            if not compiled.is_file() or not compiled.stat().st_size:
                issue(stage, "Compiled SDF binary is missing")
            else:
                stage["compiled_sdf_sha256"] = sha(compiled)
                if stage["compiled_sdf_sha256"] != compile_record.get("compiled_sha256"):
                    issue(stage, "Compiled SDF binary hash differs from run record", True)
            compile_outputs = option_values(compile_command, "-output")
            if len(compile_outputs) != 1 or source_key(compile_outputs[0]) != source_key(str(compiled)):
                issue(stage, "SDF compiler output path differs from actual compiled binary", True)
            if not any(source_key(str(arg)) == source_key(str(annotated_copy)) for arg in compile_command):
                issue(stage, "SDF compiler command did not use the verified annotation source", True)
            compile_json = load_json(folder / "sdf_compile.json", stage)
            if compile_json != compile_record:
                issue(stage, "SDF compilation artifact and simulation record disagree", True)
            compile_errors = raw_errors(read(folder / "sdf_compile.log"))
            if compile_errors:
                issue(stage, "Raw SDF compiler Error/Fatal diagnostic found", True)
    checks = results.get("checks", [])
    names = [record.get("name") for record in checks]
    required = ["synthetic", "dma"] + (["corrupt_download"] if mode == "rtl" else [])
    for name in required:
        if name not in names:
            issue(stage, "Required case missing: " + name)
    if len(names) != len(set(names)):
        issue(stage, "Duplicate case records", True)
    for record in checks:
        name = record.get("name", "")
        item = {"name": name, "issues": [], "recorded_status": record.get("status"),
                "image_sha256": record.get("image_sha256"), "exit_code": record.get("exit_code")}
        stage["cases"].append(item)
        case = firmware.get("cases", {}).get("synthetic" if name == "corrupt_download" else name, {})
        if not case or record.get("image_sha256") != case.get("sha256"):
            issue(item, "Firmware differs from frozen manifest", True)
        command = record.get("command", [])
        if not command:
            issue(item, "Simulator command absent")
        actual_command = load_json(folder / name / "command.json", item)
        if actual_command != command:
            issue(item, "Case command.json differs from recorded simulator command", True)
        command_text = " ".join(str(value) for value in command)
        images = parameter_value(command, "INIT_FILE")
        if len(images) != 1:
            issue(item, "Simulator command must select exactly one firmware image", True)
        elif case:
            image_path = ROOT / "eda/sim/firmware" / case["image"]
            if source_key(quoted_path(images[0])) != source_key(str(image_path)) or not image_path.is_file() or sha(image_path) != record.get("image_sha256"):
                issue(item, "Executed firmware path/hash differs from frozen case image", True)
        if mode != "rtl":
            used_netlists = [arg for arg in command if source_map(values).get(source_key(str(arg))) == net_hash]
            if len(used_netlists) != 1:
                issue(item, "Executed command does not identify exactly this synthesis netlist", True)
        for parameter, expected in (("CLK_PERIOD_NS", 20.), ("TCK_PERIOD_NS", 100.), ("BOOTS", 2.)):
            match = re.search(r"tb_soc_pins\." + parameter + r"=(" + NUMBER + r")\b", command_text)
            if not match or float(match[1]) != expected:
                issue(item, "Command does not establish " + parameter + "=" + str(expected), True)
        console = read(folder / name / "console.log")
        item["evidence"] = [line for line in console.splitlines() if line.startswith(("PIN_", "SOC_PINS"))]
        errors = raw_errors(console)
        item["simulator_errors"] = errors
        if record.get("status") != "PASS":
            issue(item, "Case not PASS", record.get("status") == "FAIL")
        if name == "corrupt_download":
            if not record.get("exit_code") or "SRAM verify word=7" not in console or "SOC_PINS PASS" in console or "PIN_CPU_PASS" in console:
                issue(item, "Negative corrupted-download test did not fail at its intended check", True)
        else:
            boots = re.findall(r"PIN_CPU_PASS run=(\d+) magic=c0dec0de", console)
            if record.get("exit_code") != 0 or errors or boots != ["0", "1"] or "SOC_PINS PASS downloaded_words=2048 verified_words=2048 boots=2" not in console:
                issue(item, "Raw simulator log does not establish two verified firmware boots", True)
        if mode == "sdf":
            if results.get("functional_timing_checks_disabled") is not False or re.search(r"notiming|nospecify|delay_mode_zero|sdf_no", command_text, re.I):
                issue(item, "Timed run disabled timing/specify checks", True)
            annotation = read(folder / name / "sdf_annotation.log")
            # Cadence -sdfstats lists UNannotated objects, not successful
            # annotation counts. The positive statistics are in xrun stdout.
            unannotated_path = folder / name / "sdf_unannotated.log"
            item["sdf_unannotated_log_bytes"] = unannotated_path.stat().st_size if unannotated_path.exists() else None
            item["sdf_annotation_raw"] = annotation
            item["sdf_annotation_bytes"] = len(annotation.encode())
            item["sdf_request_raw"] = [line for line in console.splitlines() if line.startswith("PIN_SDF_REQUEST")]
            command_file = folder / name / "sdf_annotation.cmd"
            command_raw = read(command_file)
            item["sdf_command_raw"] = command_raw
            settings = re.findall(r'(\w+)\s*=\s*("[^"]*"|[^,;]+)\s*[,;]', command_raw)
            settings_dict = {key: quoted_path(value) for key, value in settings}
            cli_annotation = len(settings) == 4 and set(settings_dict) == {"COMPILED_SDF_FILE", "SCOPE", "LOG_FILE", "MTM_CONTROL"}
            if not cli_annotation or settings_dict.get("SCOPE") != "tb_soc_pins.dut":
                issue(item, "SDF control file does not select exactly the full SoC DUT scope", True)
            command_files = option_values(command, "-sdf_cmd_file")
            if len(command_files) != 1 or source_key(command_files[0]) != source_key(str(command_file)):
                issue(item, "Executed command did not select this verified SDF control file", True)
            if source_key(settings_dict.get("COMPILED_SDF_FILE", "")) != source_key(str(folder / "annotate.sdf.X")):
                issue(item, "SDF control file does not select the verified compiled binary", True)
            if source_key(settings_dict.get("LOG_FILE", "")) != source_key(str(folder / name / "sdf_annotation.log")):
                issue(item, "SDF control file log destination differs from actual annotation log", True)
            if settings_dict.get("MTM_CONTROL") != results.get("sdf_corner") or results.get("sdf_corner") not in ("MINIMUM", "TYPICAL", "MAXIMUM"):
                issue(item, "SDF min/typ/max selection differs from the run record", True)
            if cli_annotation:
                if not command_file.is_file() or sha(command_file) != record.get("sdf_command_sha256"):
                    issue(item, "SDF command-file hash differs from the executed run record", True)
                if results.get("sdf_compile", {}).get("status") != "PASS" or results.get("sdf_compile", {}).get("exit_code") != 0:
                    issue(item, "SDF compiler did not record a successful exit", True)
                item["sdf_request_raw"] += [line for line in console.splitlines()
                                            if "Compiled SDF file:" in line or "Backannotation scope:" in line or "MTM control:" in line]
            actual_scopes = re.findall(r"Backannotation scope:\s*(\S+)", console)
            actual_corners = re.findall(r"MTM control:\s*(\S+)", console)
            if actual_scopes != ["tb_soc_pins.dut"] or actual_corners != [results.get("sdf_corner")]:
                issue(item, "Simulator did not confirm the exact full-SoC annotation scope/corner", True)
            problems = [line for line in (console + "\n" + annotation).splitlines()
                        if re.search(r"\*W,(?:SDF\w+|TIM\w+)|timing violation|\*[EF],", line, re.I)]
            item["sdf_timing_diagnostics"] = problems
            if problems:
                issue(item, "SDF annotation/timing diagnostics found", True)
            if not item["sdf_request_raw"] or not annotation or "Annotation completed successfully" not in console:
                issue(item, "Actual SDF annotation evidence missing")
            # A nonempty annotation log alone can describe an unsuccessful/no-op annotation.
            statistics = [line for line in console.splitlines()
                          if re.search(r"No\. of (?:Pathdelays|Tchecks).*Annotated", line)]
            item["sdf_annotation_statistics_raw"] = statistics
            counts = [int(value) for value in re.findall(r"Annotated\s*=\s*[\d.]+%\s*\((\d+)/\d+\)", "\n".join(statistics))]
            item["sdf_annotated_elements"] = sum(counts)
            if len(counts) != 2 or min(counts) <= 0:
                issue(item, "No positive annotated timing-arc/count statistics established; inspect raw annotation log")
            if record.get("sdf_annotated_elements") != sum(counts) or record.get("sdf_annotation_statistics_raw") != statistics:
                issue(item, "Runner annotation statistics differ from raw simulator output", True)
        status(item)
        for problem in item["issues"]:
            issue(stage, name + ": " + problem["message"], problem["severity"] == "FAIL")
    return status(stage)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for name in ("synthesis", "rtl", "gate", "sdf"):
        ap.add_argument("--" + name, type=Path, help="Evidence output directory for this stage")
    ap.add_argument("--out", type=Path, required=True, help="Write JSON summary here, never into source/output inputs")
    ap.add_argument("--source-snapshot", type=Path, help="Optional independently captured full RTL archive identity JSON")
    args = ap.parse_args()
    for name in ("synthesis", "rtl", "gate", "sdf"):
        folder = getattr(args, name)
        if folder and args.out.resolve() == (folder / "results.json").resolve():
            ap.error("--out must not replace a stage results.json")
    result = {"generated_utc": datetime.now(timezone.utc).isoformat(),
              "scope": "Complete CPU+DMA+NPU SoC synthesis and external-pin functional/timed simulation evidence",
              "limitations": ["No formal equivalence or CDC proof", "No place-and-route or physical signoff",
                              "Synthesis SDF uses estimated pre-layout interconnect", "Passing simulations cover the recorded test matrix"],
              "issues": []}
    syn, sources = synthesis(args.synthesis, args.source_snapshot)
    result["synthesis"] = syn
    firmware = load_json(ROOT / "eda/sim/firmware/manifest.json", result)
    for mode in ("rtl", "gate", "sdf"):
        result[mode] = simulation(getattr(args, mode), mode, sources, syn, firmware)
    for name in ("synthesis", "rtl", "gate", "sdf"):
        if result[name]["status"] != "PASS":
            issue(result, name + " stage is " + result[name]["status"], result[name]["status"] == "FAIL")
    status(result)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"status": result["status"], "stages": {name: result[name]["status"] for name in ("synthesis", "rtl", "gate", "sdf")},
                      "summary": str(args.out)}, indent=2))
    return {"PASS": 0, "INCOMPLETE": 2, "FAIL": 1}[result["status"]]


if __name__ == "__main__":
    sys.exit(main())
