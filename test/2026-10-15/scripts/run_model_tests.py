"""Test supplied trained model on real inputs through MMIO and real CPU/SoC."""
import argparse,json,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from tools.workspace import WORK, TEST_ROOT
sys.path.insert(0,str(ROOT))
from export_real_model import export
from build_model_firmware import build_model
from run_tests import HAR_RTL,RESULTS,execute,filelist,tool
from tools.memory_profile import MEMORIES,soc_target,functional_sim_flags

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--data-root",type=Path,help="Official UCI root for full 2947-row test; otherwise use committed 24-row fixture")
    p.add_argument("--unit",action="store_true",help="Run real-model MMIO regression without ModelSim")
    p.add_argument("--vsim");p.add_argument("--iverilog");p.add_argument("--vvp")
    p.add_argument("--memory",choices=MEMORIES,default="portable-sram")
    args=p.parse_args()
    meta=export(args.data_root)
    out=WORK/"real_model"
    try:
        execute("model_platform_integrity",[sys.executable,ROOT/"tools/check_hardware.py"])
        iv=tool("iverilog",args.iverilog);vv=tool("vvp",args.vvp)
        exe=out/"har_model.vvp"
        execute("har_model_compile",[iv,"-g2012","-s","tb_har_model","-o",exe]+[ROOT/n for n in HAR_RTL+["rtl/npu/simple_npu_top.sv","test/2026-10-15/rtl/tb_har_model.sv"]])
        log=execute("har_real_model",[vv,exe,f"+WEIGHTS={(out/'weights.hex').as_posix()}",f"+SAMPLES={(out/'samples.hex').as_posix()}",f"+COUNT={meta['sample_count']}"],
            cwd=out,marker=f"HAR_MODEL PASS samples={meta['sample_count']}",timeout=300)
        expected=meta["integer_correct"]*2
        if f"inferences={meta['sample_count']*2} correct={expected} " not in log:raise AssertionError("RTL accuracy count differs from reference")
        if not args.unit:
            image=build_model();vsim=tool("vsim",args.vsim)
            env=os.environ.copy()
            if not env.get("LM_LICENSE_FILE"):
                candidate=Path(vsim).parent.parent/"LICENSE.TXT"
                if candidate.exists():env["LM_LICENSE_FILE"]=str(candidate)
            top,init_parameter=soc_target(args.memory)
            directory=WORK/"soc"/(args.memory+"/har-model")
            (directory/"soc/sim/out").mkdir(parents=True,exist_ok=True)
            fl=filelist("har",args.memory)
            script=directory/"real_model.do"
            commands=["onerror {quit -code 1}","onbreak {resume}",
                "if {[file exists work]} {vdel -lib work -all}","vlib work","vmap work work",
                f"vlog -sv -f {{{fl.as_posix()}}}",
                f"vsim {functional_sim_flags(args.memory)}-suppress 12110 -novopt -onfinish stop -wlf model.wlf {{-G{init_parameter}={image.as_posix()}}} work.{top}",
                "run 0","vcd off","run -all",
                f"set status [examine -radix hex /{top}/magic_status]",
                'puts "SOC_MAGIC=$status"',
                'if {![string equal -nocase $status c0dec0de]} {quit -code 2}',"quit -code 0"]
            script.write_text("\n".join(commands)+"\n")
            name=args.memory+"_har_real_model_soc24"
            execute(name,[vsim,"-c","-do",f"do {{{script.as_posix()}}}"],cwd=directory,env=env,marker="SOC_MAGIC=c0dec0de",timeout=300)
    finally:
        (out/"results.json").write_text(json.dumps(RESULTS,indent=2)+"\n")
        result_path=WORK/"results"/(args.memory+"_model.json")
        result_path.parent.mkdir(parents=True,exist_ok=True)
        result_path.write_text(json.dumps(RESULTS,indent=2)+"\n")
    print("ALL REAL MODEL TESTS PASS",flush=True)
if __name__=="__main__":main()
