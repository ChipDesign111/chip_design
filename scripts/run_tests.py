"""Run real RTL/SoC tests and fail on missing markers, FAIL, or timeout.
Unit tests use Icarus; full SoC uses ModelSim (AXI interfaces unsupported by
Icarus 11). Build products/logs/results are isolated under build/.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.build_har_firmware import build
from scripts.generate_vectors import generate

RESULTS=[]
def execute(name,command,cwd=ROOT,marker=None,timeout=300,env=None):
    start=time.monotonic()
    result=subprocess.run([str(v) for v in command],cwd=cwd,env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=timeout)
    log=ROOT/"build/logs"/(name+".log")
    log.parent.mkdir(parents=True,exist_ok=True)
    log.write_text(result.stdout,encoding="utf-8")
    ok=result.returncode==0 and (marker is None or marker in result.stdout)
    if re.search(r"(?m)^.*(?:FATAL:|FAIL case=|TIMEOUT after|# \*\* Error:)",result.stdout):
        ok=False
    cycles=re.search(r"self-check OK after (\d+) cycles",result.stdout)
    record=dict(test=name,pass_=ok,seconds=round(time.monotonic()-start,3),log=str(log.relative_to(ROOT)),exit_code=result.returncode)
    if cycles: record["soc_cycles"]=int(cycles.group(1))
    RESULTS.append(record)
    print(f'{name}: {"PASS" if ok else "FAIL"} ({record["seconds"]}s)',flush=True)
    if not ok:
        print(result.stdout[-12000:])
        raise RuntimeError(f"{name} failed; see {log}")
    return result.stdout

def tool(name,override=None):
    found=override or shutil.which(name)
    if not found: raise RuntimeError(f"{name} not found; add it to PATH or use the explicit CLI option")
    return str(Path(found).resolve())

def units(args):
    iv=tool("iverilog",args.iverilog); vv=tool("vvp",args.vvp)
    directory=ROOT/"build/unit"
    directory.mkdir(parents=True,exist_ok=True)
    generate(args.count,ROOT/"build/vectors")
    suites=[
        ("lab3_core","tb_npu_check",["rtl/npu/lab3/simple_npu_pe.sv","rtl/npu/lab3/simple_npu_core.sv","verification/lab3/tb_npu_check.sv"],"[CHECK] ALL PASS",[]),
        ("lab3_mmio","tb_simple_npu",["rtl/npu/lab3/simple_npu_pe.sv","rtl/npu/lab3/simple_npu_core.sv","rtl/npu/lab3/simple_npu_top.sv","verification/lab3/tb_simple_npu.sv"],"[TB] ALL PASS",[]),
        ("har_core","tb_har_core",["rtl/npu/har/har_npu_core.sv","verification/npu/tb_har_core.sv"],f"HAR_CORE PASS cases={args.count}",[f"+VECTORS={(ROOT/'build/vectors/core.hex').as_posix()}",f"+COUNT={args.count}"]),
        ("har_mmio","tb_har_mmio",["rtl/npu/har/har_npu_core.sv","rtl/npu/har/simple_npu_top.sv","verification/mmio/tb_har_mmio.sv"],"HAR_MMIO PASS cases=12",[f"+VECTORS={(ROOT/'build/vectors/mmio.hex').as_posix()}","+COUNT=12"]),
    ]
    for name,top,sources,marker,plusargs in suites:
        output=directory/(name+".vvp")
        execute(name+"_compile",[iv,"-g2012","-s",top,"-o",output]+[ROOT/path for path in sources])
        execute(name,[vv,output]+plusargs,cwd=directory,marker=marker)

def filelist(profile):
    lines=[]
    inserted=False
    for raw in (ROOT/"filelists/lab3_original.f").read_text().splitlines():
        line=raw.strip()
        if not line: continue
        if line.startswith("+incdir+"):
            lines.append("+incdir+"+(ROOT/"platform/course_soc"/line[len("+incdir+"):]).as_posix())
        elif line.startswith("simple_npu/"):
            if not inserted:
                sources=["simple_npu_pe.sv","simple_npu_core.sv","simple_npu_top.sv"] if profile=="lab3" else ["har_npu_core.sv","simple_npu_top.sv"]
                lines.extend((ROOT/"rtl/npu"/profile/f).as_posix() for f in sources)
                inserted=True
        elif line=="soc/sim/tb/my_soc_tb.sv":
            lines.append((ROOT/"verification/lab3/soc/my_soc_tb.sv").as_posix())
        else:
            lines.append((ROOT/"platform/course_soc"/line).as_posix())
    lines.insert(0,"+incdir+"+(ROOT/"platform/course_soc/soc/rtl").as_posix())
    path=ROOT/"build"/(profile+".f")
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text("\n".join('"'+line+'"' for line in lines)+"\n",encoding="utf-8")
    return path

def soc(args):
    vsim=tool("vsim",args.vsim)
    env=os.environ.copy()
    if not env.get("LM_LICENSE_FILE"):
        candidate=Path(vsim).parent.parent/"LICENSE.TXT"
        if candidate.exists(): env["LM_LICENSE_FILE"]=str(candidate)
    har_hex=build(ROOT/"build/sw")
    for profile,tests in [
        ("lab3",[(f"lab3_soc_{name}",ROOT/f"verification/lab3/soc/{name}.hex") for name in ["lab3_test1","lab3_test2","lab3_test3","lab3_hand"]]),
        ("har",[("har_soc_6_classes",har_hex)]),
    ]:
        directory=ROOT/"build/soc"/profile
        (directory/"soc/sim/out").mkdir(parents=True,exist_ok=True)
        fl=filelist(profile)
        for idx,(name,hex_path) in enumerate(tests):
            commands=["onerror {quit -code 1}","onbreak {resume}"]
            if idx==0:
                commands += ["if {[file exists work]} {vdel -lib work -all}","vlib work","vmap work work",f"vlog -sv -f {{{fl.as_posix()}}}"]
            commands += [
                f"vsim -suppress 12110 -novopt -onfinish stop -wlf {{{(directory/(name+'.wlf')).as_posix()}}} {{-G/my_soc_tb/dut/i_mainmem/INIT_FILE={hex_path.as_posix()}}} work.my_soc_tb",
                "run 0", "vcd off", "run -all",
                'set status [examine -radix hex /my_soc_tb/magic_status]',
                'puts "SOC_MAGIC=$status"',
                'if {![string equal -nocase $status c0dec0de]} {quit -code 2}',
                "quit -code 0",
            ]
            do=directory/(name+".do")
            do.write_text("\n".join(commands)+"\n",encoding="utf-8")
            execute(name,[vsim,"-c","-do",f"do {{{do.as_posix()}}}"],cwd=directory,env=env,marker="SOC_MAGIC=c0dec0de",timeout=args.soc_timeout)

def main():
    p=argparse.ArgumentParser()
    mode=p.add_mutually_exclusive_group()
    mode.add_argument("--unit",action="store_true")
    mode.add_argument("--soc",action="store_true")
    p.add_argument("--count",type=int,default=1000)
    p.add_argument("--iverilog");p.add_argument("--vvp");p.add_argument("--vsim")
    p.add_argument("--soc-timeout",type=int,default=300)
    args=p.parse_args()
    output=ROOT/"build/results"/("soc.json" if args.soc else "unit.json" if args.unit else "all.json")
    try:
        execute("platform_integrity",[sys.executable,ROOT/"scripts/check_platform.py"])
        if not args.soc: units(args)
        if not args.unit: soc(args)
    finally:
        output.parent.mkdir(parents=True,exist_ok=True)
        output.write_text(json.dumps(RESULTS,indent=2)+"\n",encoding="utf-8")
    print(f"ALL SELECTED TESTS PASS; results: {output}",flush=True)

if __name__=="__main__":
    main()
