"""Generate deterministic synthetic hardware tests; not a trained HAR model."""
import argparse
import hashlib
import json
from pathlib import Path
import random
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "model/reference"))
from mlp_int import infer

WORDS = 2383
def case(index, rng):
    x = [rng.randrange(-128,128) for _ in range(64)]
    w1 = [[rng.randrange(-128,128) for _ in range(64)] for _ in range(32)]
    w2 = [[rng.randrange(-128,128) for _ in range(32)] for _ in range(6)]
    b1 = [rng.randrange(-300000,300001) for _ in range(32)]
    b2 = [rng.randrange(-100000,100001) for _ in range(6)]
    mult, shift = rng.choice([0,1,3,255,65535]), rng.choice([0,1,7,15,31])
    if index == 0 or 6 <= index < 12:
        x=[0]*64; w1=[[0]*64 for _ in range(32)]; w2=[[0]*32 for _ in range(6)]
        b1=[0]*32; b2=[0]*6; mult=1; shift=0
        if index >= 6: b2[index-6]=1
    elif index in (1,2):
        value = -128 if index==1 else 127
        x=[value]*64; w1=[[value]*64 for _ in range(32)]
        w2=[[value]*32 for _ in range(6)]; b1=[0]*32; b2=[0]*6; mult=1; shift=0
    elif index == 3:
        x=[127]*64; w1=[[-128]*64 for _ in range(32)]
        b1=[0]*32; b2=list(range(-6,0)); mult=1; shift=0
    elif index == 4:
        w1=[[0]*64 for _ in range(32)]
        b1=[-1,0,1,3,253,255,257,511]*4; b2=[0]*6; mult=1; shift=1
    elif index == 5:
        w1=[[0]*64 for _ in range(32)]; w2=[[0]*32 for _ in range(6)]
        b1=[2147483647]*32; b2=[-2147483648+k for k in range(6)]; mult=65535; shift=31
    h,s,c=infer(x,w1,w2,b1,b2,mult,shift)
    return dict(x=x,w1=w1,w2=w2,b1=b1,b2=b2,mult=mult,shift=shift,hidden=h,scores=s,category=c)

def flatten(c):
    words=c["x"]+sum(c["w1"],[])+sum(c["w2"],[])+c["b1"]+c["b2"]+[c["mult"],c["shift"]]+c["hidden"]+c["scores"]+[c["category"]]
    assert len(words)==WORDS
    return words

def generate(count, out):
    if not 12 <= count <= 1000: raise ValueError("count must be 12..1000")
    out.mkdir(parents=True,exist_ok=True)
    rng=random.Random(20261008)
    examples=[]
    core=out/"core.hex"; mmio=out/"mmio.hex"
    with core.open("w",encoding="ascii") as a, mmio.open("w",encoding="ascii") as b:
        for index in range(count):
            c=case(index,rng)
            text="".join(f"{value & 0xffffffff:08x}\n" for value in flatten(c))
            a.write(text)
            if index<12: b.write(text); examples.append(c)
    manifest={"seed":20261008,"count":count,"words_per_case":WORDS,"mmio_cases":12,
              "kind":"synthetic hardware verification; no classification accuracy claim",
              "sha256":{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (core,mmio)}}
    (out/"manifest.json").write_text(json.dumps(manifest,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(manifest))
    return manifest
def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--count",type=int,default=1000)
    args=parser.parse_args()
    generate(args.count, ROOT/"build/vectors")
if __name__=="__main__": main()
