"""Shared repository paths and timestamped, reproducible test workspaces."""
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
TEST_ROOT = ROOT / "test/2026-10-15"
SCRIPTS = TEST_ROOT / "scripts"
now = datetime.now(timezone(timedelta(hours=8)))
default_run = ROOT / "test" / now.strftime("%Y-%m-%d") / "runs" / (now.strftime("%H%M%S_%f") + "_" + str(os.getpid()))
WORK = Path(os.environ.get("CHIP_TEST_RUN", str(default_run))).resolve()
if not WORK.is_relative_to(ROOT / "test") or WORK == ROOT / "test":
    raise ValueError("CHIP_TEST_RUN must be a directory inside this repository's test/")
os.environ["CHIP_TEST_RUN"] = str(WORK)


def source_hashes():
    candidates = list((ROOT / "rtl").rglob("*.sv")) + list((ROOT / "rtl").rglob("*.svh"))
    candidates += list((ROOT / "test").glob("*/scripts/*.py")) + list((ROOT / "test").glob("*/rtl/*.sv"))
    candidates += list((ROOT / "tools").glob("*.py")) + list((ROOT / "model/export").glob("*"))
    candidates += list((ROOT / "model/quantization").glob("*.py")) + list((ROOT / "test/2026-10-20/precision").glob("*.json"))
    candidates += [ROOT / "rtl/filelist.f", ROOT / "rtl/project.json", TEST_ROOT / "fixtures/har_uci24.json"]
    return {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(candidates) if p.is_file() and p.suffix != ".md"}


def begin_run(command):
    WORK.mkdir(parents=True, exist_ok=True)
    for source, name in ((SCRIPTS, "scripts"), (TEST_ROOT / "rtl", "testbench"), (ROOT / "tools", "tools")):
        destination = WORK / name
        destination.mkdir(exist_ok=True)
        for path in source.iterdir():
            if path.is_file() and path.suffix in (".py", ".sv"):
                shutil.copyfile(path, destination / path.name)
    for kind, suffix in (("scripts", ".py"), ("rtl", ".sv")):
        for directory in sorted((ROOT/"test").glob("*/"+kind)):
            if directory.parent == TEST_ROOT: continue
            destination=WORK/(kind+"_"+directory.parent.name)
            destination.mkdir(exist_ok=True)
            for path in directory.glob("*"+suffix): shutil.copyfile(path, destination/path.name)
    metadata = {"started_at": now.isoformat(), "timezone": "Asia/Shanghai",
                "command": command, "source_sha256": source_hashes(),
                "scope": "Functional simulation / generic structure; no physical timing signoff"}
    (WORK / "manifest.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    return metadata


def finish_run(metadata, exit_code):
    changed = metadata["source_sha256"] != source_hashes()
    if changed:
        exit_code = 1
    metadata.update(exit_code=exit_code, source_changed_during_run=changed,
                    finished_at=datetime.now(timezone(timedelta(hours=8))).isoformat())
    (WORK / "manifest.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    results = WORK / "results"
    names = sorted(p.name for p in results.glob("*.json")) if results.exists() else []
    report = "# Test run\n\nCommand: `" + metadata["command"] + "`\n\nResult: "
    report += ("PASS" if exit_code == 0 else "FAIL") + "\n\n"
    report += "Source identity: [manifest.json](manifest.json). Script snapshots: scripts/, testbench/, tools/.\n\n"
    report += "Results: " + (", ".join("[" + name + "](results/" + name + ")" for name in names) or "See logs/ and synthesis/") + ".\n"
    (WORK / "report.md").write_text(report, encoding="utf-8")
    print("Test record: " + WORK.relative_to(ROOT).as_posix(), flush=True)
    return exit_code
