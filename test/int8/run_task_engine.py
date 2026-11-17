"""Real task controller + 16-MAC core + DMA, with stalled AXI memory model."""
import argparse,datetime,hashlib,json,random,struct,sys
from dataclasses import replace
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from compiler.task_abi import Task,Op,Activation,validate_segment,fc_output,activate
from compiler.tiling import plan_fc,reference_fc
from run import execute


class Image:
    def __init__(self):self.data=bytearray(b'\xa5'*8192);self.top=0
    def alloc(self,data,alignment=4):
        p=(self.top+alignment-1)&-alignment
        self.data[p:p+len(data)]=data;self.top=p+len(data)
        assert self.top<=0x1800,('Fixture too large',self.top)
        return 0x80000000+p
    def tensor(self,rows):
        stride=(len(rows[0])+3)&~3
        payload=bytearray(b'\xa5'*(len(rows)*stride))
        for b,row in enumerate(rows):payload[b*stride:b*stride+len(row)]=bytes(v&255 for v in row)
        return self.alloc(payload),stride
    def output(self,rows,width):return self.tensor([[ -91]*width for _ in range(rows)])


def linear(image,xs,ws,bias,source,stride,*,keep=False,internal=False,activation=Activation.NONE,context=17,lut=0):
    jobs,weight_data=plan_fc(xs,ws,bias,base=0x80000000)
    weight_base=image.alloc(weight_data)
    bias_base=image.alloc(struct.pack('<'+'i'*len(bias),*bias))
    b=len(xs);n=len(ws);k=len(xs[0])
    destination,out_stride=(0,0) if keep else image.output(b,n)
    tasks=[]
    for job in jobs:
        no=job['output_offset']
        # plan_fc is ordered N-block then K-block.
        local_index=len(tasks)%((k+63)//64);ko=local_index*64
        last=ko+job['k']==k
        tasks.append(Task(k=job['k'],n=job['n'],batch=b,
            source=0 if internal else source+ko,weights=weight_base+job['source']-0x80000000,
            bias=0 if job['accumulate'] else bias_base+no*4,
            destination=(0 if keep or not last else destination+no),
            input_stride=0 if internal else stride,output_stride=0 if keep or not last else out_stride,
            initialize=not job['accumulate'],last_k=last,input_internal=internal,keep_output=keep,
            end_segment=False,fc_multiplier=17,fc_shift=7,act_multiplier=3,act_shift=2,
            negative_multiplier=5,negative_shift=5,activation=activation if last else Activation.NONE,
            clamp_max=57,lut_address=lut if last else 0,context=context+no))
    raw=reference_fc(xs,ws,bias)
    q=[[fc_output(v,tasks[-1],None if not lut else image.data[lut-0x80000000:lut-0x80000000+256]) for v in row] for row in raw]
    return tasks,q,destination,out_stride


def finish(image,tasks,outputs):
    tasks[-1]=replace(tasks[-1],end_segment=True)
    allow_cache=any(t.lut_cache for t in tasks)
    validate_segment(0x80001800,tasks,allow_cache=allow_cache)
    image.data[0x1800:0x1800+len(tasks)*64]=b''.join(t.pack(allow_cache=allow_cache) for t in tasks)
    expected=bytearray(image.data)
    for address,stride,rows in outputs:
        for b,row in enumerate(rows):expected[address-0x80000000+b*stride:address-0x80000000+b*stride+len(row)]=bytes(v&255 for v in row)
    return bytes(image.data),bytes(expected),len(tasks)


def cases(lut_cache=False):
    rng=random.Random(71482);results=[]
    for ci,(k,n,b) in enumerate([(1,1,1),(7,5,2),(9,10,3),(63,31,4),(64,32,4),(65,41,2)]):
        image=Image();xs=[[rng.randrange(-8,8) for _ in range(k)] for _ in range(b)]
        ws=[[rng.randrange(-8,8) for _ in range(k)] for _ in range(n)]
        bias=[rng.randrange(-1000,1000) for _ in range(n)]
        source,stride=image.tensor(xs)
        tasks,q,dst,os=linear(image,xs,ws,bias,source,stride,activation=Activation(ci%4))
        raw,gold,count=finish(image,tasks,[(dst,os,q)])
        results.append((f'fc_{k}_{n}_{b}',raw,gold,count,0,ci==3))
    # All INT8 inputs, all six modes, multiple batch rows and LUT word lanes.
    for act in Activation:
        image=Image();rows=[list(range(-128+i*32,-128+(i+1)*32)) for i in range(8)]
        source,stride=image.tensor(rows);dst,os=image.output(8,32)
        lut_bytes=bytes(((i*73)%256) for i in range(256));lut=image.alloc(lut_bytes) if act>=4 else 0
        tasks=[Task(op=Op.ACTIVATION,k=0,n=32,batch=4,source=source+b*32,
            weights=0,bias=0,destination=dst+b*32,input_stride=32,output_stride=32,
            initialize=False,fc_multiplier=0,activation=act,act_multiplier=19,act_shift=4,
            negative_multiplier=5,negative_shift=7,clamp_max=67,lut_address=lut,end_segment=False,lut_cache=lut_cache and act>=4)
            for b in [0,4]]
        q=[[activate(v,act,19,4,5,7,67,lut_bytes) for v in row] for row in rows]
        raw,gold,count=finish(image,tasks,[(dst,os,q)])
        results.append((f'activation_{act.name}',raw,gold,count,0,False))
    # Same chain with forwarding and explicit SRAM spill; integers identical.
    for internal in [False,True]:
        rng=random.Random(33751)
        image=Image();xs=[[rng.randrange(-8,8) for _ in range(48)] for _ in range(2)]
        source,stride=image.tensor(xs);tasks=[];outputs=[]
        for li,(k,n) in enumerate([(48,24),(24,8)]):
            ws=[[rng.randrange(-8,8) for _ in range(k)] for _ in range(n)]
            bias=[rng.randrange(-1000,1000) for _ in range(n)]
            ts,q,dst,os=linear(image,xs,ws,bias,source,stride,keep=internal and li==0,
                internal=internal and li==1,activation=Activation.RELU if li==0 else Activation.NONE)
            tasks+=ts
            if dst:outputs.append((dst,os,q))
            xs=q;source=dst;stride=os
        raw,gold,count=finish(image,tasks,outputs)
        results.append((f'chain_{"internal" if internal else "sram"}',raw,gold,count,0,False))
    # Independent malformed wire fields, without using the host validator.
    raw,gold,count=results[0][1:4]
    mutations=[('version',0,0x00130100,8),('reserved',14,1,4),('end',0,0x00030101,4),
        ('k_zero',1,0x00010100,7),('weights_align',3,0x80000001,2),
        ('source_range',2,0x80002000,3),('output_table',5,0x80001800,3),
        ('no_partial',0,0x00120101,4), # INIT=0 but nonzero bias is malformed
        ('cache_on_non_lut' if lut_cache else 'cache_unsupported',0,0x00330101,4 if lut_cache else 8)]
    for name,word,value,code in mutations:
        data=bytearray(raw);struct.pack_into('<I',data,0x1800+word*4,value)
        results.append((name,bytes(data),gold,count,code,False))
    data=bytearray(raw);bias=struct.unpack_from('<I',data,0x1810)[0]
    struct.pack_into('<I',data,bias-0x80000000,0x7fffffff)
    results.append(('bias_value',bytes(data),gold,count,7,False))
    # A changed context in the second K block cannot consume the first sums.
    raw,gold,count=results[5][1:4];data=bytearray(raw)
    struct.pack_into('<I',data,0x1800+64+52,999)
    results.append(('partial_context',bytes(data),gold,count,5,False))
    if lut_cache:
        for value in [1,2]:
            image=Image();source,stride=image.tensor([[0]]);dst,os=image.output(1,1)
            lut=image.alloc(bytes([value]*256))
            t=Task(op=Op.ACTIVATION,k=0,n=1,batch=1,source=source,weights=0,bias=0,
                destination=dst,input_stride=stride,output_stride=os,initialize=False,fc_multiplier=0,
                activation=Activation.SIGMOID,lut_address=lut,lut_cache=True)
            raw,gold,count=finish(image,[t],[(dst,os,[[value]])])
            results.append((f'cache_new_segment_{value}',raw,gold,count,0,False))
        image=Image();source,stride=image.tensor([[0]]);outs=[image.output(1,1) for _ in range(3)]
        lut_a=image.alloc(bytes([37]*256));lut_b=image.alloc(bytes([91]*256));tasks=[]
        for (dst,os),lut,cached in zip(outs,[lut_a,lut_b,lut_a],[True,False,True]):
            tasks.append(Task(op=Op.ACTIVATION,k=0,n=1,batch=1,source=source,weights=0,bias=0,
                destination=dst,input_stride=stride,output_stride=os,initialize=False,fc_multiplier=0,
                activation=Activation.TANH,lut_address=lut,lut_cache=cached,end_segment=False))
        raw,gold,count=finish(image,tasks,[(dst,os,[[v]]) for (dst,os),v in zip(outs,[37,91,37])])
        results.append(('cache_direct_interleave',raw,gold,count,0,False))
    return results


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--lut-cache',action='store_true');args=parser.parse_args()
    run=ROOT/'test/int8/runs'/('task_engine_'+('cache_' if args.lut_cache else '')+datetime.datetime.now().strftime('%Y%m%d_%H%M%S'))
    run.mkdir(parents=True)
    prefix=(ROOT/'test/int8/tb_task_engine.sv').read_text()
    if args.lut_cache:prefix=prefix.replace('CACHE_SUPPORTED=0','CACHE_SUPPORTED=1')
    statements=['initial begin #1;repeat(3) @(negedge clk);rst_n=1;',f"check('h1610,'h014020{'ff' if args.lut_cache else 'bf'});"]
    records=[]
    for name,raw,gold,count,code,protect in cases(args.lut_cache):
        for suffix,data in [('input',raw),('golden',gold)]:
            (run/f'{name}_{suffix}.hex').write_text(''.join(f'{v[0]:08x}\n' for v in struct.iter_unpack('<I',data)))
        statements.append(f'run_case("{name}_input.hex","{name}_golden.hex",{count},{code},{int(protect)});')
        records.append(dict(name=name,tasks=count,error=code,input_sha256=hashlib.sha256(raw).hexdigest()))
    statements += [
        'inject_read_error=1;run_case("fc_1_1_1_input.hex","fc_1_1_1_golden.hex",1,6,0);inject_read_error=0;',
        'inject_write_error=1;run_case("fc_7_5_2_input.hex","fc_7_5_2_golden.hex",1,6,0);inject_write_error=0;',
        "check('h1620,0);",
        'run_case("fc_7_5_2_input.hex","fc_7_5_2_golden.hex",1,0,0);',
        'reset_case(2);reset_case(5);reset_case(12);reset_case(15);reset_case(17);reset_case(22);',
        "legacy_compat();invalid_start('h80001804,1,2);invalid_start('h80001fc0,2,3);invalid_start('h80001800,0,7);invalid_start('h80001800,129,7);",
        "$display(\"TASK_ENGINE PASS\");$finish;end",'initial begin #20000000;$fatal(1,"Task watchdog");end','endmodule']
    (run/'tb_task_engine.sv').write_text(prefix+'\n'+'\n'.join(statements)+'\n')
    sources=['rtl/npu/har_task_scale.sv','rtl/npu/har_task_engine.sv','rtl/npu/har_weight_store.sv',
        'rtl/npu/har_npu_core.sv','rtl/npu/simple_npu_top.sv','rtl/dma/har_dma.sv','rtl/soc/my_npu_subsystem.sv']
    execute(['iverilog','-g2012','-s','tb_task_engine','-o','task.vvp']+[ROOT/s for s in sources]+[run/'tb_task_engine.sv'],run,'compile')
    output=execute(['vvp','task.vvp'],run,'simulate','TASK_ENGINE PASS')
    print(output)
    (run/'result.json').write_text(json.dumps(dict(passed=True,cases=records,source_sha256={s:hashlib.sha256((ROOT/s).read_bytes()).hexdigest() for s in sources}),indent=2))
    print('Results: '+str(run))
if __name__=='__main__':main()
