"""Test supplied trained model on real inputs through MMIO and real CPU/SoC."""
import argparse,json,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.export_real_model import export
from scripts.build_model_firmware import build_model
from scripts.run_tests import HAR_RTL,RESULTS,execute,filelist,tool

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--data-root",type=Path,help="Official UCI root for full 2947-row test; otherwise use committed 24-row fixture")
    p.add_argument("--unit",action="store_true",help="Run real-model MMIO regression without ModelSim")
    p.add_argument("--vsim");p.add_argument("--iverilog");p.add_argument("--vvp")
    args=p.parse_args()
    meta=export(args.data_root)
    out=ROOT/"build/real_model"
    try:
        execute("model_platform_integrity",[sys.executable,ROOT/"scripts/check_platform.py"])
        iv=tool("iverilog",args.iverilog);vv=tool("vvp",args.vvp)
        exe=out/"har_model.vvp"
        execute("har_model_compile",[iv,"-g2012","-s","tb_har_model","-o",exe]+[ROOT/n for n in HAR_RTL+["rtl/npu/har/simple_npu_top.sv","verification/mmio/tb_har_model.sv"]])
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
            directory=ROOT/"build/soc/har-model"
            (directory/"soc/sim/out").mkdir(parents=True,exist_ok=True)
            fl=filelist("har")
            script=directory/"real_model.do"
            commands=["onerror {quit -code 1}","onbreak {resume}",
                "if {[file exists work]} {vdel -lib work -all}","vlib work","vmap work work",
                f"vlog -sv -f {{{fl.as_posix()}}}",
                f"vsim -suppress 12110 -novopt -onfinish stop -wlf model.wlf {{-G/my_soc_tb/dut/i_mainmem/INIT_FILE={image.as_posix()}}} work.my_soc_tb",
                "run 0","vcd off","run -all",
                "set status [examine -radix hex /my_soc_tb/magic_status]",
                'puts "SOC_MAGIC=$status"',
                'if {![string equal -nocase $status c0dec0de]} {quit -code 2}',"quit -code 0"]
            script.write_text("\n".join(commands)+"\n")
            execute("har_real_model_soc24",[vsim,"-c","-do",f"do {{{script.as_posix()}}}"],cwd=directory,env=env,marker="SOC_MAGIC=c0dec0de",timeout=300)
    finally:
        (out/"results.json").write_text(json.dumps(RESULTS,indent=2)+"\n")
    print("ALL REAL MODEL TESTS PASS",flush=True)
if __name__=="__main__":main()
