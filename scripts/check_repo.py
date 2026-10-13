"""Validate repository policy, documentation, Python syntax and MMIO layout."""
from __future__ import annotations

import ast
import json
from pathlib import Path
import re
import sys
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_FILES = (
    "README.md", "CONTRIBUTING.md", "CHANGELOG.md", "THIRD_PARTY_NOTICES.md",
    ".gitignore", ".gitattributes", ".editorconfig", "project.py", "requirements.txt",
    ".github/workflows/ci.yml", ".github/pull_request_template.md",
    ".github/ISSUE_TEMPLATE/bug.yml", ".github/ISSUE_TEMPLATE/feature.yml",
    "configs/project.json", "docs/README.md", "docs/environment.md",
    "docs/architecture.md", "docs/spec.md", "docs/numerics.md", "docs/mmio.md",
    "docs/verification.md", "docs/change-guide.md", "docs/model-verification.md",
    "docs/releases.md", "docs/roadmap.md", "docs/provenance.md", "docs/adr/README.md",
    "docs/archive/README.md", "LICENSES/README.md", "reports/README.md",
)
REQUIRED_DIRS = (
    "platform", "platform/course_soc", "rtl", "rtl/npu", "model",
    "model/reference", "model/training", "model/export", "sw", "verification",
    "verification/npu", "verification/mmio", "verification/vectors",
    "filelists", "scripts", "configs", "fpga", "asic", "reports",
)
EXCLUDED_PARTS = {".git", "build", "data", ".venv", "venv", "__pycache__"}


def files(suffix: str):
    return (
        path for path in ROOT.rglob("*" + suffix)
        if not any(part in EXCLUDED_PARTS for part in path.relative_to(ROOT).parts)
    )


def check() -> list[str]:
    errors = []
    for name in REQUIRED_FILES:
        if not (ROOT / name).is_file():
            errors.append(f"Missing required file: {name}")
    for name in REQUIRED_DIRS:
        if not (ROOT / name / "README.md").is_file():
            errors.append(f"Missing component documentation: {name}/README.md")

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
        config = json.loads((ROOT / "configs/project.json").read_text(encoding="utf-8"))
        if config["schema_version"] != 1:
            errors.append("Unsupported project configuration schema")
        network = config["network"]
        if tuple(network[key] for key in ("input_features", "hidden_features", "classes")) != (64, 32, 6):
            errors.append("Network dimensions differ from the fixed accelerator contract")
        mmio = config["mmio"]
        if not 0 <= mmio["base_address"] < 2**32 or mmio["base_address"] % 4:
            errors.append("Invalid MMIO base")
        if mmio["window_bytes"] != 16384:
            errors.append("MMIO aperture must match the 12-bit word-address port")
        previous_end = mmio["register_area_bytes"]
        if previous_end < 40 or previous_end % 4:
            errors.append("Register area does not cover the V2 control registers")
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
    print("Functional verification is performed by project.py test; frozen inputs by project.py check.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
