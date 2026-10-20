"""Generic DMA buffer/control structure; no technology or licensed views."""
import argparse,json,shutil,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from tools.workspace import WORK

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--yosys",default=shutil.which("yosys"));args=p.parse_args()
    if not args.yosys:p.error("Yosys missing")
    out=WORK/"synthesis/dma";out.mkdir(parents=True,exist_ok=True)
    net=out/"dma.json"
    commands=["read_verilog -sv rtl/dma/baseline/har_dma.sv","hierarchy -check -top har_dma","proc","opt","wreduce","opt",
              "memory_dff","memory_collect","opt_clean","check -assert","stat",'write_json "'+net.as_posix()+'"']
    script=out/"check.ys";script.write_text("\n".join(commands)+"\n")
    with (out/"yosys.log").open("w",encoding="utf-8") as log:
        subprocess.run([args.yosys,"-Q","-T","-s",str(script)],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=180)
    design=json.loads(net.read_text());cells=list(design["modules"]["har_dma"]["cells"].values())
    memories=[c for c in cells if c["type"]=="$mem_v2"]
    assert len(memories)==1
    bits=sum(int(c["parameters"]["WIDTH"],2)*int(c["parameters"]["SIZE"],2) for c in memories)
    assert bits==512 and not any("latch" in c["type"].lower() for c in cells)
    assert not any(c["type"]=="$mul" for c in cells)
    registers=sum(int(c["parameters"]["WIDTH"],2) for c in cells if "dff" in c["type"].lower())
    result={"pass":True,"buffer_bits":bits,"buffer_words":16,"explicit_register_bits":registers,"multipliers":0,"latches":0,
            "tool":subprocess.check_output([args.yosys,"-V"],text=True).strip(),"scope":"Generic DMA engine only; AXI routing/mapping/timing area excluded"}
    (out/"summary.json").write_text(json.dumps(result,indent=2)+"\n");print(json.dumps(result),flush=True)
if __name__=="__main__":main()
