"""Freeze paired CPU/NPU FC microbenchmarks and measure passive timing/traffic."""
import argparse, hashlib, json, re, sys
from datetime import datetime
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
import numpy as np
import torch
from torch import nn
from compiler.compiler import compile_model
from compiler.sim import simulate


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path)
    parser.add_argument('--frozen-suite',type=Path,help='Reuse exact model/input/calibration arrays')
    parser.add_argument('--vsim',default='vsim')
    parser.add_argument('--task-engine',action='store_true')
    args=parser.parse_args()
    out=args.out or ROOT/'test/int8/runs'/('fc_profile_'+datetime.now().strftime('%Y%m%d_%H%M%S'))
    out=out.resolve();out.mkdir(parents=True,exist_ok=False)
    fixtures=out/'fixtures';fixtures.mkdir()
    shapes=[(1,1,1),(7,5,1),(9,10,1),(16,8,1),(48,24,1),(64,32,4)]
    rng=np.random.default_rng(20261117);results=[];frozen=[]
    for k,n,b in shapes:
        name=f'k{k}_n{n}_b{b}';file=fixtures/(name+'.npz')
        if args.frozen_suite:file.write_bytes((args.frozen_suite/file.name).read_bytes())
        else:
            np.savez(file,weight=rng.normal(0,0.2,(n,k)).astype('float32'),
                bias=rng.normal(0,0.1,n).astype('float32'),
                x=rng.uniform(-1,1,(b,k)).astype('float32'))
        values=np.load(file);model=nn.Linear(k,n).eval()
        with torch.no_grad():
            model.weight.copy_(torch.from_numpy(values['weight']))
            model.bias.copy_(torch.from_numpy(values['bias']))
        x=torch.from_numpy(values['x']);references=[]
        frozen.append(dict(name=name,sha256=hashlib.sha256(file.read_bytes()).hexdigest(),k=k,n=n,batch=b))
        for force_cpu in [False,True]:
            backend='cpu' if force_cpu else 'auto' if args.task_engine else 'npu'
            package=compile_model(model,x,[-x,x*0.5],force_cpu=force_cpu,task_engine=args.task_engine)
            actual_backend=package.nodes[0]['backend']
            assert actual_backend==('CPU' if force_cpu or args.task_engine and k*n*b==1 else 'NPU')
            references.append(package.reference(x.numpy())[package.graph['output']])
            directory=out/(name+'_'+backend);directory.mkdir()
            package.write(directory,x.numpy())
            log=simulate(directory,args.vsim,profile=True)
            cycles=int(re.search(r'INT8_SOC PASS cycles=(\d+)',log).group(1))
            hardware=int(re.search(r'hw_soc_cycles=(\d+)',log).group(1))
            profile=json.loads((directory/'profile.json').read_text())
            assert profile['observed_edges']==hardware
            if name=='k1_n1_b1':
                control=out/(name+'_'+backend+'_control');control.mkdir()
                package.write(control,x.numpy());control_log=simulate(control,args.vsim)
                assert (directory/'firmware.hex').read_bytes()==(control/'firmware.hex').read_bytes()
                assert re.search(r'INT8_SOC PASS (.*)',log).group(1)==re.search(r'INT8_SOC PASS (.*)',control_log).group(1)
            results.append(dict(name=name,backend=backend,actual_backend=actual_backend,cycles=cycles,hardware_cycles=hardware,
                code_sha256=package.metadata['code_sha256'],profile=profile))
            (out/'partial.json').write_text(json.dumps(results,indent=2)+'\n',encoding='utf-8')
        assert np.array_equal(*references),name
    sources={str(p.relative_to(ROOT)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest()
        for folder in ['compiler','rtl'] for p in (ROOT/folder).rglob('*') if p.is_file() and p.suffix in ['.py','.sv','.v']}
    sources['test/int8/run_fc_profile.py']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    result=dict(passed=True,baseline_commit='94636cc',fixtures=frozen,source_sha256=sources,cases=results,
        scope=('Task RTL' if args.task_engine else 'Legacy path')+'; paired identical FC weights/input/calibration and integer output. Tiny controls verify passive probe leaves cycles/counters unchanged.')
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print('FC_PROFILE_PASS '+str(out))


if __name__=='__main__':main()
