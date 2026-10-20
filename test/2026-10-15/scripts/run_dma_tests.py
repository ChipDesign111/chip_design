"""DMA protocol/ingress tests and matched real-model CPU-vs-DMA benchmarks."""
import argparse
import json
import os
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from tools.workspace import WORK, TEST_ROOT
from tools.memory_profile import MEMORIES, functional_sim_flags
from run_tests import HAR_RTL, RESULTS, execute, filelist, tool


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--unit",action="store_true")
    p.add_argument("--memory",choices=MEMORIES,default="portable-sram")
    p.add_argument("--iverilog");p.add_argument("--vvp");p.add_argument("--vsim")
    args=p.parse_args()
    out=WORK/"dma"
    out.mkdir(parents=True,exist_ok=True)
    result_path=WORK/"results"/("dma_unit.json" if args.unit else "dma_"+args.memory+".json")
    result_path.parent.mkdir(parents=True,exist_ok=True)
    try:
        for top,inputs,marker in [
            ("tb_har_dma",["rtl/dma/baseline/har_dma.sv","test/2026-10-15/rtl/tb_har_dma.sv"],"DMA_UNIT PASS transfers=227"),
            ("tb_dma_ingress",HAR_RTL+["rtl/npu/baseline/simple_npu_top.sv","rtl/soc/my_npu_subsystem.sv","test/2026-10-15/rtl/tb_dma_ingress.sv"],"DMA_INGRESS PASS"),
        ]:
            image=out/(top+".vvp")
            execute(top+"_compile",[tool("iverilog",args.iverilog),"-g2012","-s",top,"-o",image,*[ROOT/name for name in inputs]])
            execute(top,[tool("vvp",args.vvp),image],marker=marker)
        if args.unit:
            print("ALL DMA UNIT TESTS PASS",flush=True)
            return
        from export_real_model import export
        from build_model_firmware import build_model
        model=export(None)
        images={mode:build_model(use_dma=mode=="dma",benchmark=True) for mode in ("cpu","dma")}
        vsim=tool("vsim",args.vsim)
        env=os.environ.copy()
        if not env.get("LM_LICENSE_FILE"):
            candidate=Path(vsim).parent.parent/"LICENSE.TXT"
            if candidate.exists():env["LM_LICENSE_FILE"]=str(candidate)
        directory=out/args.memory
        directory.mkdir(parents=True,exist_ok=True)
        fl=filelist("har",args.memory)
        metrics={}
        observed=("parameter_cycles","input_cycles","application_cycles","warm_cycles","dma_engine_cycles",
                  "dma_read_beats","dma_write_beats","dma_read_bursts","dma_write_bursts")
        for mode,image in images.items():
            commands=["onerror {quit -code 1}","onbreak {resume}"]
            if mode=="cpu":
                commands += ["if {[file exists work]} {vdel -lib work -all}","vlib work","vmap work work",f"vlog -sv -f {{{fl.as_posix()}}}"]
            commands += [f"vsim {functional_sim_flags(args.memory)}-suppress 12110 -novopt -onfinish stop -wlf {mode}.wlf {{-G/tb_soc/INIT_FILE={image.as_posix()}}} work.tb_soc",
                "run 0","vcd off","run -all","set status [examine -radix hex /tb_soc/magic_status]",
                'puts "SOC_MAGIC=$status"','if {![string equal -nocase $status c0dec0de]} {quit -code 2}']
            for name in observed:
                commands += [f"set observed [examine -radix hex /tb_soc/{name}]",f'puts "BENCH_{name}=$observed"']
            commands.append("quit -code 0")
            script=directory/(mode+".do")
            script.write_text("\n".join(commands)+"\n",encoding="utf-8")
            log=execute("dma_benchmark_"+args.memory+"_"+mode,[vsim,"-c","-do",f"do {{{script.as_posix()}}}"],
                        cwd=directory,env=env,marker="SOC_MAGIC=c0dec0de",timeout=300)
            stats={name:int(re.search(r"BENCH_"+name+r"=([0-9a-fA-F]+)",log)[1],16) for name in observed}
            stats["soc_cycles"]=RESULTS[-1]["soc_cycles"]
            stats["transfer_cycles"]=stats["parameter_cycles"]+stats["input_cycles"]
            assert all(stats[name]>0 for name in ("parameter_cycles","input_cycles","application_cycles")),stats
            if mode=="dma":
                assert stats["dma_read_beats"]==stats["dma_write_beats"]==982,stats
                assert stats["dma_read_bursts"]==stats["dma_write_bursts"] and stats["dma_read_bursts"]>=62,stats
                assert stats["dma_engine_cycles"]>0
            else:assert stats["dma_read_beats"]==stats["dma_write_beats"]==0,stats
            metrics[mode]=stats
        speedup={name:metrics["cpu"][name]/metrics["dma"][name] for name in
                 ("parameter_cycles","input_cycles","transfer_cycles","application_cycles","warm_cycles","soc_cycles")}
        summary={"memory":args.memory,"samples":24,"batches":12,"model_version":model["model_version"],
                 "model_sha256":model["source_sha256"],"metrics":metrics,"speedup":speedup,
                 "core_cycles_per_batch":59,"parameter_words":598,"input_words":384,
                 "scope":"Matched CPU/DMA firmware, same hardware and exact hidden/score/class checks; functional simulation only",
                 "notes":["Transfer timers include descriptor/polling/check overhead.","Application timer includes result verification; SoC timer also includes boot/status stores.","DMA uses at most 16-word bursts, one outstanding burst, with no transfer/compute overlap."]}
        (out/(args.memory+"_benchmark.json")).write_text(json.dumps(summary,indent=2)+"\n",encoding="utf-8")
        print(json.dumps(summary),flush=True)
        print("ALL DMA TESTS PASS",flush=True)
    finally:
        result_path.write_text(json.dumps(RESULTS,indent=2)+"\n",encoding="utf-8")


if __name__=="__main__":main()
