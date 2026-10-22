#!/usr/bin/env python3
"""Run/audit external-pin post-route Xcelium tests, Python 3.8 standard library.

Inputs: the functional hierarchical saveNetlist -removePowerGround output,
post-route SDF, and licensed standard-cell/SRAM/IO Verilog models. Do not use
the flat LVS netlist. The original tb_soc_pins.sv and firmware remain untouched.
With six top-level functional ports the frozen testbench is compiled directly.
If the physical top additionally exposes supply ports, a generated outer wrapper
connects those top-level ports; only the DUT module binding in a derived copy of
the frozen testbench changes. Leaf-model port mismatches are always errors.

Example (source the course EDA environment first):
  python3 eda/pnr/run_postroute.py --netlist /path/my_soc_top_hier_postpnr.v \
      --sdf /path/my_soc_top_tt_io.sdf.gz --out eda/work/postroute-sim-final
  python3 eda/pnr/run_postroute.py --audit-only --out eda/work/postroute-sim-final

No complete simulation is run by --dry-run or --audit-only.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
TB = ROOT / "eda/sim/tb_soc_pins.sv"
FIRMWARE = ROOT / "eda/sim/firmware/manifest.json"
IDENT = r"(?:\\[^\s]+|[a-zA-Z_$][\w$]*)"
FUNCTION_PORTS = {"clk_i", "rst_ni", "tck_i", "tms_i", "td_i", "td_o"}
DEFAULT_SUPPLIES = {"VDD": 1, "VSS": 0, "VDDPST": 1, "VSSPST": 0}
FROZEN_TB_SHA256 = "f18bb96bc71370e6951952579c51eb228123a751ad17b02aac8de46250f678b4"
FROZEN_IMAGES = {
    "synthetic": "29cbca3b259644d244b7c0952e5ebdf68d95990f83aed8375c5239da757264a0",
    "cpu": "7096cfbea06e99bc4d9526fc988804d99258880ed6a56d5b99bed980e45fc599",
    "dma": "54c32dca604287846adf60fca7c0aa9a5125c69dc96dc69ecea6df03bce3689f",
}
BAD_TIMING_OPTIONS = re.compile(
    r"notiming|nospecify|no_tchk|notchk|nonotifier|no_notifier|bus_conflict_off|"
    r"delay_mode|sequdp|seq_udp_delay|add_seq_delay|sdf_no|disable_sem", re.I)


def now():
    return datetime.now(timezone.utc).isoformat()


def sha(path):
    result = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def read(path):
    return path.read_text(errors="replace") if path.is_file() else ""


def save(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def checked(value):
    path = Path(value).expanduser().resolve()
    if not path.is_file():
        raise ValueError("Missing input: " + str(path))
    return path


def within(path, directory):
    try:
        path.relative_to(directory)
        return True
    except ValueError:
        return False


def quoted(value):
    value = str(value).replace("\\", "/")
    if any(char in value for char in '\n\r"'):
        raise ValueError("Unsupported command-file path: " + value)
    return '"' + value + '"'


def expand(source, destination):
    if source.suffix == ".gz":
        with gzip.open(str(source), "rb") as reader, destination.open("wb") as writer:
            for block in iter(lambda: reader.read(1024 * 1024), b""):
                writer.write(block)
    else:
        destination.write_bytes(source.read_bytes())


def modules(text):
    """Parse the non-parameterized named-pin structural Verilog EDA exports."""
    text = re.sub(r"/\*.*?\*/|//[^\n]*", "", text, flags=re.S)
    found = {}
    for match in re.finditer(r"\bmodule\s+(" + IDENT + r")\s*\((.*?)\)\s*;(.*?)\bendmodule\b", text, re.S):
        name = match[1].lstrip("\\")
        header = match[2]
        # EDA netlists and the supplied cell models use non-ANSI headers.
        # Accept ANSI scalar headers too, without confusing direction keywords.
        header = re.sub(r"(?<![\\\w$\]])\[[^]]*\]", "", header)
        ports = []
        for item in header.split(",") if header.strip() else []:
            names = re.findall(IDENT, item)
            names = [word for word in names if word not in {"input", "output", "inout", "wire", "reg", "logic", "signed"}]
            if len(names) != 1:
                raise ValueError("Cannot parse module header " + name + ": " + item.strip())
            ports.append(names[0].lstrip("\\"))
        instances = {}
        for statement in match[3].split(";"):
            inst = re.match(r"\s*(" + IDENT + r")\s+(" + IDENT + r")\s*\((.*)\)\s*$", statement, re.S)
            if not inst:
                continue
            master, instance = inst[1].lstrip("\\"), inst[2].lstrip("\\")
            # Primitive gates are represented in the models, not the netlist.
            if master in {"buf", "not", "and", "or", "nor", "nand", "xor", "xnor", "tran", "bufif0", "bufif1", "pmos", "nmos"}:
                continue
            pin_names = [pin.lstrip("\\") for pin in re.findall(r"\.\s*(" + IDENT + r")\s*\(", inst[3])]
            if inst[3].strip() and not pin_names:
                raise ValueError("Positional netlist instance unsupported: " + name + "/" + instance)
            if instance in instances:
                raise ValueError("Duplicate instance: " + name + "/" + instance)
            connected = [pin.lstrip("\\") for pin, expression in re.findall(
                r"\.\s*(" + IDENT + r")\s*\(([^()]*)\)", inst[3]) if expression.strip()]
            instances[instance] = {"master": master, "pins": pin_names, "connected_pins": connected}
        if name in found:
            raise ValueError("Duplicate module definition: " + name)
        found[name] = {"ports": ports, "instances": instances}
    return found


def model_ports(text):
    """Only headers are needed; model internals/UDPs are deliberately untouched."""
    text = re.sub(r"/\*.*?\*/|//[^\n]*", "", text, flags=re.S)
    result = {}
    for match in re.finditer(r"\bmodule\s+(" + IDENT + r")\s*\((.*?)\)\s*;", text, re.S):
        header = re.sub(r"(?<![\\\w$\]])\[[^]]*\]", "", match[2])
        names = []
        for entry in header.split(","):
            tokens = [token for token in re.findall(IDENT, entry)
                      if token not in {"input", "output", "inout", "wire", "reg", "logic", "signed"}]
            if tokens:
                names.append(tokens[-1].lstrip("\\"))
        result[match[1].lstrip("\\")] = set(names)
    return result


def binding_ports(text):
    """Ports and literal-range bit selects that an SDF endpoint can bind.

    Named Verilog instance ports still use model_ports(); this separate set
    admits A[10] only when A really has that declared bit. Unresolved parameter
    ranges are deliberately not guessed. The course exports/models have
    elaborated, literal port widths.
    """
    headers = model_ports(text)
    result = {name: set(ports) for name, ports in headers.items()}
    clean = re.sub(r"/\*.*?\*/|//[^\n]*", "", text, flags=re.S)
    for match in re.finditer(r"\bmodule\s+(" + IDENT + r")\s*\((.*?)\)\s*;(.*?)\bendmodule\b", clean, re.S):
        name = match[1].lstrip("\\")
        declarations = re.findall(r"\b(?:input|output|inout)\s+([^;]+);", match[3])
        # ANSI scalar/vector headers are accepted as well as non-ANSI models.
        declarations += re.findall(r"\b(?:input|output|inout)\s+(.+?)(?=,\s*(?:input|output|inout)\b|$)", match[2], re.S)
        for declaration in declarations:
            width = re.match(r"\s*(?:(?:wire|reg|logic|signed|unsigned)\s+)*\[\s*(-?\d+)\s*:\s*(-?\d+)\s*\]", declaration)
            if not width:
                continue
            a, b = map(int, width.groups())
            if abs(a-b) > 1048576:
                raise ValueError("Unreasonable literal port width in " + name)
            names = re.findall(IDENT, declaration[width.end():])
            for pin in names:
                pin = pin.lstrip("\\")
                if pin in headers[name]:
                    result[name].update(pin + "[" + str(bit) + "]" for bit in range(min(a, b), max(a, b)+1))
    return result


def sdf_path(token, divider):
    """Decode identifiers without turning escaped literal dividers into paths."""
    token = token.strip()
    if token.startswith('"') and token.endswith('"'):
        token = token[1:-1]
    if not token:
        return []
    parts, part, index = [], [], 0
    while index < len(token):
        char = token[index]
        if char == "\\":
            index += 1
            if index == len(token):
                raise ValueError("Trailing SDF identifier escape: " + token)
            part.append(token[index])
        elif char == divider:
            if not part:
                raise ValueError("Empty SDF path segment: " + token)
            parts.append("".join(part))
            part = []
        else:
            part.append(char)
        index += 1
    if not part:
        raise ValueError("Empty final SDF path segment: " + token)
    return parts + ["".join(part)]


def display_path(parts):
    """Diagnostic text only; tuple segments remain the actual identity keys."""
    return "/".join(part.replace("\\", "\\\\").replace("/", "\\/") for part in parts)


def interconnect_bindings(sdf_text, cell_headers, paths, connected, design, ports, top, divider):
    """Bind every INTERCONNECT endpoint, including root top-level ports.

    A CELL header alone cannot establish wire binding: antenna diodes excluded
    from the functional netlist can still occur only as root INTERCONNECT
    loads. Unknown instances, unknown ports and undeclared vector bits fail.
    """
    token = r'(?:"(?:\\.|[^"\\])*"|(?:\\.|[^\s()])+)'
    arc = re.compile(r"\(\s*INTERCONNECT\s+(" + token + r")\s+(" + token + r")\s*(?=\()")
    total, root_total, top_port_ends, instance_pin_ends = 0, 0, 0, 0
    failures = []
    for index, header in enumerate(cell_headers):
        scope = tuple(sdf_path(header[2], divider))
        end = cell_headers[index+1].start() if index+1 < len(cell_headers) else len(sdf_text)
        body = sdf_text[header.end():end]
        expected = len(re.findall(r"\(\s*INTERCONNECT\b", body))
        found = list(arc.finditer(body))
        if len(found) != expected:
            raise ValueError("Unparsed SDF INTERCONNECT syntax in CELL " + (display_path(scope) or "<root>"))
        for match in found:
            total += 1
            root_total += int(not scope)
            for endpoint in match.groups():
                parts = tuple(sdf_path(endpoint, divider))
                if len(parts) == 1:
                    master = top if not scope else paths.get(scope)
                    valid = master in design and parts[0] in ports.get(master, set())
                    top_port_ends += int(not scope)
                    description = display_path(scope + parts)
                else:
                    instance = scope + parts[:-1]
                    master = paths.get(instance)
                    pin = parts[-1]
                    base_pin = re.sub(r"\[-?\d+\]$", "", pin)
                    has_connection = pin in connected.get(instance, set()) or base_pin in connected.get(instance, set())
                    valid = master is not None and pin in ports.get(master, set()) and has_connection
                    instance_pin_ends += 1
                    description = display_path(instance + (parts[-1],))
                if not valid and len(failures) < 20:
                    failures.append({"cell_scope": display_path(scope), "endpoint": endpoint, "resolved": description,
                                     "master": master, "reason": "Unknown instance, undeclared port/bit or unconnected pin"})
    if failures:
        raise ValueError("SDF INTERCONNECT endpoint binding failed: " + repr(failures))
    if not root_total:
        raise ValueError("SDF has no bound root INTERCONNECT records")
    return {"status": "PASS", "records": total, "root_records": root_total,
            "verified_endpoints": total*2, "root_top_port_endpoints": top_port_ends,
            "instance_pin_endpoints": instance_pin_ends, "unknown_endpoints": [],
            "policy": "Every instance pin and top port must bind; instance pins require nonempty named connections and vector bits require literal declared ranges"}


def structural_audit(netlist, sdf, models, top):
    netlist_text = read(netlist)
    design = modules(netlist_text)
    if top not in design:
        raise ValueError("No physical top module " + top)
    libraries, endpoint_ports = {}, binding_ports(netlist_text)
    for model in models:
        model_text = read(model)
        for name, pins in model_ports(model_text).items():
            if name in libraries and libraries[name] != pins:
                raise ValueError("Conflicting model port declarations for " + name)
            libraries[name] = pins
        for name, pins in binding_ports(model_text).items():
            if name in endpoint_ports and endpoint_ports[name] != pins:
                raise ValueError("Conflicting model SDF port/bit declarations for " + name)
            endpoint_ports[name] = pins
    paths, connected, missing, mismatches = {}, {}, [], []

    def walk(module, prefix=(), ancestors=()):
        if module in ancestors:
            raise ValueError("Recursive hierarchy: " + display_path(prefix))
        for inst, item in design[module]["instances"].items():
            path, master = prefix + (inst,), item["master"]
            if path in paths:
                raise ValueError("Ambiguous hierarchical instance path: " + display_path(path))
            paths[path] = master
            connected[path] = set(item["connected_pins"])
            expected = set(design[master]["ports"]) if master in design else libraries.get(master)
            if expected is None:
                missing.append([display_path(path), master])
            else:
                unknown = sorted(set(item["pins"]) - expected)
                if unknown:
                    mismatches.append([display_path(path), master, unknown[:12]])
            if master in design:
                walk(master, path, ancestors + (module,))
    walk(top)
    if missing or mismatches:
        raise ValueError("Netlist/model linking failed. Missing masters=" + repr(missing[:10]) +
                         "; unknown ports=" + repr(mismatches[:10]) +
                         ". Export the hierarchical functional netlist with -removePowerGround; do not use flat LVS.")
    counts = Counter(paths.values())
    if counts["RA1SHD_2048x32M8"] != 1:
        raise ValueError("Expected one main SRAM macro, got " + str(counts["RA1SHD_2048x32M8"]))
    if counts["PDDW0204CDG"] != 6:
        raise ValueError("Expected six functional IO PADs, got " + str(counts["PDDW0204CDG"]))
    physical_only = {master: count for master, count in counts.items()
                     if re.match(r"(?:FILL\d|PFILLER|TAPCELL|PCORNER|PAD60LU|DCAP|ANTENNA)", master)}
    sdf_text = read(sdf)
    divider = re.search(r"\(DIVIDER\s+(\S+)\s*\)", sdf_text)
    divider = divider[1].strip('"') if divider else "/"
    if len(divider) != 1:
        raise ValueError("Unsupported SDF DIVIDER: " + divider)
    cell_headers = list(re.finditer(r'\(\s*CELLTYPE\s+"([^\"]+)"\)\s*\(\s*INSTANCE\s*([^)]*)\)', sdf_text))
    cells = [match.groups() for match in cell_headers]
    sdf_missing, root_cells = [], 0
    for master, instance in cells:
        path = tuple(sdf_path(instance, divider))
        if not path:
            root_cells += 1
            if master != top:
                sdf_missing.append([display_path(path), master, top])
        elif paths.get(path) != master:
            sdf_missing.append([display_path(path), master, paths.get(path)])
    arc_counts = {name: len(re.findall(r"\(\s*" + name + r"\b", sdf_text))
                  for name in ("IOPATH", "INTERCONNECT", "SETUPHOLD", "RECREM")}
    if not cells or not root_cells or not arc_counts["IOPATH"] or not arc_counts["INTERCONNECT"]:
        raise ValueError("SDF lacks root/instance/cell delay or routed interconnect data")
    if sdf_missing:
        raise ValueError("SDF CELLTYPE/INSTANCE mismatches: " + repr(sdf_missing[:20]))
    bindings = interconnect_bindings(sdf_text, cell_headers, paths, connected, design, endpoint_ports, top, divider)
    if bindings["records"] != arc_counts["INTERCONNECT"]:
        raise ValueError("Some SDF INTERCONNECT records are outside parsed CELL scopes")
    return {"status": "PASS", "top": top, "top_ports": design[top]["ports"],
            "netlist_modules": len(design), "hierarchical_instances": len(paths),
            "main_sram_count": counts["RA1SHD_2048x32M8"], "functional_pad_count": counts["PDDW0204CDG"],
            "supply_pad_counts": {name: count for name, count in counts.items() if re.match(r"PVDD|PVSS", name)},
            "physical_only_instances_in_functional_netlist": physical_only,
            "sdf_cells": len(cells), "sdf_root_cells": root_cells, "sdf_arc_records": arc_counts,
            "sdf_interconnect_binding": bindings,
            "sdf_hierarchy_mismatches": [], "model_port_mismatches": []}


def prepare_testbench(out, top, ports, supplies):
    extra = set(ports) - FUNCTION_PORTS
    absent = FUNCTION_PORTS - set(ports)
    if absent:
        raise ValueError("Physical top lacks functional ports: " + repr(sorted(absent)))
    if extra - set(supplies):
        raise ValueError("Unmapped additional top ports: " + repr(sorted(extra - set(supplies))))
    if not extra and top == "my_soc_top":
        return TB, [], "tb_soc_pins.dut", {"kind": "frozen_testbench_direct", "power_ports": {}}
    wrapper = out / "postroute_supply_wrapper.sv"
    connections = ["." + port + "(" + port + ")" for port in sorted(FUNCTION_PORTS)]
    connections += ["." + port + "(" + ("vdd_sim" if supplies[port] else "vss_sim") + ")" for port in sorted(extra)]
    wrapper.write_text("`timescale 1ns/1ps\nmodule eda_postroute_pad_top(input clk_i,rst_ni,tck_i,tms_i,td_i,output td_o);\n"
                       "  supply1 vdd_sim; supply0 vss_sim;\n  " + top + " i_chip(" + ",".join(connections) + ");\nendmodule\n")
    frozen = read(TB)
    target = "my_soc_top dut (.clk_i(clk_i), .rst_ni(rst_ni), .tck_i(tck_i),"
    if frozen.count(target) != 1:
        raise ValueError("Frozen testbench DUT binding changed; inspect before adapting")
    adapted = out / "tb_soc_pins_postroute.sv"
    adapted.write_text(frozen.replace(target, target.replace("my_soc_top", "eda_postroute_pad_top"), 1))
    return adapted, [wrapper], "tb_soc_pins.dut.i_chip", {
        "kind": "top_port_supply_wrapper", "original_testbench_sha256": sha(TB),
        "derived_testbench_sha256": sha(adapted), "only_testbench_change": "DUT module binding to outer supply wrapper",
        "power_ports": {port: supplies[port] for port in sorted(extra)},
        "leaf_power_pin_policy": "Unknown library model ports are rejected; no leaf power connections are stripped"}


def diagnostics(text):
    r"""Reject incomplete negative-delay compensation as well as SDF errors.

    These four warning forms occurred in the actual raw-SDF MAXIMUM run.
    Successful firmware execution cannot compensate for an unfaithful delay
    model, so none may silently pass the post-route audit.

    >>> samples = (
    ...     "xmelab: *W,NDLMLD: A driver of a net with negative delay (<INTC-NO-NAME>) has multiple loads.",
    ...     "xmelab: *W,NDLPAR: Partial adjustment was done on driver while compensating negative path delay: (tb_soc_pins.dut.i_dm_top.i_dm_csrs.g45962.I0 - tb_soc_pins.dut.i_dm_top.i_dm_csrs.g45962.ZN).",
    ...     "xmelab: *W,NDLNOC: Unable to compensate negative module path delay at tb_soc_pins.dut.i_npu_subsystem.i_npu_core.core.g10983.B1.",
    ...     "xmelab: *W,NDLFAL: 1 negative path delay failed to adjust out of a total of 12.",
    ... )
    >>> errors, rejected = diagnostics("\n".join(samples))
    >>> errors == [] and rejected == list(samples)
    True
    >>> diagnostics("Annotation completed successfully...\nPIN_CPU_PASS run=0 magic=c0dec0de")
    ([], [])
    >>> len(diagnostics("xmelab: *W,SDFNDP: negative delay\nTiming violation in $hold")[1])
    2
    >>> bool(diagnostics("ERROR : 0 ++BUS CONFLICT++ : tb_soc_pins.dut.i_pad_td_o")[0])
    True
    """
    errors, timing = [], []
    for line in text.splitlines():
        if re.search(r"\*[EF],|^\s*(?:ERROR|Fatal)\s*:|\+\+BUS CONFLICT\+\+", line, re.I):
            errors.append(line)
        if re.search(r"\*W,(?:SDF\w+|TIM\w+|NDL\w*)|timing violation", line, re.I):
            timing.append(line)
    return errors, timing


def audit_case(out, record):
    folder = out / record["name"]
    text, annotation = read(folder / "console.log"), read(folder / "sdf_annotation.log")
    errors, timing = diagnostics(text + "\n" + annotation)
    issues = []
    if record.get("status") != "PASS" or record.get("exit_code") != 0:
        issues.append("Simulator did not complete successfully")
    if errors or timing:
        issues.append("Raw simulator/IO/SDF/timing diagnostics found")
    if re.findall(r"PIN_CPU_PASS run=(\d+) magic=c0dec0de", text) != ["0", "1"]:
        issues.append("Two fresh CPU firmware boots not established")
    if "PIN_CONFIG sys_period_ns=20.000 tck_period_ns=100.000 boots=2" not in text:
        issues.append("Actual fixed 20 ns / 100 ns / two-boot configuration missing")
    for marker in ("PIN_IMAGE_VERIFIED words=2048", "PIN_BOOT_VECTOR_READY address=00010000 instruction=800002b7",
                   "SOC_PINS PASS downloaded_words=2048 verified_words=2048 boots=2"):
        if marker not in text:
            issues.append("Missing raw marker: " + marker)
    stats = re.findall(r"^.*No\. of (?:Pathdelays|Tchecks).*Annotated.*$", text, re.M)
    counts = [int(value) for value in re.findall(r"Annotated\s*=\s*[\d.]+%\s*\((\d+)/\d+\)", "\n".join(stats))]
    if not annotation or "Annotation completed successfully" not in text or len(counts) != 2 or min(counts) <= 0:
        issues.append("Actual successful SDF annotation and positive path/timing-check statistics not established")
    command = record.get("command", [])
    if not command or BAD_TIMING_OPTIONS.search(" ".join(command)):
        issues.append("Missing command or forbidden timing/model suppression option")
    if "-sdf_cmd_file" not in command or "+define+NTC+RECREM" not in command or "-negdelay" not in command:
        issues.append("Required actual SDF/model configuration missing")
    metrics = {str(run): {metric: int(value) for metric, value in re.findall(
        r"PIN_BENCH run=" + str(run) + r" metric=(\d+) cycles=(\d+)", text)} for run in (0, 1)}
    if record["name"] in ("cpu", "dma"):
        for values in metrics.values():
            if set(values) != {"0", "1", "2", "3", "4"}:
                issues.append("Missing CPU benchmark metric")
            elif any(values[key] <= 0 for key in ("0", "1", "2", "4")) or ((values["3"] > 0) != (record["name"] == "dma")):
                issues.append("Invalid DMA/CPU benchmark metrics")
        if metrics["0"] != metrics["1"]:
            issues.append("Fresh-boot software benchmark results disagree")
    raw_command = read(folder / "sdf_annotation.cmd")
    if raw_command != record.get("sdf_command_raw") or sha(folder / "sdf_annotation.cmd") != record.get("sdf_command_sha256"):
        issues.append("SDF command file changed from recorded input")
    return {"name": record["name"], "status": "FAIL" if issues else "PASS", "issues": issues,
            "simulator_errors": errors, "timing_diagnostics": timing, "observed_timing_violations": len(timing),
            "benchmark_cycles": metrics, "annotation_statistics_raw": stats,
            "annotation_statistics_denominator": "All potential specify objects in compiled models, not source-SDF requested coverage",
            "annotated_elements": sum(counts), "warning_counts": dict(Counter(re.findall(r"\*W,([A-Z0-9_]+)", text))),
            "evidence": [line for line in text.splitlines() if line.startswith(("PIN_", "SOC_PINS"))]}


def audit(out):
    result = json.loads((out / "results.json").read_text())
    issues, changed = [], []
    for name, expected in result["input_sha256"].items():
        path = Path(name)
        if not path.is_file() or sha(path) != expected:
            changed.append(name)
    if changed:
        issues.append("Input files changed or unavailable")
    for name, expected in result["prepared_sha256"].items():
        path = out / name
        if not path.is_file() or sha(path) != expected:
            issues.append("Prepared simulator input changed: " + name)
    if result.get("structural_audit", {}).get("status") != "PASS":
        issues.append("Structural/model/SDF input audit missing")
    bindings = result.get("structural_audit", {}).get("sdf_interconnect_binding", {})
    if bindings.get("status") != "PASS" or bindings.get("root_records", 0) <= 0 or bindings.get("verified_endpoints") != 2*bindings.get("records", 0):
        issues.append("Complete SDF INTERCONNECT endpoint binding evidence missing")
    compile_info = result.get("sdf_compile", {})
    compiled = out / "annotate.sdf.X"
    if compile_info.get("exit_code") != 0 or not compiled.is_file() or sha(compiled) != compile_info.get("compiled_sha256"):
        issues.append("Compiled SDF evidence missing or changed")
    compile_errors, compile_warnings = diagnostics(read(out / "sdf_compile.log"))
    if compile_errors or compile_warnings:
        issues.append("SDF compiler diagnostics found")
    cases = []
    for record in result["checks"]:
        try:
            cases.append(audit_case(out, record))
        except (OSError, KeyError, ValueError) as exc:
            cases.append({"name": record.get("name"), "status": "FAIL", "issues": [str(exc)]})
    if any(case["status"] != "PASS" for case in cases):
        issues.append("At least one post-route simulation case failed audit")
    names = {case["name"] for case in cases}
    complete = {"synthetic", "dma"}.issubset(names)
    if not complete:
        issues.append("Complete required synthetic+dma matrix not established")
    report = {"generated_utc": now(), "status": "FAIL" if issues else "PASS", "issues": issues,
              "changed_inputs": changed, "cases": cases, "structural_audit": result.get("structural_audit"),
              "scope": "TT post-route SDF pin-level dynamic simulation with IO models; not independent DRC/LVS or complete signoff"}
    save(out / "audit.json", report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--netlist", type=Path)
    parser.add_argument("--sdf", type=Path)
    parser.add_argument("--design-top", default="my_soc_top")
    parser.add_argument("--stdcell-model", type=Path, default=Path("/lec/pdk/tsmc180/tcb018gbwp7t_290a/TSMCHOME/digital/Front_End/verilog/tcb018gbwp7t_270a/tcb018gbwp7t.v"))
    parser.add_argument("--sram-model", type=Path, default=Path("/lec/lab4/soc_cv32e40p_template_pnr-stu/src/macro/RA1SHD_2048x32M8/RA1SHD_2048x32M8.v"))
    parser.add_argument("--io-model", type=Path, default=Path("/lec/pdk/tsmc180/tpd018nv_280a/TSMCHOME/digital/Front_End/verilog/tpd018nv_260a/tpd018nv.v"))
    parser.add_argument("--extra-model", type=Path, action="append", default=[])
    parser.add_argument("--supply", action="append", default=[], help="Additional physical top supply PORT=0 or PORT=1; repeat")
    parser.add_argument("--only", choices=("synthetic", "dma", "cpu"), action="append")
    parser.add_argument("--sdf-corner", choices=("MAXIMUM", "TYPICAL", "MINIMUM"), default="MAXIMUM")
    parser.add_argument("--out", type=Path)
    parser.add_argument("--xrun", default="xrun")
    parser.add_argument("--xmsdfc", default="xmsdfc")
    parser.add_argument("--timeout", type=int, default=10800, help="Wall-clock seconds per case")
    parser.add_argument("--xrun-arg", action="append", default=[])
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--audit-only", action="store_true")
    args = parser.parse_args()
    if args.audit_only:
        if not args.out:
            parser.error("--audit-only requires --out")
        if not within(args.out.resolve(), ROOT / "eda/work"):
            parser.error("Audit side effects must stay under this repository's eda/work/")
        report = audit(args.out.resolve())
        print(json.dumps({"status": report["status"], "audit": str(args.out.resolve() / "audit.json")}, indent=2))
        return 0 if report["status"] == "PASS" else 1
    if not args.netlist or not args.sdf or args.timeout <= 0:
        parser.error("Provide --netlist and --sdf and a positive --timeout")
    if any(BAD_TIMING_OPTIONS.search(option) for option in args.xrun_arg):
        parser.error("Post-route timing checks and library behavior cannot be suppressed/retimed")
    if not re.fullmatch(r"[a-zA-Z_$][\w$]*", args.design_top):
        parser.error("Unsupported physical top identifier")
    out = (args.out or ROOT / "eda/work" / ("postroute-sim-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))).resolve()
    if not within(out, ROOT / "eda/work"):
        parser.error("Simulation side effects must stay under this repository's eda/work/")
    if out.exists() and any(out.iterdir()):
        parser.error("Choose a fresh --out directory")
    supplies = dict(DEFAULT_SUPPLIES)
    for entry in args.supply:
        match = re.fullmatch(r"([a-zA-Z_$][\w$]*)=([01])", entry)
        if not match:
            parser.error("Expected --supply PORT=0 or PORT=1")
        supplies[match[1]] = int(match[2])
    selected = args.only or ["synthetic", "dma"]
    if len(selected) != len(set(selected)):
        parser.error("Duplicate --only cases")
    inputs = [checked(args.netlist), checked(args.sdf)]
    models = [checked(args.stdcell_model), checked(args.sram_model), checked(args.io_model)] + [checked(value) for value in args.extra_model]
    firmware = json.loads(FIRMWARE.read_text())
    if sha(TB) != FROZEN_TB_SHA256:
        raise ValueError("Frozen pin-level testbench changed; review before accepting a new test contract")
    images = {name: checked(FIRMWARE.parent / firmware["cases"][name]["image"]) for name in selected}
    for name, image in images.items():
        words = image.read_text().split()
        if sha(image) != firmware["cases"][name]["sha256"] or sha(image) != FROZEN_IMAGES[name] or len(words) != 2048 or any(not re.fullmatch(r"[0-9a-fA-F]{8}", word) for word in words):
            raise ValueError("Frozen firmware invalid/changed: " + name)
    input_paths = sorted(set(inputs + models + [TB, FIRMWARE, Path(__file__).resolve()] + list(images.values())))
    out.mkdir(parents=True, exist_ok=True)
    netlist, sdf = out / "postroute.v", out / "annotate.sdf"
    expand(inputs[0], netlist)
    expand(inputs[1], sdf)
    structural = structural_audit(netlist, sdf, models, args.design_top)
    tb, wrappers, scope, binding = prepare_testbench(out, args.design_top, structural["top_ports"], supplies)
    prepared = [netlist, sdf] + wrappers + ([tb] if tb != TB else [])
    result = {"started_utc": now(), "status": "PREPARED" if args.dry_run else "RUNNING",
              "mode": "postroute_sdf", "sys_period_ns": 20, "tck_period_ns": 100, "boots": 2,
              "sdf_corner": args.sdf_corner, "functional_timing_checks_disabled": False,
              "annotation_scope": scope, "testbench_binding": binding, "structural_audit": structural,
              "input_sha256": {str(path): sha(path) for path in input_paths},
              "prepared_sha256": {path.relative_to(out).as_posix(): sha(path) for path in prepared},
              "checks": [], "limitations": ["No waveforms requested/generated", "Single selected SDF corner; no independent DRC/LVS, formal equivalence or full signoff"]}
    save(out / "results.json", result)
    compiled = out / "annotate.sdf.X"
    compile_command = [args.xmsdfc, "-64bit", str(sdf), "-output", str(compiled)]
    result["sdf_compile"] = {"command": compile_command, "status": "PREPARED"}
    if not args.dry_run:
        with (out / "sdf_compile.log").open("wb") as log:
            process = subprocess.run(compile_command, cwd=str(out), stdout=log, stderr=subprocess.STDOUT, timeout=args.timeout)
        result["sdf_compile"].update(exit_code=process.returncode, status="PASS" if process.returncode == 0 and compiled.is_file() else "FAIL")
        if compiled.is_file():
            result["sdf_compile"]["compiled_sha256"] = sha(compiled)
        save(out / "results.json", result)
        if result["sdf_compile"]["status"] != "PASS" or any(diagnostics(read(out / "sdf_compile.log"))):
            result["status"] = "FAIL"
            save(out / "results.json", result)
            raise RuntimeError("SDF compiler failed; inspect " + str(out / "sdf_compile.log"))
    for name in selected:
        folder = out / name
        folder.mkdir()
        command_file = folder / "sdf_annotation.cmd"
        command_file.write_text("COMPILED_SDF_FILE = " + quoted(compiled) + ",\nSCOPE = " + scope + ",\nLOG_FILE = " + quoted(folder / "sdf_annotation.log") + ",\nMTM_CONTROL = " + quoted(args.sdf_corner) + ";\n")
        command = [args.xrun, "-64bit", "-sv", "-timescale", "1ns/1ps", "+define+NTC+RECREM", "-negdelay", str(netlist)]
        command += [str(path) for path in models + wrappers] + [str(tb), "-top", "tb_soc_pins", "-l", str(folder / "xrun.log"),
                    "-sdf_cmd_file", str(command_file), "-sdfstats", str(folder / "sdf_unannotated.log")]
        parameters = {"INIT_FILE": quoted(images[name]), "CLK_PERIOD_NS": 20.0, "TCK_PERIOD_NS": 100.0,
                      "BOOTS": 2, "EXPECT_DMA": int(name == "dma"), "BENCHMARK": int(name in ("cpu", "dma")),
                      "CORRUPT_WORD": -1, "QUIET_CYCLES": 100000, "MAX_POLLS": 2000, "WATCHDOG_NS": 250000000.0}
        for key, value in parameters.items():
            command += ["-defparam", "tb_soc_pins." + key + "=" + str(value)]
        command += args.xrun_arg
        record = {"name": name, "command": command, "status": "PREPARED", "image_sha256": sha(images[name]),
                  "firmware_checks": firmware["cases"][name]["checks"], "sdf_command_raw": command_file.read_text(),
                  "sdf_command_sha256": sha(command_file)}
        result["checks"].append(record)
        save(folder / "command.json", command)
        save(out / "results.json", result)
        if args.dry_run:
            print("PREPARED post-route " + name + " (not executed)", flush=True)
            continue
        start = time.monotonic()
        try:
            with (folder / "console.log").open("wb") as log:
                process = subprocess.run(command, cwd=str(folder), stdout=log, stderr=subprocess.STDOUT, timeout=args.timeout)
            record.update(status="PASS", exit_code=process.returncode, elapsed_seconds=round(time.monotonic() - start, 3))
            checked_case = audit_case(out, record)
            record["case_audit"] = checked_case
            if checked_case["status"] != "PASS":
                raise RuntimeError("Post-route case failed: " + name + "; inspect " + str(folder / "console.log"))
            print("PASS post-route " + name + ": two verified CPU boots with SDF checks enabled", flush=True)
        except Exception as exc:
            record.update(status="FAIL", error=str(exc), elapsed_seconds=round(time.monotonic() - start, 3))
            result["status"] = "FAIL"
            save(out / "results.json", result)
            raise
        save(out / "results.json", result)
    if args.dry_run:
        save(out / "results.json", result)
        print(str(out / "results.json"), flush=True)
        return 0
    result["status"] = "SIMULATION_COMPLETE"
    save(out / "results.json", result)
    report = audit(out)
    result.update(status=report["status"], finished_utc=now())
    save(out / "results.json", result)
    print(json.dumps({"status": result["status"], "results": str(out / "results.json"), "audit": str(out / "audit.json")}, indent=2), flush=True)
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
