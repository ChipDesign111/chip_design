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

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.workspace import SCRIPTS, begin_run, finish_run
PROFILE_REQUIREMENTS = {
    "repository": ("python",),
    "unit": ("python", "numpy", "iverilog", "vvp"),
    "memory": ("python", "iverilog", "vvp"),
    "soc": ("python", "numpy", "vsim"),
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
        print("See report/development.md or run python tools/project.py doctor.", file=sys.stderr)
        return False
    return True


def command_plan(args, tools):
    def flags(*names):
        return [v for name in names if tools[name] for v in ("--"+name,tools[name])]
    def script(name,*extra):return [sys.executable,str(SCRIPTS/name),*extra]
    checks=[[sys.executable,str(ROOT/"tools"/name)] for name in ("check_repo.py","check_hardware.py")]
    unit=script("run_stream_tests.py",*flags("iverilog","vvp"))
    if getattr(args,"data_root",None):unit += ["--data-root",str(args.data_root.expanduser().resolve())]
    memory=script("run_sram_tests.py","--memory",getattr(args,"memory","portable-sram"),*flags("iverilog","vvp"))
    soc=script("run_soc_tests.py","--memory",getattr(args,"memory","portable-sram"),*flags("vsim"))
    synthesis=[script(name,*flags("yosys")) for name in ("check_stream_synthesis.py","check_sram_synthesis.py")]
    if args.command=="check":return checks
    if args.command=="download-data":return [[sys.executable,str(ROOT/"tools/download_uci_har.py")]]
    if args.command=="synth":return synthesis
    if args.command=="ci":return checks+[unit,memory]+synthesis
    return {"unit":[unit],"memory":[memory],"soc":[soc],"all":[unit,memory,soc]}[args.suite]

def parser():
    result=argparse.ArgumentParser(description=__doc__)
    commands=result.add_subparsers(dest="command",required=True)
    def add_tools(command):
        for name in ("iverilog","vvp","vsim","yosys"):command.add_argument("--"+name)
    doctor=commands.add_parser("doctor",help="Report prerequisites")
    doctor.add_argument("--require",action="append",choices=PROFILE_REQUIREMENTS,default=[]);add_tools(doctor)
    commands.add_parser("check",help="Check final-design paths, links, MMIO and perimeter")
    test=commands.add_parser("test",help="Test the single final W8A4 design")
    test.add_argument("--suite",choices=["unit","memory","soc","all"],default="unit")
    test.add_argument("--memory",choices=["portable-sram","ra1shd"],default="portable-sram")
    test.add_argument("--data-root",type=Path,help="Official UCI dataset; unit/all adds all 2947 inputs")
    add_tools(test)
    add_tools(commands.add_parser("synth",help="Final NPU/DMA and main SRAM generic structure"))
    add_tools(commands.add_parser("ci",help="Public final-design checks without a licensed SoC simulator"))
    commands.add_parser("download-data")
    return result

def main(argv=None):
    cli=parser();args=cli.parse_args(argv)
    try:details,tools=environment(args)
    except ValueError as e:cli.error(str(e))
    if args.command=="doctor":
        print(json.dumps(details,indent=2));return 0 if require_profiles(details,args.require or ["repository"]) else 1
    required=["repository"]
    if args.command=="synth":required += ["synthesis"]
    elif args.command=="ci":required += ["unit","memory","synthesis"]
    elif args.command=="test":
        required += ["unit","memory","soc"] if args.suite=="all" else [args.suite]
        if args.memory=="ra1shd":
            from tools.memory_profile import vendor_model
            try:vendor_model()
            except FileNotFoundError as e:cli.error(str(e))
        if args.data_root:
            if args.suite not in ("unit","all"):cli.error("--data-root applies to unit/all; SoC uses the fixed 24-row self-check")
            if not all((args.data_root/"test"/n).is_file() for n in ("X_test.txt","y_test.txt")):cli.error("Invalid --data-root")
    if not require_profiles(details,required):return 1
    record=begin_run(args.command+(" "+args.suite if args.command=="test" else "")) if args.command in ("test","ci","synth") else None
    code=0
    try:
        for command in command_plan(args,tools):
            print(">>> "+Path(command[1]).name+" "+" ".join(command[2:]),flush=True)
            code=subprocess.run(command,cwd=ROOT,check=False).returncode
            if code:break
    except Exception:
        if record:finish_run(record,1)
        raise
    return finish_run(record,code) if record else code
if __name__=="__main__":raise SystemExit(main())
