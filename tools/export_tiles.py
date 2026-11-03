"""Export trained INT8 weights in the DMA SRAM order, without NumPy dependency."""
import argparse,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from model.reference.tile_layout import encode,weights,parameters
ACCUMULATOR_BITS=22
def check_accumulator_bounds(name,vectors,bias,input_lo,input_hi):
    for index,(row,offset) in enumerate(zip(vectors,bias)):
        low=sum(weight*(input_lo if weight>=0 else input_hi) for weight in row)+offset
        high=sum(weight*(input_hi if weight>=0 else input_lo) for weight in row)+offset
        limit=1<<(ACCUMULATOR_BITS-1)
        if low < -limit or high > limit-1:
            raise ValueError('%s output %d accumulator range [%d,%d] exceeds INT%d' %
                             (name,index,low,high,ACCUMULATOR_BITS))
def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    w1,w2=weights();q=parameters()
    check_accumulator_bounds('FC1',w1,q['fc1']['bias_int32'],-128,127)
    check_accumulator_bounds('FC2',w2,q['fc2']['bias_int32'],0,127)
    meta={'format':'FC1[tile32][output32][lane2]; FC2[packet4][tile8][output6]','accumulator_bits':ACCUMULATOR_BITS,'source_sha256':hashlib.sha256((ROOT/'model/export/weights_int8.npz').read_bytes()).hexdigest(),'parameters':q,'files':{}}
    for name,data in zip(['fc1_tiles.bin','fc2_tiles.bin'],encode(w1,w2)):
        (a.output/name).write_bytes(data);meta['files'][name]={'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
    (a.output/'tiles.json').write_text(json.dumps(meta,indent=2)+'\n');print(a.output)
if __name__=='__main__':main()
