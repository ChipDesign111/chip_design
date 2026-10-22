"""Export trained INT8 weights in the DMA SRAM order, without NumPy dependency."""
import argparse,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from model.reference.tile_layout import encode,weights,parameters
def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    meta={'format':'FC1[tile32][output32][lane2]; FC2[input32][output6+pad2]','source_sha256':hashlib.sha256((ROOT/'model/export/weights_int8.npz').read_bytes()).hexdigest(),'parameters':parameters(),'files':{}}
    for name,data in zip(['fc1_tiles.bin','fc2_tiles.bin'],encode(*weights())):
        (a.output/name).write_bytes(data);meta['files'][name]={'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
    (a.output/'tiles.json').write_text(json.dumps(meta,indent=2)+'\n');print(a.output)
if __name__=='__main__':main()
