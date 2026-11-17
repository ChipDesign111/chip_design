"""PyTorch task compiler, six activation modes and strict MODE0 selection."""
import argparse,datetime,json,re,sys
from pathlib import Path
import numpy as np
import torch
from torch import nn
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from compiler.compiler import compile_model
from compiler.sim import simulate


def special_network(activation=None):
    model=nn.Sequential(nn.Linear(64,32),activation or nn.ReLU(),nn.Linear(32,6)).eval()
    with torch.no_grad():
        model[0].weight.fill_(1/64);model[0].bias.zero_()
        model[2].weight.copy_(torch.linspace(-0.1,0.2,192).reshape(6,32));model[2].bias.zero_()
    return model


def main():
    p=argparse.ArgumentParser();p.add_argument('--soc',action='store_true');p.add_argument('--vsim',default='vsim');args=p.parse_args()
    run=ROOT/'test/int8/runs'/('task_compiler_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));run.mkdir(parents=True)
    torch.manual_seed(417)
    x=torch.linspace(-2,2,96).reshape(2,48)
    configurations=[('chain',nn.Sequential(nn.Linear(48,24),nn.ReLU(),nn.Linear(24,8)).eval(),x,{}),
        ('chain_materialized',None,x,dict(forward=False,fuse=False)),
        ('deep',nn.Sequential(nn.Linear(17,13),nn.LeakyReLU(0.125),nn.Linear(13,9),nn.ReLU6(),nn.Linear(9,5),nn.Tanh()).eval(),torch.linspace(-3,3,34).reshape(2,17),{}),
        ('split',nn.Sequential(nn.Linear(65,41),nn.ReLU(),nn.Linear(41,9)).eval(),torch.linspace(-1,1,65).reshape(1,65),{})]
    configurations[1]=(configurations[1][0],configurations[0][1],x,configurations[1][3])
    for name,act in [('none',nn.Identity()),('relu',nn.ReLU()),('relu6',nn.ReLU6()),
                     ('leaky',nn.LeakyReLU(0.13)),('sigmoid',nn.Sigmoid()),('tanh',nn.Tanh())]:
        configurations.append(('act_'+name,nn.Sequential(nn.Linear(9,7),act).eval(),torch.linspace(-8,8,36).reshape(4,9),{}))
    sx=torch.linspace(0.5,1,256).reshape(4,64)
    configurations += [('special',special_network(),sx,{}),
        ('same_shape_wrong_activation',special_network(nn.LeakyReLU(0.1)),sx,{}),
        ('special_disabled',None,sx,dict(specialize=False))]
    configurations[-1]=(configurations[-1][0],configurations[-3][1],sx,configurations[-1][3])
    large=nn.Linear(256,20).eval()
    with torch.no_grad():large.weight.fill_(1);large.bias.zero_()
    configurations.append(('large_cpu_fallback',large,torch.linspace(0.5,1,1024).reshape(4,256),{}))
    results=[]
    for name,model,x,options in configurations:
        calibration=[-x,x*0.5]
        package=compile_model(model,x,calibration,task_engine=True,**options)
        cpu=compile_model(model,x,calibration,force_cpu=True)
        actual=package.reference(x.numpy());gold=cpu.reference(x.numpy())
        for node,value in actual.items():assert np.array_equal(value,gold[node]),(name,node)
        if name=='special':assert len(package.metadata['special_segments'])==1
        if name in ('same_shape_wrong_activation','special_disabled'):assert not package.metadata['special_segments']
        if name=='chain':assert package.metadata['task_segments'][0]['internal_edges']
        if name=='chain_materialized':assert not package.metadata['task_segments'][0]['internal_edges']
        if name=='large_cpu_fallback':assert package.nodes[0]['backend']=='CPU' and 'INT22' in package.nodes[0]['reason']
        out=run/name;package.write(out,x.numpy());log=simulate(out,args.vsim) if args.soc else ''
        if name in ('act_relu6','act_leaky') and args.soc:
            cpu_out=run/(name+'_cpu');cpu.write(cpu_out,x.numpy());simulate(cpu_out,args.vsim)
        results.append(dict(name=name,code_bytes=package.metadata['code_bytes'],free_bytes=package.metadata['free_bytes'],
            segments=len(package.metadata['task_segments']),descriptors=sum(s['count'] for s in package.metadata['task_segments']),
            special_segments=len(package.metadata['special_segments']),
            observed_cycles=int(re.search(r'INT8_SOC PASS cycles=(\d+)',log).group(1)) if log else None))
    (run/'result.json').write_text(json.dumps(dict(passed=True,soc=args.soc,cases=results),indent=2)+'\n')
    print(json.dumps(results,indent=2));print('Results: '+str(run))
if __name__=='__main__':main()
