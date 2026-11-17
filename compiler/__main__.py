"""Compile a user PyTorch model factory and representative NumPy inputs."""
import argparse,importlib.util,json
from pathlib import Path
import numpy as np
import torch
from .compiler import compile_model

def main():
    p=argparse.ArgumentParser();p.add_argument('--model',type=Path,required=True)
    p.add_argument('--factory',default='build_model');p.add_argument('--weights',type=Path)
    p.add_argument('--input',type=Path,required=True);p.add_argument('--calibration',type=Path)
    p.add_argument('--simulate',action='store_true');p.add_argument('--vsim',default='vsim');
    p.add_argument('--out',type=Path,required=True);p.add_argument('--force-cpu',action='store_true')
    target=p.add_mutually_exclusive_group()
    target.add_argument('--task-engine',dest='task_engine',action='store_true',default=True,help='Use autonomous task RTL (default)')
    target.add_argument('--legacy-npu',dest='task_engine',action='store_false',help='Use the compatible legacy MMIO compiler path')
    cache=p.add_mutually_exclusive_group()
    cache.add_argument('--lut-cache',dest='lut_cache',action='store_true',default=None,help='Use the selected one-word shared LUT cache')
    cache.add_argument('--no-lut-cache',dest='lut_cache',action='store_false',help='Use direct SRAM LUT reads')
    a=p.parse_args()
    spec=importlib.util.spec_from_file_location('user_network',a.model)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    model=getattr(module,a.factory)().cpu().eval()
    if a.weights:model.load_state_dict(torch.load(a.weights,map_location='cpu',weights_only=True))
    x=torch.from_numpy(np.load(a.input).astype(np.float32))
    calibration=[torch.from_numpy(v.astype(np.float32)) for v in np.load(a.calibration)] if a.calibration else None
    package=compile_model(model,x,calibration,force_cpu=a.force_cpu,task_engine=a.task_engine,lut_cache=a.lut_cache);package.write(a.out,x.numpy())
    if a.simulate:
        from .sim import simulate
        simulate(a.out,a.vsim)
    print(json.dumps(dict(output=str(a.out),code_bytes=package.metadata['code_bytes'],free_bytes=package.metadata['free_bytes'],
                         schedule=[(n['name'],n['backend'],n['reason']) for n in package.nodes]),indent=2))

if __name__=='__main__':main()
