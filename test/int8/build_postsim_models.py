"""Build checked mixed-network and doubly tiled FC payloads for TT gate simulation."""
import argparse,hashlib,json,shutil,sys
from pathlib import Path
import numpy as np
import torch
from torch import nn
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from compiler.compiler import compile_model
from model.generic_mixed.model import build_model

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    args.out.mkdir(parents=True,exist_ok=True)
    if any(args.out.iterdir()):raise ValueError('Use a new empty firmware directory')
    data=ROOT/'model/generic_mixed/data';mixed=build_model()
    mixed.load_state_dict(torch.load(data/'weights.pth',map_location='cpu',weights_only=True))
    x=torch.from_numpy(np.load(data/'input.npy'))
    calibration=[torch.from_numpy(v) for v in np.load(data/'calibration.npy')]
    torch.manual_seed(719);tiled=nn.Sequential(nn.Linear(65,41),nn.Tanh()).eval()
    cases=[('model_mixed',mixed,x,calibration),('model_tiled',tiled,torch.linspace(-1,1,65).reshape(1,65),None)]
    records={}
    for name,model,example,calibration in cases:
        package=compile_model(model,example,calibration)
        directory=args.out/name;values=package.write(directory,example.numpy())
        checks=[]
        for tensor,array in values.items():
            spec=package.metadata['tensors'][tensor]
            for sample,row in enumerate(array):
                raw=row.tobytes()+bytes(spec['stride']-len(row))
                for offset in range(0,len(raw),4):
                    checks.append(dict(address=spec['address']+sample*spec['stride']+offset,
                                       expected=int.from_bytes(raw[offset:offset+4],'little'),mask=0xffffffff))
        last=[n for n in package.nodes if n['backend']=='NPU'][-1]['jobs'][-1]
        checks.extend([dict(address=0x70000028,expected=last['batch']*((last['k']+1)//2)*((last['n']+7)//8),mask=0xffffffff),
                       dict(address=0x7000002c,expected=0,mask=0xffffffff),dict(address=0x70000004,expected=1,mask=0xffffffff)])
        target=args.out/('firmware_'+name+'.hex');shutil.copyfile(directory/'firmware.hex',target)
        sidecar=target.with_suffix('.checks.json');sidecar.write_text(json.dumps(checks,indent=2)+'\n')
        records[name]=dict(firmware=target.name,sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
                           checks=sidecar.name,checks_sha256=hashlib.sha256(sidecar.read_bytes()).hexdigest(),words=len(checks))
    (args.out/'manifest.json').write_text(json.dumps(records,indent=2)+'\n')
    print(json.dumps(records,indent=2))

if __name__=='__main__':main()
