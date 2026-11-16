"""Exercise single/dual mode switching, real DMA, tails and retained partial sums."""
import argparse,datetime,hashlib,json,random,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from compiler.tiling import plan_fc,reference_fc
from run import execute,pack


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--soc',action='store_true');parser.add_argument('--vsim',default='vsim');args=parser.parse_args()
    run=ROOT/'test/int8/runs'/('single_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S'))
    run.mkdir(parents=True)
    prefix=(ROOT/'test/int8/tb_tiled_dma.sv').read_text().split('    initial begin\n',1)[0]
    prefix=prefix.replace('module tb_tiled_dma;', 'module tb_single_fc;')
    statements=['#1;rst_n=0;repeat(3) @(negedge clk);rst_n=1;']
    def put(addr,value): statements.append(f"put('h{addr:x},32'h{value&0xffffffff:08x});")
    def check(addr,value): statements.append(f"check('h{addr:x},32'h{value&0xffffffff:08x});")
    # Continuation is rejected before a valid single-FC result exists.
    put(0x20,0x80000000);put(0x3c,3);put(0,1);check(4,4);put(0,2)
    shapes=[(1,1,1),(7,5,2),(8,8,3),(9,10,4),(63,31,1),(64,32,4),
            (65,17,2),(97,41,4),(128,16,1),(3,64,3)]
    for ci,(k,n,b) in enumerate(shapes):
        r=random.Random(72000+ci)
        xs=[[r.randint(-128,127) for _ in range(k)] for _ in range(b)]
        ws=[[r.randint(-128,127) for _ in range(k)] for _ in range(n)]
        bias=[r.randint(-10000,10000) for _ in range(n)]
        if ci==5: bias[0]=(1<<21)-1;bias[1]=-(1<<21)
        jobs,image=plan_fc(xs,ws,bias)
        mem=[0]*2048;mem[:len(image)//4]=pack(list(image))
        filename=run/f'weights_{ci}.hex'
        filename.write_text(''.join(f'{v:08x}\n' for v in mem))
        statements.append(f'$readmemh("{filename.as_posix()}",mem);')
        golden=reference_fc(xs,ws,bias)
        for ji,job in enumerate(jobs):
            put(0x3c,3 if job['accumulate'] else 1)
            put(0x80,job['k']);put(0x84,job['n']);put(0x18,b);put(0x20,job['source'])
            for sample,row in enumerate(job['inputs']):
                addr=[0x40,0xc00,0x1000,0x1040][sample]
                for wi,word in enumerate(pack(row)):put(addr+wi*4,word)
            for oi,value in enumerate(job['bias']):put(0x9c0+oi*4,value)
            put(0,1)
            statements.append('await_done();')
            check(4,1);check(0x2c,0);check(0x30,(job['k']+1)//2)
            check(0x28,b*((job['k']+1)//2)*((job['n']+7)//8))
            if ji+1==len(jobs) or not jobs[ji+1]['accumulate']:
                for sample in range(b):
                    for oi in range(job['n']):check(0x1400+sample*128+oi*4,golden[sample][job['output_offset']+oi])
                if job['n']<32:check(0x1400+job['n']*4,0)
            put(0,2)
        statements.append(f'$display("SINGLE_FC CASE {ci} PASS K={k} N={n} B={b} jobs={len(jobs)}");')
    # Changing output width or batch cannot reuse another partial sum context.
    put(0x3c,3);put(0x84,31);put(0,1);check(4,4);put(0,2)
    put(0x84,32);put(0x18,2);put(0,1);check(4,4);put(0,2)
    # Invalid shape, layout mode and SRAM range; writes leave legal config intact.
    for addr,value in [(0x80,0),(0x80,65),(0x84,0),(0x84,33),(0x3c,2)]:
        put(addr,value);check(4,4);put(0,2)
    put(0x3c,1);put(0x20,0x80001ffc);put(0,1);check(4,4);put(0,2)
    # Re-enter the original two-layer path in the same instance, then verify
    # that legacy execution revoked the previous single-layer partial sums.
    put(0x3c,0)
    statements.append('$readmemh("'+(run/'legacy.hex').as_posix()+'",mem);')
    statements.append('configure();put(0,1);await_done();check(4,1);')
    from run import make_case
    (run/'legacy.hex').write_text(''.join(f'{v:08x}\n' for v in make_case(1)))
    statements.append("for(j=0;j<6;j=j+1) check('hb00+j*4,mem['h1c20/4+j]);")
    put(0,2);put(0x3c,3);put(0,1);check(4,4);put(0,2)
    # A failed single-layer DMA invalidates retained sums and prevents resume.
    put(0x3c,1);put(0x80,64);put(0x84,32);put(0x18,1);put(0x20,0x80000000)
    statements.append('inject_error=1;');put(0,1);put(0x80,1)
    statements.append('await_done();');check(4,5);check(0x80,64)
    statements.append('inject_error=0;');put(0,2);put(0x3c,3);put(0,1);check(4,4);put(0,2)
    statements.append('rst_n=0;repeat(3) @(negedge clk);rst_n=1;')
    put(0x3c,3);put(0x20,0x80000000);put(0,1);check(4,4)
    statements.append('$display("SINGLE_FC PASS");$finish;')
    (run/'tb_single_fc.sv').write_text(prefix+'    initial begin\n'+'\n'.join(statements)+'\nend\nendmodule\n')
    sources=['rtl/npu/har_weight_store.sv','rtl/npu/har_npu_core.sv','rtl/npu/simple_npu_top.sv','rtl/dma/har_dma.sv']
    execute(['iverilog','-g2012','-s','tb_single_fc','-o','single.vvp']+[ROOT/s for s in sources]+[run/'tb_single_fc.sv'],run,'compile_single')
    execute(['vvp','single.vvp'],run,'single','SINGLE_FC PASS')
    if args.soc: run_soc(run,args.vsim)
    source_paths=['rtl/npu/har_npu_core.sv','rtl/npu/simple_npu_top.sv',
                  'rtl/npu/har_weight_store.sv','rtl/dma/har_dma.sv',
                  'compiler/tiling.py','test/int8/run_single_fc.py','test/int8/tb_tiled_dma.sv']
    hashes={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in source_paths}
    (run/'result.json').write_text(json.dumps(dict(passed=True,shapes=shapes,soc=args.soc,source_sha256=hashes),indent=2))
    print('Results: '+str(run))

def run_soc(run,vsim):
    from assembler import Assembler
    r=random.Random(951)
    xs=[[r.randint(-128,127) for _ in range(65)]]
    ws=[[r.randint(-128,127) for _ in range(65)] for _ in range(9)]
    bias=[r.randint(-5000,5000) for _ in range(9)]
    jobs,image=plan_fc(xs,ws,bias,base=0x80001000)
    a=Assembler();a.compact_li=True;a.li(20,0x70000000)
    def put(offset,value):
        a.li(5,value)
        if offset<2048:a.sw(5,20,offset)
        else:a.li(21,0x70000000+offset);a.sw(5,21)
    for ji,job in enumerate(jobs):
        put(0x3c,3 if job['accumulate'] else 1)
        put(0x80,job['k']);put(0x84,job['n']);put(0x18,1);put(0x20,job['source'])
        for wi,word in enumerate(pack(job['inputs'][0])):put(0x40+4*wi,word)
        for oi,value in enumerate(bias):put(0x9c0+4*oi,value)
        put(0,1);a.label('poll'+str(ji));a.lw(5,20,4);a.andi(6,5,2)
        a.branch('bne',6,0,'poll'+str(ji));a.li(6,1);a.branch('bne',5,6,'fail')
        put(0,2)
    a.li(22,0x70001400)
    for oi,value in enumerate(reference_fc(xs,ws,bias)[0]):
        a.lw(5,22,oi*4);a.li(6,value);a.branch('bne',5,6,'fail')
    a.lw(5,20,0x2c);a.branch('bne',5,0,'fail')
    a.li(5,0xc0dec0de);a.jump('finish');a.label('fail');a.li(5,0xdeadbeef)
    a.label('finish');a.li(6,0x80001fe0);a.sw(5,6);a.label('halt');a.jump('halt');a.resolve()
    assert len(a.words)*4<0x1000
    mem=[0]*2048;mem[:len(a.words)]=a.words;mem[0x1000//4:0x1000//4+len(image)//4]=pack(list(image))
    (run/'firmware.hex').write_text(''.join(f'{v:08x}\n' for v in mem))
    (run/'firmware.S').write_text('\n'.join(a.listing)+'\n')
    fl=[]
    for line in (ROOT/'rtl/filelist.f').read_text().splitlines():
        if line.startswith('+incdir+'):fl.append('+incdir+'+(ROOT/line[8:]).as_posix())
        elif line.strip():fl.append((ROOT/line).as_posix())
    fl.append((ROOT/'test/int8/tb_soc.sv').as_posix());(run/'soc.f').write_text('\n'.join(fl)+'\n')
    commands=['onerror {quit -code 1}','onbreak {resume}','vlib work','vmap work work','vlog -sv -f soc.f',
              'vsim -suppress 12110 -novopt -onfinish stop work.tb_soc','run -all',
              'set status [examine -radix hex /tb_soc/magic]',
              'if {![string equal -nocase $status c0dec0de]} {quit -code 3}','quit -code 0']
    (run/'soc.do').write_text('\n'.join(commands)+'\n')
    execute([vsim,'-c','-do','do soc.do'],run,'single_soc','INT8_SOC PASS')

if __name__=='__main__': main()
