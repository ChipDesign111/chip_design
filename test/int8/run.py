"""Reproducible INT8 RTL tests. Runtime files stay in ignored test/int8/runs/."""
import argparse,datetime,hashlib,json,random,re,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from model.reference.tile_layout import weights,parameters
def pack(v):return [sum((x&255)<<(8*j) for j,x in enumerate(v[i:i+4])) for i in range(0,len(v),4)]
def i32(v):return ((v+2**31)%2**32)-2**31
def make_case(seed):
    r=random.Random(17000+seed)
    w1=[[r.randint(-128,127) for _ in range(64)] for _ in range(32)]
    w2=[[r.randint(-128,127) for _ in range(32)] for _ in range(6)]
    b1=[r.randint(-100000,100000) for _ in range(32)]
    b2=[r.randint(-100000,100000) for _ in range(6)]
    mult=[1,65535,123,7][seed%4];shift=[0,31,14,7][seed%4]
    batch=8 if seed%6==0 else 1+seed%2
    xs=[[r.randint(-128,127) for _ in range(64)] for _ in range(batch)]
    if seed%8==6:mult=0
    if seed%5==0:b1[0]=2**31-1;b2[0]=-2**31
    if seed>=10000:
        w1,w2=weights();q=parameters();b1=q['fc1']['bias_int32'];b2=q['fc2']['bias_int32']
        fixture=json.loads((HERE/'har_uci24.json').read_text());i=(seed-10000)*8
        xs=fixture['x_int8'][i:i+8];mult=q['hidden_requant']['mul'];shift=q['hidden_requant']['shift'];batch=8
    mem=[0]*2048
    def store(offset,values):mem[offset//4:offset//4+len(values)]=[x&0xffffffff for x in values]
    # Tile-major order: input pair, output neuron, lane.
    w1_address=0xffc if seed<10000 and seed%4==0 else 0x1000
    store(w1_address,pack([w1[o][2*t+k] for t in range(32) for o in range(32) for k in range(2)]))
    # Each FC2 bank packet holds eight packed six-byte output rows (48 B).
    store(0x1800,pack([w2[o][t] for t in range(32) for o in range(6)]))
    store(0x1900,b1);store(0x1980,b2)
    for n,x in enumerate(xs):store(0x1a00+n*64,pack(x))
    for n,x in enumerate(xs):
        acc=[i32(b1[o]+sum(a*b for a,b in zip(x,w1[o]))) for o in range(32)]
        h=[min(127,(max(0,a)*mult+((1<<(shift-1)) if shift else 0))>>shift) for a in acc]
        y=[i32(b2[o]+sum(a*b for a,b in zip(h,w2[o]))) for o in range(6)]
        store(0x1c00+n*64,pack(h)+y+[max(range(6),key=lambda o:y[o])])
    store(0x1f00,[mult,shift,batch,0x80000000+w1_address])
    return mem
def execute(command,run,name,marker=None):
    result=subprocess.run([str(x) for x in command],cwd=run,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=300)
    (run/(name+'.log')).write_text(result.stdout,encoding='utf-8')
    if result.returncode or (marker and marker not in result.stdout) or re.search(r'FATAL:|# \*\* (?:Fatal|Error):|TIMEOUT',result.stdout):
        print(result.stdout[-7000:]);raise RuntimeError(name+' failed')
    print(name+': PASS',flush=True)
    return result.stdout
def main():
    p=argparse.ArgumentParser();p.add_argument('--count',type=int,default=32);p.add_argument('--soc',action='store_true');p.add_argument('--trained',action='store_true');p.add_argument('--vsim',default='vsim');p.add_argument('--vendor-model',type=Path);args=p.parse_args()
    run=HERE/'runs'/datetime.datetime.now().strftime('%Y%m%d_%H%M%S');run.mkdir(parents=True)
    source_files=[p for folder in ['rtl','test/int8'] for p in (ROOT/folder).rglob('*') if p.is_file() and 'runs' not in p.parts and '__pycache__' not in p.parts]
    source_files.append(ROOT/'model/reference/tile_layout.py')
    source_sha={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in source_files}
    (run/'source_manifest.json').write_text(json.dumps(source_sha,indent=2)+'\n')
    seeds=list(range(args.count))+(list(range(10000,10003)) if args.trained else [])
    for index,seed in enumerate(seeds):(run/('case_%d.hex'%index)).write_text(''.join('%08x\n'%v for v in make_case(seed)))
    sources=['rtl/npu/har_weight_store.sv','rtl/npu/har_npu_core.sv','rtl/npu/simple_npu_top.sv','rtl/dma/har_dma.sv','test/int8/tb_tiled_dma.sv']
    execute(['iverilog','-g2012','-s','tb_tiled_dma','-o','test.vvp']+[ROOT/x for x in sources],run,'compile_unit')
    output=execute(['vvp','test.vvp','+DIR='+run.as_posix(),'+COUNT='+str(len(seeds))],run,'unit','INT8_TILED_DMA PASS')
    print('\n'.join(x for x in output.splitlines() if 'CASE' in x)[-3000:])
    if args.soc:
        from firmware import build
        build(run)
        fl=[]
        for line in (ROOT/'rtl/filelist.f').read_text().splitlines():
            if line.startswith('+incdir+'):fl.append('+incdir+'+(ROOT/line[8:]).as_posix())
            elif line.strip():fl.append((ROOT/line).as_posix())
        if args.vendor_model:
            if not args.vendor_model.is_file():raise ValueError('Missing authorized SRAM model')
            fl=['+define+CHIP_USE_RA1SHD',args.vendor_model.resolve().as_posix()]+fl
        fl.append((HERE/'tb_soc.sv').as_posix());(run/'soc.f').write_text('\n'.join(fl)+'\n')
        commands=['onerror {quit -code 1}','onbreak {resume}','vlib work','vmap work work','vlog -sv -f soc.f','vsim -suppress 12110 -novopt -onfinish stop '+('+notimingchecks ' if args.vendor_model else '')+'work.tb_soc','run -all','set status [examine -radix hex /tb_soc/magic]','if {![string equal -nocase $status c0dec0de]} {quit -code 3}','quit -code 0']
        (run/'soc.do').write_text('\n'.join(commands)+'\n');execute([args.vsim,'-c','-do','do soc.do'],run,'soc','INT8_SOC PASS')
    if any(hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=value for name,value in source_sha.items()):raise RuntimeError('Source changed during functional run')
    (run/'result.json').write_text(json.dumps({'unit_cases':len(seeds),'trained_samples':24 if args.trained else 0,'soc':args.soc,'vendor_model_sha256':hashlib.sha256(args.vendor_model.read_bytes()).hexdigest() if args.vendor_model else None,'passed':True},indent=2)+'\n')
    print('Results: '+str(run))
if __name__=='__main__':main()
