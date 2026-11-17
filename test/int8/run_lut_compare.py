"""Same integer models: direct SRAM LUT versus shared single-word landing cache."""
import argparse,datetime,hashlib,json,re,sys
from pathlib import Path
import numpy as np
import torch
from torch import nn
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from compiler.compiler import compile_model
from compiler.sim import simulate
from model.generic_mixed.model import Network


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--vsim',default='vsim');args=parser.parse_args()
    run=ROOT/'test/int8/runs'/('lut_compare_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));run.mkdir(parents=True)
    torch.manual_seed(6531)
    mixed=Network().eval();fixtures=ROOT/'model/generic_mixed/data'
    mixed.load_state_dict(torch.load(fixtures/'weights.pth',map_location='cpu',weights_only=True))
    configs=[('ordered',nn.Sigmoid().eval(),torch.linspace(-8,8,128).reshape(4,32),None),
        ('random',nn.Tanh().eval(),torch.rand(4,32)*8-4,None),
        ('two_tables',nn.Sequential(nn.Linear(9,16),nn.Sigmoid(),nn.Tanh()).eval(),torch.linspace(-1,1,36).reshape(4,9),None),
        ('mixed',mixed,torch.from_numpy(np.load(fixtures/'input.npy')),[torch.from_numpy(v) for v in np.load(fixtures/'calibration.npy')])]
    results=[]
    for name,model,x,calibration in configs:
        references=[];code=[]
        for cached in [False,True]:
            package=compile_model(model,x,calibration or [-x,x*0.5],task_engine=True,lut_cache=cached,specialize=False)
            out=run/(name+('_cache' if cached else '_direct'));package.write(out,x.numpy())
            references.append(json.loads((out/'reference.json').read_text()));code.append(package.metadata['code_sha256'])
            log=simulate(out,args.vsim,profile=True);profile=json.loads((out/'profile.json').read_text())
            results.append(dict(name=name,cached=cached,observed_cycles=int(re.search(r'INT8_SOC PASS cycles=(\d+)',log).group(1)),
                lut_dma=profile['dma_role_traffic'].get('lut',{}),traffic=profile['traffic'],exclusive=profile['exclusive_wall_cycles']))
            (run/'partial.json').write_text(json.dumps(results,indent=2)+'\n')
        assert references[0]==references[1],name
        assert code[0]==code[1],name
    sources={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for folder in ['compiler','rtl'] for p in (ROOT/folder).rglob('*') if p.is_file() and p.suffix in ['.py','.sv','.v']}
    (run/'result.json').write_text(json.dumps(dict(passed=True,cases=results,source_sha256=sources,
        scope='Functional cycle/traffic comparison only; cache area and physical timing not yet accepted'),indent=2)+'\n')
    print(json.dumps(results,indent=2));print('Results: '+str(run))
if __name__=='__main__':main()
