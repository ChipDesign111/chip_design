"""Validate the shared scaffold; does not run chip functionality."""
from __future__ import annotations

import json
from pathlib import Path
import re
import sys
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_FILES = (
    "README.md", "CONTRIBUTING.md", ".gitignore", ".gitattributes",
    "docs/plan.md", "docs/backlog.md", "docs/architecture.md", "docs/spec.md",
    "docs/numerics.md", "docs/mmio.md", "docs/memory-budget.md",
    "docs/verification.md", "docs/environment.md", "docs/sources.md",
    "docs/decisions.md", "docs/team.md", "configs/project.json",
    "configs/env.example.json", ".github/pull_request_template.md",
    ".github/ISSUE_TEMPLATE/task.yml",
)
REQUIRED_DIRS = (
    "platform/course_soc", "rtl/npu", "rtl/memory", "rtl/soc",
    "model/reference", "model/training", "model/export", "sw/include",
    "sw/drivers", "sw/tests", "sw/startup", "verification/unit",
    "verification/npu", "verification/mmio", "verification/soc",
    "verification/vectors", "filelists", "scripts", "configs", "fpga",
    "asic", "reports", "docs/ai-log", "docs/weekly",
)

def check() -> list[str]:
    errors: list[str] = []
    for name in REQUIRED_FILES:
        if not (ROOT / name).is_file():
            errors.append(f"Missing file: {name}")
    for name in REQUIRED_DIRS:
        if not (ROOT / name / "README.md").is_file():
            errors.append(f"Missing directory description: {name}/README.md")
    for doc in ROOT.rglob("*.md"):
        if ".git" in doc.parts or "build" in doc.parts:
            continue
        content = doc.read_text(encoding="utf-8")
        for target in re.findall(r"(?<!!)\[[^\]\n]*\]\(([^)\n]+)\)", content):
            target = target.strip().split("#", 1)[0]
            if not target or re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", target):
                continue
            resolved = (doc.parent / unquote(target)).resolve()
            if not resolved.is_relative_to(ROOT):
                errors.append(f"Link leaves repository: {doc.relative_to(ROOT)} -> {target}")
            elif not resolved.exists():
                errors.append(f"Broken link: {doc.relative_to(ROOT)} -> {target}")
    config_path = ROOT / "configs/project.json"
    if config_path.exists():
        try:
            config = json.loads(config_path.read_text(encoding="utf-8"))
            n = config["network"]
            if (n["input_features"], n["hidden_features"], n["classes"]) != (64, 32, 6):
                errors.append("Unexpected target network; update the agreed specification.")
            m = config["mmio"]
            if m["base_address"] % 4 or m["window_bytes"] <= 0:
                errors.append("Invalid MMIO base or window.")
            entries = sorted(m["windows"], key=lambda w: w["offset"])
            previous_end = m["register_area_bytes"]
            for item in entries:
                start, size = item["offset"], item["size_bytes"]
                if start % 4 or size <= 0 or size % 4:
                    errors.append(f"Unaligned/invalid MMIO window: {item['name']}")
                if start < previous_end:
                    errors.append(f"Overlapping MMIO window: {item['name']}")
                if start + size > m["window_bytes"]:
                    errors.append(f"MMIO window exceeds local addressing: {item['name']}")
                previous_end = max(previous_end, start + size)
        except (ValueError, KeyError, TypeError) as exc:
            errors.append(f"Invalid project config: {exc}")
    return errors

def main() -> int:
    errors = check()
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("PASS: shared structure, Markdown links, project config and MMIO layout.")
    print("Scope: scaffold only; no model, RTL, FPGA or ASIC validation performed.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
