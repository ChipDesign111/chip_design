"""Compile PyTorch graphs; boot generated programs on the complete SoC RTL."""
import argparse,datetime,hashlib,json,re,sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
import torch
from torch import nn
from model.compiler.compiler import compile_model
from model.compiler.frontend import CompileError
from run import execute

class MixedNetwork(nn.Module):
    def __init__(self):
        super().__init__();self.fc1=nn.Linear(17,12);self.relu=nn.ReLU();self.sigmoid=nn.Sigmoid();self.fc2=nn.Linear(12,5)
    def forward(self,x):
        y=self.relu(self.fc1(x));z=self.sigmoid(y)
        return torch.softmax(self.fc2(z*y+y)*0.9+0.1,dim=1)

class ArithmeticNetwork(nn.Module):
    def forward(self,x):return torch.softmax((1.0-x)-x*0.5,dim=-1)

class WideNetwork(nn.Module):
    def __init__(self):super().__init__();self.fc=nn.Linear(65,9);self.tanh=nn.Tanh()
    def forward(self,x):return self.tanh(self.fc(x))

from model.compiler.sim import simulate

def run_soc(package,directory,x,vsim='vsim'):
    package.write(directory,x)
    return simulate(directory,vsim)

def main():
    p=argparse.ArgumentParser();p.add_argument('--soc',action='store_true');p.add_argument('--vsim',default='vsim');args=p.parse_args()
    run=ROOT/'test/int8/runs'/('compiler_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));run.mkdir(parents=True)
    torch.manual_seed(42);mixed=MixedNetwork().eval();wide=WideNetwork().eval()
    fallback=nn.Sequential(nn.Linear(4,3),nn.ReLU()).eval()
    with torch.no_grad():fallback[0].weight.fill_(0.01);fallback[0].bias.fill_(10)
    configurations=[('mixed',mixed,torch.linspace(-1,1,17).reshape(1,17),False),
                    ('cpu_only',mixed,torch.linspace(-1,1,17).reshape(1,17),True),
                    ('wide',wide,torch.linspace(-1,1,130).reshape(2,65),False),
                    ('range_fallback',fallback,torch.tensor([[-1.,0.5,0.2,1.]]),False),
                    ('output_tiled',nn.Linear(9,41).eval(),torch.linspace(-1,1,9).reshape(1,9),False),
                    ('cpu_arithmetic',ArithmeticNetwork().eval(),torch.linspace(-1,1,14).reshape(2,7),False)]
    # Retained trained PyTorch HAR weights, with a separate calibration subset.
    har=nn.Sequential(nn.Linear(64,32),nn.ReLU(inplace=True),nn.Linear(32,6)).eval()
    weights=np.load(ROOT/'model/export/weights_float32.npz')
    with torch.no_grad():
        for layer,prefix in [(har[0],'fc1'),(har[2],'fc2')]:
            layer.weight.copy_(torch.from_numpy(weights[prefix+'_weight']))
            layer.bias.copy_(torch.from_numpy(weights[prefix+'_bias']))
    fixture=json.loads((ROOT/'test/int8/har_uci24.json').read_text())
    har_inputs=torch.tensor(fixture['x_int8'],dtype=torch.float32)*float(weights['input_scale'][0])
    configurations.append(('trained_har',har,har_inputs[12:13],False))
    results=[]
    for name,model,example,cpu in configurations:
        calibration=[v.reshape(1,64) for v in har_inputs[:12]] if name=='trained_har' else [-example,example*0.5]
        package=compile_model(model,example,calibration_inputs=calibration,force_cpu=cpu)
        if name=='range_fallback':assert package.nodes[0]['backend']=='CPU' and 'INT22' in package.nodes[0]['reason']
        for index,x in enumerate([example,example.flip(1)*0.7] if name=='mixed' else [example]):
            directory=run/(name+str(index));directory.mkdir()
            log=run_soc(package,directory,x.numpy(),args.vsim) if args.soc else ''
            if not args.soc:package.write(directory,x.numpy())
            quant=package.reference(x.numpy())[package.graph['output']]
            scale=package.metadata['tensors'][package.graph['output']]['scale']
            with torch.no_grad():floating=model(x).numpy()
            results.append(dict(name=name+str(index),code_sha256=package.metadata['code_sha256'],
                                backends=[n['backend'] for n in package.nodes],code_bytes=package.metadata['code_bytes'],
                                observed_cycles=int(re.search(r'INT8_SOC PASS cycles=(\d+)',log).group(1)) if args.soc else None,
                                npu_jobs=sum(len(n.get('jobs',[])) for n in package.nodes if n['backend']=='NPU'),
                                free_bytes=package.metadata['free_bytes'],float_max_abs_error=float(np.abs(quant.astype(float)*scale-floating).max())))
    assert results[0]['code_sha256']==results[1]['code_sha256']
    # Automatic NPU execution and forced CPU execution have the same integer contract.
    mixed_input=configurations[0][2]
    mixed_accel=compile_model(mixed,mixed_input,[-mixed_input,mixed_input*0.5])
    mixed_cpu=compile_model(mixed,mixed_input,[-mixed_input,mixed_input*0.5],force_cpu=True)
    for name,q in mixed_accel.reference(mixed_input.numpy()).items():
        assert np.array_equal(q,mixed_cpu.reference(mixed_input.numpy())[name])
    try:mixed_accel.write(run/'invalid_input',np.full((1,17),np.nan))
    except CompileError:pass
    else:raise AssertionError('Nonfinite runtime input was accepted')
    # Unsupported operators and oversized models must be rejected explicitly.
    for model,x in [(nn.Sequential(nn.LeakyReLU()).eval(),torch.ones(1,4)),
                    (nn.Sequential(nn.Linear(128,128)).eval(),torch.ones(1,128))]:
        try:compile_model(model,x)
        except (CompileError,ValueError):pass
        else:raise AssertionError('Unsupported/oversized model was accepted')
    sources=[p for folder in ['model/compiler','rtl'] for p in (ROOT/folder).rglob('*') if p.is_file() and p.suffix in ('.py','.sv','.v')]+[Path(__file__)]
    source_hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    (run/'result.json').write_text(json.dumps(dict(passed=True,soc=args.soc,torch_version=torch.__version__,source_sha256=source_hashes,cases=results),indent=2)+'\n')
    print(json.dumps(results,indent=2));print('Results: '+str(run))

if __name__=='__main__':main()
