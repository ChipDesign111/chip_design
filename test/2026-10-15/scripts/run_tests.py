"""Run real RTL/SoC tests and fail on missing markers, FAIL, or timeout.
Unit tests use Icarus; full SoC uses ModelSim (AXI interfaces unsupported by
Icarus 11). Each invocation writes under test/YYYY-MM-DD/runs/<timestamp>/.
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

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from tools.workspace import WORK, TEST_ROOT
sys.path.insert(0,str(ROOT))
from build_har_firmware import build
from generate_vectors import generate
from tools.memory_profile import MEMORIES, soc_target, sources as memory_sources, functional_sim_flags

RESULTS=[]
HAR_RTL=["rtl/npu/common/har_dot_tile.sv","rtl/npu/common/har_weight_store.sv","rtl/npu/baseline/har_npu_core.sv"]
def execute(name,command,cwd=ROOT,marker=None,timeout=300,env=None):
    start=time.monotonic()
    result=subprocess.run([str(v) for v in command],cwd=cwd,env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=timeout)
    log=WORK/"logs"/(name+".log")
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
    directory=WORK/"unit"
    directory.mkdir(parents=True,exist_ok=True)
    generate(args.count,WORK/"vectors")
    suites=[
        ("har_core","tb_har_core",HAR_RTL+["test/2026-10-15/rtl/tb_har_core.sv"],f"HAR_CORE PASS cases={args.count}",[f"+VECTORS={(WORK/'vectors/core.hex').as_posix()}",f"+BATCH={(WORK/'vectors/batch.hex').as_posix()}",f"+COUNT={args.count}"]),
        ("har_mmio","tb_har_mmio",HAR_RTL+["rtl/npu/baseline/simple_npu_top.sv","test/2026-10-15/rtl/tb_har_mmio.sv"],"HAR_MMIO PASS cases=12",[f"+VECTORS={(WORK/'vectors/mmio.hex').as_posix()}",f"+BATCH={(WORK/'vectors/batch.hex').as_posix()}","+COUNT=12"]),
    ]
    for name,top,sources,marker,plusargs in suites:
        output=directory/(name+".vvp")
        execute(name+"_compile",[iv,"-g2012","-s",top,"-o",output]+[ROOT/path for path in sources])
        execute(name,[vv,output]+plusargs,cwd=directory,marker=marker)

def filelist(profile="har", memory="portable-sram"):
    if profile != "har" or memory not in MEMORIES:
        raise ValueError("Only the current HAR SoC and supported SRAM backends may be built")
    lines=[]
    if memory == "ra1shd":
        from tools.memory_profile import vendor_model
        lines += ["+define+CHIP_USE_RA1SHD", vendor_model().as_posix()]
    for raw in (ROOT/"rtl/filelist.f").read_text(encoding="utf-8").splitlines():
        line=raw.strip()
        if not line or line.startswith("#"): continue
        if line.startswith("+incdir+"):
            lines.append("+incdir+"+(ROOT/line[len("+incdir+"):]).as_posix())
        else:
            lines.append((ROOT/line).as_posix())
    lines.append((TEST_ROOT/"rtl/tb_soc.sv").as_posix())
    path=WORK/("soc_"+memory+".f")
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text("\n".join('"'+line+'"' for line in lines)+"\n",encoding="utf-8")
    return path

def soc(args):
    memory = args.memory
    top, init_parameter = soc_target(memory)
    vsim=tool("vsim",args.vsim)
    env=os.environ.copy()
    if not env.get("LM_LICENSE_FILE"):
        candidate=Path(vsim).parent.parent/"LICENSE.TXT"
        if candidate.exists(): env["LM_LICENSE_FILE"]=str(candidate)
    har_hex=build(WORK/"sw")
    har_single_hex=build(WORK/"sw/single6",include_batch=False)
    for profile,tests in [
        ("har",[("har_soc_tiled_8",har_hex),("har_soc_single6",har_single_hex)]),
    ]:
        directory=WORK/"soc"/(memory+"/"+profile)
        (directory/"soc/sim/out").mkdir(parents=True,exist_ok=True)
        fl=filelist(profile, memory)
        for idx,(name,hex_path) in enumerate(tests):
            commands=["onerror {quit -code 1}","onbreak {resume}"]
            if idx==0:
                commands += ["if {[file exists work]} {vdel -lib work -all}","vlib work","vmap work work",f"vlog -sv -f {{{fl.as_posix()}}}"]
            commands += [
                f"vsim {functional_sim_flags(memory)}-suppress 12110 -novopt -onfinish stop -wlf {{{(directory/(name+'.wlf')).as_posix()}}} {{-G{init_parameter}={hex_path.as_posix()}}} work.{top}",
                "run 0", "vcd off", "run -all",
                f'set status [examine -radix hex /{top}/magic_status]',
                'puts "SOC_MAGIC=$status"',
                'if {![string equal -nocase $status c0dec0de]} {quit -code 2}',
                "quit -code 0",
            ]
            do=directory/(name+".do")
            do.write_text("\n".join(commands)+"\n",encoding="utf-8")
            result_name = memory + "_" + name
            execute(result_name,[vsim,"-c","-do",f"do {{{do.as_posix()}}}"],cwd=directory,env=env,marker="SOC_MAGIC=c0dec0de",timeout=args.soc_timeout)

def main():
    p=argparse.ArgumentParser()
    mode=p.add_mutually_exclusive_group()
    mode.add_argument("--unit",action="store_true")
    mode.add_argument("--soc",action="store_true")
    p.add_argument("--count",type=int,default=1000)
    p.add_argument("--iverilog");p.add_argument("--vvp");p.add_argument("--vsim")
    p.add_argument("--soc-timeout",type=int,default=300)
    p.add_argument("--memory",choices=MEMORIES,default="portable-sram")
    args=p.parse_args()
    output=WORK/"results"/((args.memory+"_")+("soc.json" if args.soc else "unit.json" if args.unit else "all.json"))
    try:
        execute("platform_integrity",[sys.executable,ROOT/"tools/check_hardware.py"])
        if not args.soc: units(args)
        if not args.unit: soc(args)
    finally:
        output.parent.mkdir(parents=True,exist_ok=True)
        output.write_text(json.dumps(RESULTS,indent=2)+"\n",encoding="utf-8")
    print(f"ALL SELECTED TESTS PASS; results: {output}",flush=True)

if __name__=="__main__":
    main()
