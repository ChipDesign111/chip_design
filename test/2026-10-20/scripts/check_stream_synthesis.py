"""Generic streaming NPU/DMA structure checks, without licensed libraries."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from tools.workspace import WORK,begin_run,finish_run


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--yosys',default=shutil.which('yosys'))
    args=p.parse_args()
    if not args.yosys:raise SystemExit('Yosys required')
    metadata=begin_run(' '.join(sys.argv));code=1
    out=WORK/'synthesis';out.mkdir(parents=True,exist_ok=True)
    sources={'har_stream_top':['rtl/npu/har_dot_tile.sv','rtl/npu/har_weight_store.sv','rtl/npu/har_stream_core.sv','rtl/npu/har_stream_top.sv'],
             'har_stream_dma':['rtl/dma/har_stream_dma.sv']}
    results={}
    try:
        for top,files in sources.items():
            script=out/(top+'.ys');net=out/(top+'.json');log=out/(top+'.log')
            script.write_text('read_verilog -sv '+' '.join(files)+'\nhierarchy -check -top '+top+
                '\nproc\nopt\nwreduce\nopt\nmemory_dff\nmemory_collect\nopt_clean\ncheck -assert\nstat\nwrite_json "'+net.as_posix()+'"\n')
            with log.open('w',encoding='utf-8') as f:
                r=subprocess.run([args.yosys,'-Q','-T','-s',str(script)],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,timeout=180)
            if r.returncode:raise RuntimeError('Synthesis failed: '+str(log))
            design=json.loads(net.read_text())
            def count(name):
                result={'multipliers':0,'latches':0,'memory_bits':0,'explicit_dff_bits':0}
                for cell in design['modules'][name]['cells'].values():
                    kind=cell['type'];params=cell.get('parameters',{})
                    if kind in design['modules']:
                        child=count(kind)
                        for key in result:result[key]+=child[key]
                    elif kind=='$mul':result['multipliers']+=1
                    elif 'latch' in kind.lower():result['latches']+=1
                    elif kind=='$mem_v2':result['memory_bits']+=int(params['WIDTH'],2)*int(params['SIZE'],2)
                    elif 'dff' in kind.lower():result['explicit_dff_bits']+=int(params['WIDTH'],2)
                return result
            results[top]=count(top);assert results[top]['latches']==0
        assert results['har_stream_top']['multipliers']==172 and results['har_stream_top']['memory_bits']>=17920
        assert results['har_stream_dma']['multipliers']==0 and results['har_stream_dma']['memory_bits']==512
        results.update(scope='Generic structure only; no mapped area/timing/power or native 4x8 multiplier claim',
                       source_sha256={f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for files in sources.values() for f in files})
        (WORK/'results').mkdir(exist_ok=True)
        (WORK/'results/stream_synthesis.json').write_text(json.dumps(results,indent=2)+'\n')
        print(json.dumps(results));code=0
    finally:finish_run(metadata,code)


if __name__=='__main__':main()
