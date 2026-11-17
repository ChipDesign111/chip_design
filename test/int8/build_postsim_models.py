"""Build checked CPU/NPU payloads, including task modes, for TT gate simulation."""
import argparse,hashlib,json,shutil,sys
from pathlib import Path
import numpy as np
import torch
from torch import nn
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from compiler.compiler import compile_model
from model.generic_mixed.model import build_model

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--task-engine',action='store_true');parser.add_argument('--lut-cache',action='store_true')
    parser.add_argument('--verify-rtl',action='store_true');parser.add_argument('--vsim',default='vsim');args=parser.parse_args()
    args.out.mkdir(parents=True,exist_ok=True)
    if any(args.out.iterdir()):raise ValueError('Use a new empty firmware directory')
    data=ROOT/'model/generic_mixed/data';mixed=build_model()
    mixed.load_state_dict(torch.load(data/'weights.pth',map_location='cpu',weights_only=True))
    x=torch.from_numpy(np.load(data/'input.npy'))
    calibration=[torch.from_numpy(v) for v in np.load(data/'calibration.npy')]
    torch.manual_seed(719);tiled=nn.Sequential(nn.Linear(65,41),nn.Tanh()).eval()
    cases=[('model_mixed',mixed,x,calibration),('model_tiled',tiled,torch.linspace(-1,1,65).reshape(1,65),None)]
    if args.task_engine:
        from run_task_compiler import special_network
        cases += [('task_deep',nn.Sequential(nn.Linear(17,13),nn.LeakyReLU(0.125),nn.Linear(13,9),nn.ReLU6(),nn.Linear(9,5),nn.Tanh()).eval(),torch.linspace(-3,3,34).reshape(2,17),None),
            ('task_chain',nn.Sequential(nn.Linear(48,24),nn.ReLU(),nn.Linear(24,8)).eval(),torch.linspace(-1,1,96).reshape(2,48),None),
            ('task_split_chain',nn.Sequential(nn.Linear(65,41),nn.ReLU(),nn.Linear(41,9)).eval(),torch.linspace(-1,1,65).reshape(1,65),None),
            ('task_lut',nn.Sequential(nn.Sigmoid(),nn.Tanh()).eval(),torch.linspace(-8,8,128).reshape(4,32),None),
            ('task_special',special_network(),torch.linspace(0.5,1,256).reshape(4,64),None)]
    records={}
    for name,model,example,calibration in cases:
        package=compile_model(model,example,calibration,task_engine=args.task_engine,lut_cache=args.lut_cache)
        directory=args.out/name;values=package.write(directory,example.numpy())
        checks=[]
        for tensor,array in values.items():
            spec=package.metadata['tensors'][tensor]
            if spec.get('storage') in ('internal','fused','special_fc','special_hidden'):continue
            for sample,row in enumerate(array):
                raw=row.tobytes()+bytes(spec['stride']-len(row))
                for offset in range(0,len(raw),4):
                    checks.append(dict(address=spec['address']+sample*spec['stride']+offset,
                                       expected=int.from_bytes(raw[offset:offset+4],'little'),mask=0xffffffff))
        if args.task_engine:
            last_node=next(n for n in reversed(package.nodes) if 'segment' in n or 'special_segment' in n)
            if 'segment' in last_node:
                last=package.metadata['task_segments'][last_node['segment']]
                checks.extend([dict(address=0x70001604,expected=9,mask=0xffffffff),
                    dict(address=0x70001618,expected=0,mask=0xffffffff),
                    dict(address=0x70001620,expected=last['count'],mask=0xffffffff)])
                desc=last['tasks'][-1];d=desc['descriptor'];output=values[desc['output_node']]
                for b,row in enumerate(output):
                    part=row[desc['output_offset']:desc['output_offset']+d['n']].tobytes()
                    for offset in range(0,len(part),4):
                        word=part[offset:offset+4]
                        checks.append(dict(address=0x70001680+b*32+offset,expected=int.from_bytes(word,'little'),mask=(1<<(8*len(word)))-1))
            else:
                last=package.metadata['special_segments'][last_node['special_segment']]
                hidden=values[last['hidden']]
                for b,row in enumerate(hidden):
                    for offset in range(0,32,4):
                        checks.append(dict(address=0x70000000+[0xa80,0xc40,0x1200,0x1240][b]+offset,
                            expected=int.from_bytes(row[offset:offset+4].tobytes(),'little'),mask=0xffffffff))
                checks.append(dict(address=0x70000004,expected=1,mask=0xffffffff))
        else:
            last=[n for n in package.nodes if n['backend']=='NPU'][-1]['jobs'][-1]
            checks.extend([dict(address=0x70000028,expected=last['batch']*((last['k']+1)//2)*((last['n']+7)//8),mask=0xffffffff),
                           dict(address=0x7000002c,expected=0,mask=0xffffffff),dict(address=0x70000004,expected=1,mask=0xffffffff)])
        target=args.out/('firmware_'+name+'.hex');shutil.copyfile(directory/'firmware.hex',target)
        sidecar=target.with_suffix('.checks.json');sidecar.write_text(json.dumps(checks,indent=2)+'\n')
        if args.verify_rtl:
            from compiler.sim import simulate
            simulate(directory,args.vsim,word_checks=checks)
        records[name]=dict(firmware=target.name,sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
                           checks=sidecar.name,checks_sha256=hashlib.sha256(sidecar.read_bytes()).hexdigest(),words=len(checks),rtl_verified=args.verify_rtl)
    (args.out/'manifest.json').write_text(json.dumps(records,indent=2)+'\n')
    print(json.dumps(records,indent=2))

if __name__=='__main__':main()
