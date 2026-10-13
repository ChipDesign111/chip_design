#!/usr/bin/env python3
"""Portable command entry point for HAR-NPU engineering workflows."""
from __future__ import annotations

import argparse
from importlib import metadata
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
PROFILE_REQUIREMENTS = {
    "repository": ("python",),
    "unit": ("python", "iverilog", "vvp"),
    "model": ("python", "numpy", "iverilog", "vvp"),
    "soc": ("python", "vsim"),
    "model-soc": ("python", "numpy", "iverilog", "vvp", "vsim"),
    "synthesis": ("python", "yosys"),
}


def resolve_tool(name: str, override: str | None) -> str | None:
    if override:
        path = Path(override).expanduser()
        if path.is_file():
            return str(path.resolve())
        found = shutil.which(override)
        if found:
            return str(Path(found).resolve())
        raise ValueError(f"{name}: executable not found: {override}")
    found = shutil.which(name)
    return str(Path(found).resolve()) if found else None


def environment(args: argparse.Namespace) -> tuple[dict, dict]:
    tools = {
        name: resolve_tool(name, getattr(args, name, None))
        for name in ("iverilog", "vvp", "vsim", "yosys")
    }
    try:
        numpy_version = metadata.version("numpy")
    except metadata.PackageNotFoundError:
        numpy_version = None
    available = {
        "python": sys.version_info >= (3, 11),
        "numpy": numpy_version is not None,
        **{name: path is not None for name, path in tools.items()},
    }
    details = {
        "python_version": ".".join(str(value) for value in sys.version_info[:3]),
        "numpy_version": numpy_version,
        "tools_available": {name: path is not None for name, path in tools.items()},
        "modelsim_license_environment_set": bool(os.environ.get("LM_LICENSE_FILE")),
        "profiles": {
            name: {"available": all(available[key] for key in requirements),
                   "missing": [key for key in requirements if not available[key]]}
            for name, requirements in PROFILE_REQUIREMENTS.items()
        },
    }
    return details, tools


def require_profiles(details: dict, profiles: list[str]) -> bool:
    missing = sorted({
        item for profile in profiles
        for item in details["profiles"][profile]["missing"]
    })
    if missing:
        print("Missing prerequisites: " + ", ".join(missing), file=sys.stderr)
        print("See docs/environment.md or run python project.py doctor.", file=sys.stderr)
        return False
    return True


def command_plan(args: argparse.Namespace, tools: dict) -> list[list[str]]:
    def command(script: str, *flags: str) -> list[str]:
        return [sys.executable, str(ROOT / "scripts" / script), *flags]

    def simulator_flags(*names: str) -> list[str]:
        flags = []
        for name in names:
            if tools[name]:
                flags.extend(["--" + name, tools[name]])
        return flags

    def test_command(suite: str) -> list[str]:
        if suite == "unit":
            return command("run_tests.py", "--unit", "--count", str(args.count),
                           *simulator_flags("iverilog", "vvp"))
        if suite == "soc":
            return command("run_tests.py", "--soc", *simulator_flags("vsim"))
        flags = simulator_flags("iverilog", "vvp")
        if suite == "model":
            flags.append("--unit")
        else:
            flags.extend(simulator_flags("vsim"))
        if args.data_root:
            flags.extend(["--data-root", str(args.data_root.expanduser().resolve())])
        return command("run_model_tests.py", *flags)

    checks = [command("check_repo.py"), command("check_platform.py")]
    if args.command == "check":
        return checks
    if args.command == "download-data":
        return [command("download_uci_har.py")]
    if args.command == "synth":
        return [command("check_synthesis.py", *simulator_flags("yosys"))]
    if args.command == "ci":
        return checks + [
            command("run_tests.py", "--unit", *simulator_flags("iverilog", "vvp")),
            command("run_model_tests.py", "--unit", *simulator_flags("iverilog", "vvp")),
            command("check_synthesis.py", *simulator_flags("yosys")),
        ]
    suites = ["unit", "model", "soc", "model-soc"] if args.suite == "all" else [args.suite]
    return [test_command(suite) for suite in suites]


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    commands = result.add_subparsers(dest="command", required=True)

    def add_tools(command: argparse.ArgumentParser) -> None:
        for name in ("iverilog", "vvp", "vsim", "yosys"):
            command.add_argument("--" + name, help=f"Explicit {name} executable")

    doctor = commands.add_parser("doctor", help="Report local prerequisites without changing the host")
    doctor.add_argument("--require", action="append", choices=PROFILE_REQUIREMENTS, default=[])
    add_tools(doctor)
    commands.add_parser("check", help="Check repository policy, links, configuration and frozen inputs")
    test = commands.add_parser("test", help="Run a verification suite")
    test.add_argument("--suite", choices=["unit", "model", "soc", "model-soc", "all"], default="unit")
    test.add_argument("--count", type=int, default=1000, help="Synthetic cases, 12..1000 (unit suite)")
    test.add_argument("--data-root", type=Path, help="Official UCI root; omitted uses 24 real fixtures")
    add_tools(test)
    add_tools(commands.add_parser("synth", help="Check generic Yosys structure without a technology library"))
    add_tools(commands.add_parser("ci", help="Run the same local suites as public CI"))
    commands.add_parser("download-data", help="Download official UCI test data to ignored data/")
    return result


def main(argv: list[str] | None = None) -> int:
    cli = parser()
    args = cli.parse_args(argv)
    try:
        details, tools = environment(args)
    except ValueError as error:
        cli.error(str(error))
    if args.command == "doctor":
        print(json.dumps(details, indent=2))
        return 0 if require_profiles(details, args.require or ["repository"]) else 1

    required = ["repository"]
    if args.command == "synth":
        required.append("synthesis")
    elif args.command == "ci":
        required.extend(["unit", "model", "synthesis"])
    elif args.command == "test":
        if not 12 <= args.count <= 1000:
            cli.error("--count must be in 12..1000")
        if args.data_root:
            path = args.data_root.expanduser().resolve()
            if not all((path / "test" / name).is_file() for name in ("X_test.txt", "y_test.txt")):
                cli.error("--data-root must contain test/X_test.txt and test/y_test.txt")
        required.extend(["unit", "model", "soc", "model-soc"] if args.suite == "all" else [args.suite])
    if not require_profiles(details, required):
        return 1

    for command in command_plan(args, tools):
        print(">>> " + Path(command[1]).name + " " + " ".join(command[2:]), flush=True)
        result = subprocess.run(command, cwd=ROOT, check=False)
        if result.returncode:
            print(f"FAILED: {Path(command[1]).name} (exit {result.returncode})", file=sys.stderr)
            return result.returncode if result.returncode > 0 else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
