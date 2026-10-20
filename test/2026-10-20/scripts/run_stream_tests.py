"""Final W8A4 NPU arithmetic, packet safety and DMA protocol verification."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

import numpy as np

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from tools.workspace import WORK, begin_run, finish_run
sys.path.insert(0,str(ROOT/'test/2026-10-15/scripts'))
from run_tests import execute,tool

NEW_RTL=['rtl/npu/har_dot_tile.sv','rtl/npu/har_weight_store.sv',
         'rtl/npu/har_stream_core.sv','rtl/npu/har_stream_top.sv']


def vectors(directory,data_root=None):
    directory.mkdir(parents=True,exist_ok=True)
    config=json.loads((ROOT/'model/quantization/w8a4.json').read_text())
    with np.load(ROOT/'model/export/weights_int8.npz',allow_pickle=False) as z:
        w1=z['fc1_weight_int8'].astype(np.int64);w2=z['fc2_weight_int8'].astype(np.int64)
        indices=z['feat_idx'].astype(int)
    values=w1.ravel().tolist()+w2.ravel().tolist()
    words=[sum((int(v)&255)<<(8*k) for k,v in enumerate(values[i:i+4])) for i in range(0,len(values),4)]
    words+=config['bias1_int32']+config['bias2_int32']+[config['requant_multiplier'],config['requant_shift']]
    cases=json.loads((ROOT/'test/2026-10-20/fixtures/w8a4_soc24.json').read_text())
    def save(name,values):
        path=directory/(name+'.hex');path.write_text(''.join(f'{int(v)&0xffffffff:08x}\n' for v in values),encoding='ascii');return path
    params=save('params',words)
    def record(c):return c['input_words_u32']+c['hidden_u4']+c['scores_int32']+[c['class_id']]
    fixture=save('vectors',[v for c in cases for v in record(c)])
    full=None
    if data_root:
        raw=np.loadtxt(data_root/'test/X_test.txt',usecols=indices,dtype=np.float64)
        x=np.clip(np.rint(raw/config['input_scale']),-7,7).astype(np.int64)
        a=x@w1.T+np.array(config['bias1_int32'])
        h=np.minimum(15,(np.maximum(a,0)*config['requant_multiplier']+(1<<(config['requant_shift']-1)))>>config['requant_shift'])
        score=h@w2.T+np.array(config['bias2_int32']);pred=np.argmax(score,axis=1)
        full_words=[]
        for i in range(len(x)):
            packed=[sum((int(v)&15)<<(4*k) for k,v in enumerate(x[i,j:j+8])) for j in range(0,64,8)]
            full_words+=packed+h[i].tolist()+score[i].tolist()+[int(pred[i])]
        full=save('full_vectors',full_words)
    return words,cases,params,fixture,full


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--unit',action='store_true')
    p.add_argument('--data-root',type=Path);p.add_argument('--iverilog');p.add_argument('--vvp')
    args=p.parse_args();metadata=begin_run(' '.join(sys.argv));exit_code=1
    out=WORK/'stream';out.mkdir(parents=True,exist_ok=True)
    try:
        _,_,params,fixture,full=vectors(out,args.data_root)
        iv=tool('iverilog',args.iverilog);vv=tool('vvp',args.vvp)
        dma_image=out/'dma.vvp'
        execute('stream_dma_compile',[iv,'-g2012','-s','tb_stream_dma','-o',dma_image,ROOT/'rtl/dma/har_stream_dma.sv',ROOT/'test/2026-10-20/rtl/tb_stream_dma.sv'])
        execute('stream_dma_protocol',[vv,dma_image],marker='DMA_UNIT PASS transfers=248')
        image=out/'stream.vvp'
        execute('stream_compile',[iv,'-g2012','-s','tb_stream_npu','-o',image,*[ROOT/x for x in NEW_RTL],ROOT/'test/2026-10-20/rtl/tb_stream_npu.sv'])
        log=execute('stream_unit',[vv,image,f'+PARAMS={params.as_posix()}',f'+VECTORS={fixture.as_posix()}'],marker='STREAM_NPU PASS')
        unit=[dict(mode=int(a),samples=int(b),cycles=int(c),result_span=int(d)) for a,b,c,d in
              re.findall(r'STREAM_UNIT mode=(\d+) samples=(\d+) cycles=(\d+) result_span=(\d+)',log)]
        if full:
            execute('stream_full_model',[vv,image,f'+PARAMS={params.as_posix()}',f'+VECTORS={full.as_posix()}','+COUNT=2947'],marker='STREAM_NPU PASS')
        summary={'samples':24,'unit':unit,'dma_protocol_cases':248,
                 'precision':'W8A4, INT32 accumulation','parameter_words':598,'input_words':192,
                 'scope':'Final continuous mode; exact hidden/score/class, DMA protocol and packet safety',
                 'full_model_rtl_samples':2947 if full else 0,
                 'source_sha256':{x:hashlib.sha256((ROOT/x).read_bytes()).hexdigest() for x in NEW_RTL+['rtl/dma/har_stream_dma.sv']}}
        (out/'results.json').write_text(json.dumps(summary,indent=2)+'\n')
        (WORK/'results').mkdir(exist_ok=True)
        (WORK/'results/stream.json').write_text(json.dumps(summary,indent=2)+'\n')
        print(json.dumps(summary),flush=True);exit_code=0
    finally:finish_run(metadata,exit_code)


if __name__=='__main__':main()
