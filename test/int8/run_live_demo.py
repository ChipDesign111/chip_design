"""Generate and verify persistent online requests on the complete SoC RTL.

Generation needs compiler dependencies; --case EXISTING_PACKAGE --simulate-only
runs an already-generated case with Xcelium without PyTorch on the EDA host.
The host is modelled at Debug SBA/AXI, not at serial JTAG pins or USB hardware.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def generate(directory):
    import numpy as np
    import torch
    from torch import nn
    from compiler.compiler import compile_model
    from fpga.demo.firmware import write_resident
    torch.manual_seed(4107)
    model=nn.Sequential(nn.Linear(64,32),nn.ReLU(),nn.Linear(32,6)).eval()
    example=torch.linspace(-1,1,64).reshape(1,64)
    rng=np.random.default_rng(9102)
    calibration=[torch.from_numpy(rng.uniform(-1,1,(1,64)).astype(np.float32)) for _ in range(12)]
    package=compile_model(model,example,calibration_inputs=calibration)
    metadata=write_resident(package,directory)
    live=metadata['live_demo']
    xs=[np.zeros((1,64),dtype=np.int8),rng.integers(-128,128,(1,64),dtype=np.int16).astype(np.int8),
        np.array([[-128,127]*32],dtype=np.int8),np.full((1,64),127,dtype=np.int8)]
    expected=[package.reference(x.astype(np.float32)*live['input_scale'])[package.graph['output']][0] for x in xs]
    if len({bytes(y) for y in expected})<2:raise AssertionError('Test vectors must produce distinct real outputs')
    def words(data):
        data=bytes(data);data+=bytes((-len(data))%4)
        return struct.unpack('<%dI'%(len(data)//4),data)
    def write_words(name,values):(directory/name).write_text(''.join(f'{w&0xffffffff:08x}\n' for w in values),newline='\n')
    write_words('input_vectors.hex',[w for x in xs for w in words(x.tobytes())])
    write_words('expected_vectors.hex',[w for y in expected for w in words(y.tobytes())])
    write_words('expected_classes.hex',[int(np.argmax(y)) for y in expected])
    tag=int(live['package_tag'],16)
    config=dict(ROUNDS=len(xs),INPUT_BYTES=64,INPUT_WORDS=16,OUTPUT_WORDS=(live['output_bytes']+3)//4,
        NPU_STARTS_PER_ROUND=metadata['npu_core_starts'],HIDDEN_WORDS=8)
    sv=''.join(f'localparam integer {k}={v};\n' for k,v in config.items())
    hidden=metadata['tensors'][metadata['nodes'][0]['name']]
    config_hex=dict(INPUT_ADDRESS=live['input_address'],OUTPUT_ADDRESS=live['output_address'],
        HIDDEN_ADDRESS=hidden['address'],
        OUTPUT_TAIL_MASK=(1<<(8*(live['output_bytes']%4 or 4)))-1,
        PACKAGE_TAG_LOW=tag&0xffffffff,PACKAGE_TAG_HIGH=tag>>32)
    hidden_expected=[package.reference(x.astype(np.float32)*live['input_scale'])[metadata['nodes'][0]['name']][0] for x in xs]
    write_words('expected_hidden.hex',[w for y in hidden_expected for w in words(y.tobytes())])
    sv+=''.join(f"localparam [31:0] {k}=32'h{v:08x};\n" for k,v in config_hex.items())
    (directory/'live_config.svh').write_text(sv,newline='\n')
    (directory/'vectors.json').write_text(json.dumps(dict(
        purpose='Untrained deterministic arithmetic validation; not camera accuracy evidence',
        input_int8=[x.tolist() for x in xs],expected_int8=[y.tolist() for y in expected],
        calibration_overlap=False,reference_embedded_in_firmware=False),indent=2)+'\n',newline='\n')
    print('GENERATED',directory,flush=True)

def simulate(directory,xrun,timeout):
    build=directory/'build';build.mkdir(exist_ok=False)
    source=[]
    for line in (ROOT/'rtl/filelist.f').read_text().splitlines():
        line=line.strip()
        if not line or line.startswith('//'):continue
        source.append('+incdir+'+str(ROOT/line[8:]) if line.startswith('+incdir+') else str(ROOT/line))
    source+=['+incdir+'+str(directory),str(ROOT/'test/int8/tb_live_demo.sv')]
    (build/'sources.f').write_text('\n'.join(source)+'\n')
    command=[xrun,'-64bit','-sv','-timescale','1ns/1ps','-f',str(build/'sources.f'),
        '-top','tb_live_demo','-xmlibdirname',str(build/'xcelium.d'),'-l',str(directory/'xrun.log'),
        '+notimingchecks','-nospecify']
    result=subprocess.run(command,cwd=directory,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=timeout)
    (directory/'console.log').write_bytes(result.stdout)
    text=result.stdout.decode(errors='replace')
    match=re.search(r'LIVE_DEMO PASS rounds=(\d+) npu_starts=(\d+) activation_writes=(\d+) duplicate_requests=(\d+) rejected_requests=2',text)
    if result.returncode or not match or re.search(r'\*[EF],|FATAL|TIMEOUT',text):
        raise RuntimeError('Live SoC simulation failed:\n'+text[-6000:])
    sources=[p for p in (ROOT/'rtl').rglob('*') if p.is_file()]
    sources += [ROOT/'test/int8/tb_live_demo.sv',ROOT/'test/int8/run_live_demo.py',ROOT/'fpga/demo/firmware.py']
    report=dict(status='PASS',scope='Complete SoC RTL; host at forced Debug SBA boundary; no serial JTAG/USB/board validation',
        clock_period_ns=10,rtl_commit='0b5e34d',rounds=int(match[1]),npu_starts=int(match[2]),hidden_words_checked_per_round=8,
        sequence_rollover_checked='LIVE_SEQUENCE_WRAP PASS' in text,
        activation_writes=int(match[3]),duplicate_requests=int(match[4]),rejected_requests=2,
        responses=[dict(sequence=int(s),status=int(t),error=int(e),cycles=int(c)) for s,t,e,c in
            re.findall(r'LIVE_RESPONSE seq=(\d+) status=(\d+) error=(\d+) cycles=(\d+)',text)],
        source_sha256={p.relative_to(ROOT).as_posix():sha(p) for p in sources},
        files_sha256={p.name:sha(p) for p in directory.iterdir() if p.is_file() and p.name!='results.json'})
    assert len(report['responses'])==report['rounds']+2, 'Missing real response record'
    assert report['sequence_rollover_checked'], 'Missing sequence rollover check'
    (directory/'results.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('source_sha256','files_sha256')},indent=2),flush=True)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--case',type=Path,required=True)
    p.add_argument('--simulate',action='store_true');p.add_argument('--simulate-only',action='store_true')
    p.add_argument('--xrun',default='xrun');p.add_argument('--timeout',type=int,default=600)
    args=p.parse_args();directory=args.case.resolve()
    if not args.simulate_only:
        directory.mkdir(parents=True,exist_ok=False);generate(directory)
    if args.simulate or args.simulate_only:
        xrun=shutil.which(args.xrun)
        if not xrun:p.error('xrun not found; source the course EDA environment first')
        simulate(directory,xrun,args.timeout)

if __name__=='__main__':main()
