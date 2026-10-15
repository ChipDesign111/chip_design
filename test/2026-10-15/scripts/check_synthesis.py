"""Technology-independent Yosys structural checks; no PDK/library accessed."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from tools.workspace import WORK, TEST_ROOT
sys.path.insert(0,str(ROOT))
from run_tests import HAR_RTL

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--yosys",default=shutil.which("yosys"))
    args=p.parse_args()
    if not args.yosys: raise SystemExit("Yosys not found; specify --yosys")
    out=WORK/"synthesis"
    out.mkdir(parents=True,exist_ok=True)
    netlist=out/"har_generic.json"
    # Old Yosys embeds source filenames into RTLIL names, which cannot contain
    # spaces. Keep source filenames relative even when the checkout has spaces.
    commands=["read_verilog -sv "+" ".join('"'+s+'"' for s in HAR_RTL+["rtl/npu/simple_npu_top.sv"]),
        "hierarchy -check -top simple_npu_top","proc","opt","wreduce","opt",
        "memory_dff","memory_collect","opt_clean","check -assert","stat",
        'write_json "'+netlist.as_posix()+'"']
    script=out/"check.ys"
    script.write_text("\n".join(commands)+"\n")
    log=out/"yosys.log"
    with log.open("w",encoding="utf-8") as output:
        result=subprocess.run([args.yosys,"-Q","-T","-s",str(script)],cwd=ROOT,stdout=output,stderr=subprocess.STDOUT,timeout=180)
    if result.returncode: raise SystemExit("Yosys failed; see "+str(log))
    design=json.loads(netlist.read_text())
    cells=[cell for module in design["modules"].values() for cell in module["cells"].values()]
    memories=[c for c in cells if c["type"]=="$mem_v2"]
    bits=sum(int(c["parameters"]["WIDTH"],2)*int(c["parameters"]["SIZE"],2) for c in memories)
    sync_ports=sum(int(c["parameters"]["RD_CLK_ENABLE"],2).bit_count() for c in memories)
    # Tile module definition is shared by two instances; count physical hierarchy.
    def count_multipliers(name):
        total=0
        for cell in design["modules"][name]["cells"].values():
            kind=cell["type"]
            if kind=="$mul": total+=1
            elif kind in design["modules"]: total+=count_multipliers(kind)
        return total
    muls=count_multipliers("simple_npu_top")
    latches=[c["type"] for c in cells if "latch" in c["type"].lower()]
    assert len(memories)==38 and bits==17920, (len(memories),bits)
    assert sync_ports==76, "Both ports of all weight banks must be synchronous"
    assert muls==172 and not latches, (muls,latches)
    summary=dict(pass_=True,weight_banks=38,weight_bits=bits,synchronous_read_ports=sync_ports,
        dot_product_multipliers=140,requant_multipliers=32,total_multipliers=muls,latches=0,
        tool=subprocess.check_output([args.yosys,"-V"],text=True).strip(),
        scope="Generic cells and memory structure only; no area/frequency/BRAM/ASIC claim")
    (out/"summary.json").write_text(json.dumps(summary,indent=2)+"\n")
    print(json.dumps(summary))
if __name__=="__main__": main()
