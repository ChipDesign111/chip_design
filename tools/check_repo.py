"""Validate repository policy, documentation, Python syntax and MMIO layout."""
from __future__ import annotations

import ast
import json
from pathlib import Path
import re
import sys
import shutil
import subprocess
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_FILES = (
    "README.md", ".gitignore", ".gitattributes", ".editorconfig",
    "tools/project.py", "tools/workspace.py", "tools/check_hardware.py",
    "model/requirements.txt", "rtl/project.json", "rtl/filelist.f", "rtl/manifest.json",
    "report/README.md", "report/architecture.md", "report/development.md", "report/mmio.md",
    "report/sram.md", "report/THIRD_PARTY_NOTICES.md", "model/numerics.md",
    ".github/workflows/ci.yml", "test/README.md", "tools/README.md",
)
REQUIRED_DIRS = ("rtl", "model", "tools", "test", "report", "fpga", "eda")
EXCLUDED_PARTS = {".git", "data", "local", "runs", "dist", ".venv", "venv", "__pycache__"}


def files(suffix: str):
    return (
        path for path in ROOT.rglob("*" + suffix)
        if not any(part in EXCLUDED_PARTS for part in path.relative_to(ROOT).parts)
    )


def check() -> list[str]:
    errors = []
    if "/tools/local/" not in (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines():
        errors.append("Local physical-IP / temporary directory must be ignored")
    if shutil.which("git") and (ROOT / ".git").exists():
        tracked = subprocess.check_output(["git", "ls-files", "--", "tools/local"], cwd=ROOT, text=True)
        if tracked.strip(): errors.append("Licensed/local files must not be tracked")
    for name in REQUIRED_FILES:
        if not (ROOT / name).is_file(): errors.append(f"Missing required file: {name}")
    for name in REQUIRED_DIRS:
        if not (ROOT / name).is_dir(): errors.append(f"Missing directory: {name}")
    visible = {p.name for p in ROOT.iterdir() if p.is_dir() and not p.name.startswith(".")}
    if visible != set(REQUIRED_DIRS): errors.append("Top-level directories must be exactly rtl/fpga/model/eda/test/report/tools")
    rtl_dirs = {p.name for p in (ROOT / "rtl").iterdir() if p.is_dir()}
    if rtl_dirs != {"soc", "platform", "npu", "dma"}:
        errors.append("RTL directories must be soc/platform/npu/dma")
    listed = set()
    for raw in (ROOT / "rtl/filelist.f").read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        include = line.startswith("+incdir+")
        relative = line[len("+incdir+"):] if include else line
        target = (ROOT / relative).resolve()
        if not target.is_relative_to(ROOT / "rtl") or not (target.is_dir() if include else target.is_file()):
            errors.append("Invalid RTL filelist entry: " + line)
        if line in listed:
            errors.append("Duplicate RTL filelist entry: " + line)
        listed.add(line)
    for forbidden in ("rtl/npu/common", "rtl/npu/baseline", "rtl/dma/baseline"):
        if (ROOT / forbidden).exists():errors.append("Retired layout present: " + forbidden)
    rtl_text = "\n".join(p.read_text(encoding="utf-8") for p in files(".sv"))
    if "CHIP_STREAM_NPU" in rtl_text or "module simple_npu_top" in rtl_text or "module har_npu_core" in rtl_text:
        errors.append("Only the final W8A4 hardware may be present")
    for name in ("fpga",):
        if (ROOT/name).exists() and any(p.name != ".gitkeep" for p in (ROOT/name).iterdir()):
            errors.append(name + " must remain empty except for its Git placeholder")
    for name in ("eda/README.md", "eda/docs/操作指南.md", "eda/server/bin/flow.py", "eda/package_server.py"):
        if not (ROOT/name).is_file():
            errors.append("Missing EDA deployment/documentation entry: " + name)
    for path in (ROOT/"eda").rglob("*"):
        if path.is_file() and not {"dist", "runs", "__pycache__"}.intersection(path.relative_to(ROOT/"eda").parts):
            if any(s.lower() in {".lib", ".lef", ".vclef", ".gds", ".gds2", ".cdl", ".spi", ".db"} for s in path.suffixes):
                errors.append("Licensed/process implementation data must stay outside EDA source: " + str(path.relative_to(ROOT)))
    if (ROOT/"rtl/npu/lab3").exists(): errors.append("Original NPU must not be retained")
    for doc in files(".md"):
        content = doc.read_text(encoding="utf-8")
        if re.search(r"^(<<<<<<< |=======|>>>>>>> )", content, flags=re.MULTILINE):
            errors.append(f"Unresolved merge marker: {doc.relative_to(ROOT)}")
        for target in re.findall(r"(?<!!)\[[^\]\n]*\]\(([^)\n]+)\)", content):
            target = target.strip().split("#", 1)[0].strip("<>")
            if not target or re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", target):
                continue
            resolved = (doc.parent / unquote(target)).resolve()
            if not resolved.is_relative_to(ROOT):
                errors.append(f"Link leaves repository: {doc.relative_to(ROOT)} -> {target}")
            elif not resolved.exists():
                errors.append(f"Broken link: {doc.relative_to(ROOT)} -> {target}")

    for path in files(".py"):
        try:
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path.relative_to(ROOT)))
        except (SyntaxError, UnicodeError) as error:
            errors.append(f"Invalid Python source: {path.relative_to(ROOT)}: {error}")

    try:
        config = json.loads((ROOT / "rtl/project.json").read_text(encoding="utf-8"))
        if config["schema_version"] != 1:
            errors.append("Unsupported project configuration schema")
        network = config["network"]
        if tuple(network[key] for key in ("input_features", "hidden_features", "classes")) != (64, 32, 6):
            errors.append("Network dimensions differ from the fixed accelerator contract")
        if config["numeric"]["input_bits"] != 4 or config["architecture"]["batch_max"] != 64:
            errors.append("Final design must use W8A4 and a 64-sample maximum batch")
        mmio = config["mmio"]
        if not 0 <= mmio["base_address"] < 2**32 or mmio["base_address"] % 4:
            errors.append("Invalid MMIO base")
        if mmio["window_bytes"] != 16384:
            errors.append("MMIO aperture must match the 12-bit word-address port")
        previous_end = mmio["register_area_bytes"]
        if previous_end < 40 or previous_end % 4:
            errors.append("Register area does not cover final scalar control registers")
        for window in sorted(mmio["windows"], key=lambda value: value["offset"]):
            start, size = window["offset"], window["size_bytes"]
            if start % 4 or size <= 0 or size % 4:
                errors.append(f"Unaligned/invalid MMIO window: {window['name']}")
            if start < previous_end:
                errors.append(f"Overlapping MMIO window: {window['name']}")
            if start + size > mmio["window_bytes"]:
                errors.append(f"MMIO window exceeds aperture: {window['name']}")
            previous_end = max(previous_end, start + size)
    except (OSError, ValueError, KeyError, TypeError) as error:
        errors.append(f"Invalid project configuration: {error}")
    return errors


def main() -> int:
    errors = check()
    if errors:
        for error in errors:
            print("ERROR: " + error)
        return 1
    print("PASS: repository policy, local documentation links, Python syntax and MMIO configuration.")
    print("Functional verification: tools/project.py test; retained perimeter: tools/project.py check.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
