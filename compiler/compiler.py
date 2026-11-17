"""Ahead-of-time INT8 graph compiler for the fixed 8KiB RV32IM/NPU SoC."""
import hashlib,json,struct
from pathlib import Path
import numpy as np
from .frontend import capture,CompileError
from .rv32 import Program,BASE
from .tiling import plan_fc

SRAM_BYTES=8192
DATA_TOP=0x1fc0  # Reserve statistics and boot-completion mailboxes.

def quantize(value,scale):
    value=np.asarray(value)
    if not np.isfinite(value).all():raise CompileError('Nonfinite runtime input or quantization value')
    return np.clip(np.rint(value/scale),-128,127).astype(np.int8)

def coefficients(ratios,bounds):
    for shift in range(24,-1,-1):
        mult=[int(round(r*(1<<shift))) for r in ratios]
        bound=sum(abs(m)*b for m,b in zip(mult,bounds))+(1<<(shift-1) if shift else 0)
        if all(abs(m)<(1<<30) for m in mult) and bound<(1<<31):return mult,shift
    raise CompileError('CPU fixed-point rescaling cannot fit INT32')

def rescale(value,mult,shift):
    v=np.asarray(value,dtype=np.int64)*mult
    if shift:v=(v+(1<<(shift-1)))>>shift
    return np.clip(v,-128,127).astype(np.int8)

class Memory:
    def __init__(self):self.top=DATA_TOP;self.image=bytearray(SRAM_BYTES);self.allocations=[]
    def alloc(self,name,size,data=None,alignment=4):
        if alignment<4 or alignment&(alignment-1):raise CompileError('Invalid allocation alignment')
        self.top=(self.top-size)&-alignment
        if self.top<0:raise CompileError('Data exceed 8KiB SRAM')
        if data is not None:
            if len(data)!=size:raise CompileError('Internal allocation size mismatch')
            self.image[self.top:self.top+size]=data
        address=BASE+self.top
        self.allocations.append(dict(name=name,address=address,bytes=size))
        return address

class Package:
    def __init__(self,graph,nodes,memory,program,metadata):
        self.graph,self.nodes,self.memory,self.program,self.metadata=graph,nodes,memory,program,metadata
    def reference(self,x):
        ts=self.graph['tensors'];vals={self.graph['input']:quantize(x,ts[self.graph['input']]['scale'])}
        for node in self.nodes:
            op=node['op'];args=[vals[n].astype(np.int64) for n in node['inputs']]
            if op=='linear':
                value=args[0]@node['qweight'].T.astype(np.int64)+node['qbias']
                out=rescale(value,node['mult'][0],node['shift'])
            elif op in ('sigmoid','tanh'):out=node['lut'][args[0]+128]
            elif op=='softmax':
                ex=node['lut'][args[0]-args[0].max(axis=1,keepdims=True)+255].astype(np.int64)
                total=ex.sum(axis=1,keepdims=True)
                out=np.clip((ex*node['reciprocal']+total//2)//total,0,127).astype(np.int8)
            elif op in ('relu','relu6','leaky_relu','identity'):
                out=rescale(np.maximum(args[0],0) if op in ('relu','relu6') else args[0],node['mult'][0],node['shift'])
                if op=='relu6':out=np.minimum(out,node['clamp_max']).astype(np.int8)
                if op=='leaky_relu':out=np.where(args[0]<0,rescale(args[0],node['negative_mult'],node['negative_shift']),out).astype(np.int8)
            elif op=='mul':out=rescale(args[0]*(args[1] if len(args)>1 else 1),node['mult'][0],node['shift'])
            else:
                value=args[0]*node['mult'][0]+(args[1] if len(args)>1 else 1)*node['mult'][1]
                if node['shift']:value=(value+(1<<(node['shift']-1)))>>node['shift']
                out=np.clip(value,-128,127).astype(np.int8)
            vals[node['name']]=out
        return vals
    def write(self,directory,x):
        directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
        image=bytearray(self.memory.image)
        t=self.graph['tensors'][self.graph['input']]
        q=quantize(x,t['scale'])
        if list(q.shape)!=t['shape']:raise CompileError('Runtime input shape differs from compiled shape')
        for b,row in enumerate(q):
            at=t['address']-BASE+b*t['stride'];image[at:at+len(row)]=row.tobytes()
        words=struct.unpack('<2048I',image)
        (directory/'firmware.hex').write_text(''.join(f'{w:08x}\n' for w in words))
        (directory/'firmware.bin').write_bytes(image)
        (directory/'firmware.S').write_text('\n'.join(self.program.listing)+'\n')
        (directory/'manifest.json').write_text(json.dumps(self.metadata,indent=2)+'\n')
        if self.metadata.get('task_abi'):
            from .tasks import write_plan
            write_plan(directory,self.metadata)
        vals=self.reference(x)
        (directory/'reference.json').write_text(json.dumps({n:v.tolist() for n,v in vals.items()},indent=2)+'\n')
        return vals

class Codegen:
    def __init__(self,memory,tensors):
        self.m=memory;self.ts=tensors;self.a=Program();self.profile_events=[]
        self.profile_scope=('startup','runtime');self.mark(*self.profile_scope)
        self.a.li(30,-128);self.a.li(31,127)
    def mark(self,phase,node):
        """Metadata only: never emit instructions or change label addresses."""
        self.profile_scope=(phase,node)
        self.profile_events.append(dict(start_pc=BASE+4*len(self.a.words),phase=phase,node=node))
    def put(self,offset,value):
        self.a.li(5,value);self.a.li(6,0x70000000+offset);self.a.sw(5,6)
    def quant(self,node,already_scaled=False):
        previous=self.profile_scope;self.mark('cpu_quant',node['name'])
        a=self.a
        if not already_scaled:a.mul(10,10,17)
        if node['shift']:a.add(10,10,18);a.srai(10,10,node['shift'])
        low=a.fresh('clip_low');high=a.fresh('clip_high')
        a.branch('bge',10,30,low);a.addi(10,30,0);a.label(low)
        a.branch('bge',31,10,high);a.addi(10,31,0);a.label(high)
        self.mark(*previous)
    def setup_quant(self,node):
        self.a.li(17,node['mult'][0]);self.a.li(18,(1<<(node['shift']-1)) if node['shift'] else 0)
    def linear_npu(self,node):
        a=self.a;src=self.ts[node['inputs'][0]];dst=self.ts[node['name']]
        for job in node['jobs']:
            self.mark('cpu_schedule',node['name'])
            self.put(0,2);self.put(0x3c,3 if job['accumulate'] else 1)
            self.put(0x80,job['k']);self.put(0x84,job['n']);self.put(0x18,job['batch']);self.put(0x20,job['source'])
            self.mark('cpu_input_copy',node['name'])
            for b in range(job['batch']):
                a.li(5,src['address']+b*src['stride']+job['input_offset'])
                a.li(6,0x70000000+[0x40,0xc00,0x1000,0x1040][b]);a.li(7,(job['k']+3)//4)
                loop=a.fresh('load_input');a.label(loop);a.lw(8,5);a.sw(8,6)
                a.addi(5,5,4);a.addi(6,6,4);a.addi(7,7,-1);a.branch('bne',7,0,loop)
            if not job['accumulate']:
                self.mark('cpu_bias_copy',node['name'])
                a.li(5,node['bias_address']+job['output_offset']*4);a.li(6,0x700009c0);a.li(7,job['n'])
                loop=a.fresh('load_bias');a.label(loop);a.lw(8,5);a.sw(8,6)
                a.addi(5,5,4);a.addi(6,6,4);a.addi(7,7,-1);a.branch('bne',7,0,loop)
            self.mark('cpu_launch',node['name']);self.put(0,1)
            self.mark('cpu_poll',node['name']);a.li(6,0x70000004);a.li(7,20000)
            loop=a.fresh('wait_npu');finished=a.fresh('npu_finished');a.label(loop)
            a.lw(8,6);a.li(9,1);a.branch('beq',8,9,finished)
            a.andi(9,8,4);a.branch('bne',9,0,'fail');a.addi(7,7,-1);a.branch('bne',7,0,loop);a.jump('fail');a.label(finished)
            if job['last_input']:
                self.mark('cpu_result_copy',node['name'])
                self.setup_quant(node)
                for b in range(job['batch']):
                    a.li(5,0x70001400+b*128);a.li(6,dst['address']+b*dst['stride']+job['output_offset']);a.li(7,job['n'])
                    loop=a.fresh('read_npu');a.label(loop);a.lw(10,5);self.quant(node);a.sb(10,6)
                    a.addi(5,5,4);a.addi(6,6,1);a.addi(7,7,-1);a.branch('bne',7,0,loop)
    def linear_cpu(self,node):
        self.mark('cpu_fc',node['name'])
        a=self.a;src=self.ts[node['inputs'][0]];dst=self.ts[node['name']];b,k=src['shape'];n=dst['shape'][1]
        self.setup_quant(node)
        for sample in range(b):
            a.li(12,node['weight_address']);a.li(13,node['bias_address']);a.li(6,dst['address']+sample*dst['stride']);a.li(14,n)
            outer=a.fresh('cpu_fc_out');inner=a.fresh('cpu_fc_dot');a.label(outer);a.lw(10,13)
            a.li(5,src['address']+sample*src['stride']);a.li(7,k);a.label(inner)
            a.lb(8,5);a.lb(9,12);a.mul(8,8,9);a.add(10,10,8)
            a.addi(5,5,1);a.addi(12,12,1);a.addi(7,7,-1);a.branch('bne',7,0,inner)
            self.quant(node);a.sb(10,6);a.addi(6,6,1);a.addi(13,13,4);a.addi(14,14,-1);a.branch('bne',14,0,outer)
    def task_segment(self,segment):
        self.mark('cpu_schedule',segment['nodes'][0]);a=self.a
        a.li(6,0x70001610);a.lw(8,6);a.srai(8,8,24);a.li(9,1);a.branch('bne',8,9,'fail')
        self.put(0x1600,2);self.put(0x1608,segment['address']);self.put(0x160c,segment['count'])
        a.emit(0x0ff0000f,'fence iorw, iorw')
        self.mark('cpu_launch',segment['nodes'][0]);self.put(0x1600,1)
        self.mark('cpu_poll',segment['nodes'][0]);a.li(6,0x70001604);a.li(7,200000)
        loop=a.fresh('wait_segment');finished=a.fresh('segment_done');a.label(loop)
        a.lw(8,6);a.li(9,9);a.branch('beq',8,9,finished)
        a.andi(9,8,20);a.branch('bne',9,0,'fail');a.addi(7,7,-1)
        a.branch('bne',7,0,loop);a.jump('fail');a.label(finished)
        a.emit(0x0ff0000f,'fence iorw, iorw')
    def special_segment(self,segment,nodes):
        first,last=nodes[segment['nodes'][0]],nodes[segment['nodes'][-1]]
        self.mark('cpu_schedule',first['name']);a=self.a;src=self.ts[first['inputs'][0]];dst=self.ts[last['name']]
        for offset,value in [(0,2),(0x3c,0),(0x18,segment['batch']),(0x20,segment['weight1']),
                             (0x24,segment['weight2']),(0x10,segment['multiplier']),(0x14,segment['shift'])]:self.put(offset,value)
        self.mark('cpu_input_copy',first['name'])
        for b in range(segment['batch']):
            a.li(5,src['address']+b*src['stride']);a.li(6,0x70000000+[0x40,0xc00,0x1000,0x1040][b]);a.li(7,16)
            loop=a.fresh('special_input');a.label(loop);a.lw(8,5);a.sw(8,6)
            a.addi(5,5,4);a.addi(6,6,4);a.addi(7,7,-1);a.branch('bne',7,0,loop)
        self.mark('cpu_bias_copy',first['name'])
        for node,offset,n in [(first,0x9c0,32),(last,0xa40,6)]:
            a.li(5,node['bias_address']);a.li(6,0x70000000+offset);a.li(7,n)
            loop=a.fresh('special_bias');a.label(loop);a.lw(8,5);a.sw(8,6)
            a.addi(5,5,4);a.addi(6,6,4);a.addi(7,7,-1);a.branch('bne',7,0,loop)
        self.mark('cpu_launch',first['name']);self.put(0,1)
        self.mark('cpu_poll',first['name']);a.li(6,0x70000004);a.li(7,20000)
        loop=a.fresh('special_wait');finished=a.fresh('special_done');a.label(loop)
        a.lw(8,6);a.li(9,1);a.branch('beq',8,9,finished);a.andi(9,8,4);a.branch('bne',9,0,'fail')
        a.addi(7,7,-1);a.branch('bne',7,0,loop);a.jump('fail');a.label(finished)
        self.mark('cpu_result_copy',last['name']);self.setup_quant(last)
        for b in range(segment['batch']):
            a.li(5,0x70000000+[0xb00,0xc80,0x1220,0x1260][b]);a.li(6,dst['address']+b*dst['stride']);a.li(7,6)
            loop=a.fresh('special_scores');a.label(loop);a.lw(10,5);self.quant(last);a.sb(10,6)
            a.addi(5,5,4);a.addi(6,6,1);a.addi(7,7,-1);a.branch('bne',7,0,loop)
    def softmax(self,node):
        self.mark('cpu_activation',node['name'])
        a=self.a;src=self.ts[node['inputs'][0]];dst=self.ts[node['name']];batch,n=dst['shape']
        a.li(17,node['lut_address']);a.li(19,node['reciprocal'])
        for sample in range(batch):
            start=src['address']+sample*src['stride']
            a.li(5,start);a.li(7,n);a.li(14,-128)
            loop=a.fresh('softmax_max');skip=a.fresh('keep_max');a.label(loop);a.lb(10,5)
            a.branch('bge',14,10,skip);a.addi(14,10,0);a.label(skip)
            a.addi(5,5,1);a.addi(7,7,-1);a.branch('bne',7,0,loop)
            a.li(5,start);a.li(7,n);a.li(15,0)
            loop=a.fresh('softmax_sum');a.label(loop);a.lb(10,5);a.sub(10,10,14);a.addi(10,10,255)
            a.slli(10,10,1);a.add(10,10,17);a.lhu(10,10);a.add(15,15,10)
            a.addi(5,5,1);a.addi(7,7,-1);a.branch('bne',7,0,loop)
            a.li(5,start);a.li(6,dst['address']+sample*dst['stride']);a.li(7,n)
            a.srai(18,15,1);loop=a.fresh('softmax_normalize');clip=a.fresh('softmax_clip');a.label(loop)
            a.lb(10,5);a.sub(10,10,14);a.addi(10,10,255);a.slli(10,10,1);a.add(10,10,17);a.lhu(10,10)
            a.mul(10,10,19);a.add(10,10,18);a.divu(10,10,15)
            a.branch('bge',31,10,clip);a.addi(10,31,0);a.label(clip);a.sb(10,6)
            a.addi(5,5,1);a.addi(6,6,1);a.addi(7,7,-1);a.branch('bne',7,0,loop)
    def elementwise(self,node):
        self.mark('cpu_activation' if node['op'] in ('relu','relu6','leaky_relu','sigmoid','tanh') else 'cpu_elementwise',node['name'])
        a=self.a;src=self.ts[node['inputs'][0]];dst=self.ts[node['name']];b,n=dst['shape'];op=node['op']
        if op not in ('sigmoid','tanh'):self.setup_quant(node)
        else:a.li(17,node['lut_address'])
        if op in ('add','sub'):a.li(19,node['mult'][1])
        if op=='relu6':a.li(19,node['clamp_max'])
        if op=='leaky_relu':
            a.li(19,node['negative_mult']);a.li(20,(1<<(node['negative_shift']-1)) if node['negative_shift'] else 0)
        for sample in range(b):
            a.li(5,src['address']+sample*src['stride']);a.li(6,dst['address']+sample*dst['stride']);a.li(7,n)
            if len(node['inputs'])==2:
                other=self.ts[node['inputs'][1]];a.li(12,other['address']+sample*other['stride'])
            loop=a.fresh('cpu_'+op);a.label(loop);a.lb(10,5)
            if op in ('relu','relu6'):
                label=a.fresh('relu');a.branch('bge',10,0,label);a.addi(10,0,0);a.label(label)
            if op in ('sigmoid','tanh'):
                a.addi(10,10,128);a.add(10,10,17);a.lb(10,10)
            else:
                if op in ('add','sub','mul') and len(node['inputs'])==2:
                    a.lb(11,12);a.addi(12,12,1)
                    if op=='mul':a.mul(10,10,11)
                    else:a.mul(10,10,17);a.mul(11,11,19);a.add(10,10,11)
                if op in ('add','sub') and len(node['inputs'])==1:a.mul(10,10,17);a.add(10,10,19)
                if op=='leaky_relu':
                    positive=a.fresh('leaky_positive');finished=a.fresh('leaky_finished')
                    a.branch('bge',10,0,positive);a.mul(10,10,19)
                    if node['negative_shift']:a.add(10,10,20);a.srai(10,10,node['negative_shift'])
                    self.quant(dict(node,shift=0),already_scaled=True);a.jump(finished)
                    a.label(positive);self.quant(node);a.label(finished)
                else:self.quant(node,already_scaled=op in ('add','sub'))
                if op=='relu6':
                    clipped=a.fresh('relu6_cap');a.branch('bge',19,10,clipped);a.addi(10,19,0);a.label(clipped)
            a.sb(10,6);a.addi(5,5,1);a.addi(6,6,1);a.addi(7,7,-1);a.branch('bne',7,0,loop)
    def finish(self):
        self.mark('finish','runtime')
        a=self.a;a.li(5,0xc0dec0de);a.jump('finish');a.label('fail');a.li(5,0xdeadbeef)
        a.label('finish');a.li(6,0x80001fe0);a.sw(5,6);a.label('halt');a.jump('halt');a.resolve()
        code=struct.pack('<%dI'%len(a.words),*a.words)
        if len(code)>self.m.top:raise CompileError(f'Code/data overlap: code={len(code)}B, available={self.m.top}B; SRAM total=8192B')
        self.m.image[:len(code)]=code
        return a

def compile_model(model,example_input,calibration_inputs=None,force_cpu=False,*,task_engine=False,forward=True,fuse=True,specialize=True,lut_cache=False):
    if lut_cache and not task_engine:raise CompileError('LUT cache requires task-engine target')
    graph=capture(model,example_input,calibration_inputs);mem=Memory();ts=graph['tensors'];nodes=graph['nodes']
    for name,t in ts.items():
        b,n=t['shape'];t['stride']=(n+3)//4*4;t['address']=mem.alloc('tensor:'+name,b*t['stride'])
    for node in nodes:
        op=node['op'];src=[ts[n] for n in node['inputs']];out=ts[node['name']];node['backend']='CPU';node['reason']='CPU operator kernel'
        if op=='linear':
            w=node.pop('weight');bias=node.pop('bias');sw=max(float(np.abs(w).max())/127,1e-12)
            qw=np.clip(np.rint(w/sw),-127,127).astype(np.int8)
            qb64=np.rint(bias/(src[0]['scale']*sw))
            if not np.isfinite(qb64).all() or np.abs(qb64).max()>=(1<<31):raise CompileError(f"{node['name']}: bias cannot fit INT32")
            qb=qb64.astype(np.int32);lo=qb.astype(np.int64)+np.minimum(-128*qw.astype(np.int64),127*qw.astype(np.int64)).sum(axis=1)
            hi=qb.astype(np.int64)+np.maximum(-128*qw.astype(np.int64),127*qw.astype(np.int64)).sum(axis=1)
            bound=int(max(np.abs(lo).max(),np.abs(hi).max()))
            if bound>=(1<<31):raise CompileError(f"{node['name']}: CPU accumulation may overflow INT32")
            node.update(qweight=qw,qbias=qb)
            node['mult'],node['shift']=coefficients([src[0]['scale']*sw/out['scale']],[bound])
            node['bias_address']=mem.alloc(node['name']+':bias',qb.nbytes,qb.astype('<i4').tobytes())
            tiny=task_engine and src[0]['shape'][0]*src[0]['shape'][1]*out['shape'][1]<=1
            if not force_cpu and not tiny and lo.min()>=-(1<<21) and hi.max()<(1<<21):
                b,k=src[0]['shape'];jobs,image=plan_fc([[0]*k for _ in range(b)],qw.tolist(),qb.tolist())
                addr=mem.alloc(node['name']+':weights',len(image),image)
                for job in jobs:
                    job['source']+=addr-BASE
                    # plan_fc orders all K segments within each output block.
                    job['input_offset']=0 if not job['accumulate'] else input_offset
                    input_offset=job['input_offset']+job['k']
                    job['last_input']=input_offset==k
                    del job['inputs'];del job['bias']
                node.update(backend='NPU',reason='INT8 operands; full input-domain accumulation fits INT22',jobs=jobs)
            else:
                node['weight_address']=mem.alloc(node['name']+':weights',qw.nbytes,qw.tobytes())
                node['reason']='Forced CPU backend' if force_cpu else 'Measured tiny-FC launch overhead exceeds CPU work' if tiny else 'Accumulation exceeds NPU INT22 range'
        elif op=='softmax':
            reciprocal=int(round(1/out['scale']))
            maximum=min(32767,((1<<31)-1)//max(1,reciprocal+out['shape'][1]))
            if maximum<1:raise CompileError('Softmax scale is too small for INT32 normalization')
            lut=np.rint(np.exp(np.arange(-255,1)*src[0]['scale'])*maximum).astype('<u2')
            node.update(lut=lut,reciprocal=reciprocal,lut_address=mem.alloc(node['name']+':exp_lut',512,lut.tobytes()))
        elif op in ('sigmoid','tanh'):
            vals=np.arange(-128,128,dtype=np.float64)*src[0]['scale']
            fn=(lambda x:1/(1+np.exp(-np.clip(x,-700,700)))) if op=='sigmoid' else np.tanh
            node['lut']=quantize(fn(vals),out['scale']);node['lut_address']=mem.alloc(node['name']+':lut',256,node['lut'].tobytes())
        else:
            if op in ('add','sub'):
                if 'scalar' in node:
                    ratios=[src[0]['scale']/out['scale']*(-1 if op=='sub' and node['scalar_left'] else 1),
                            node['scalar']/out['scale']*(-1 if op=='sub' and not node['scalar_left'] else 1)];bounds=[128,1]
                else:ratios=[src[0]['scale']/out['scale'],src[1]['scale']/out['scale']*(1 if op=='add' else -1)];bounds=[128,128]
            else:
                ratios=[src[0]['scale']*((node['scalar'] if 'scalar' in node else src[1]['scale']) if op=='mul' else 1)/out['scale']];bounds=[16384 if op=='mul' and 'scalar' not in node else 128]
            node['mult'],node['shift']=coefficients(ratios,bounds)
            if op=='relu6':node['clamp_max']=min(127,max(0,int(round(6/out['scale']))))
            if op=='leaky_relu':
                m,s=coefficients([src[0]['scale']*node['negative_slope']/out['scale']],[128])
                node.update(negative_mult=m[0],negative_shift=s)
    segments=[];specials=[]
    if task_engine and not force_cpu:
        from .tasks import plan_segments,select_special_segments
        if specialize:specials=select_special_segments(nodes,ts,mem,graph['output'])
        segments=plan_segments(nodes,ts,mem,graph['output'],forward=forward,fuse=fuse,lut_cache=lut_cache)
    gen=Codegen(mem,ts);emitted=set();special_emitted=set();by_name={n['name']:n for n in nodes}
    for node in nodes:
        node['start_pc']=BASE+len(gen.a.words)*4
        if 'special_segment' in node:
            if node['special_segment'] not in special_emitted:
                gen.special_segment(specials[node['special_segment']],by_name);special_emitted.add(node['special_segment'])
        elif 'segment' in node:
            if node['segment'] not in emitted:
                gen.task_segment(segments[node['segment']]);emitted.add(node['segment'])
        elif node['op']=='linear':getattr(gen,'linear_'+node['backend'].lower())(node)
        elif node['op']=='softmax':gen.softmax(node)
        else:gen.elementwise(node)
        node['end_pc']=BASE+len(gen.a.words)*4
    program=gen.finish()
    report_nodes=[{k:v for k,v in n.items() if k not in ('qweight','qbias','lut')} for n in nodes]
    ranges=[]
    events=gen.profile_events+[dict(start_pc=BASE+len(program.words)*4)]
    for first,last in zip(events,events[1:]):
        if first['start_pc']<last['start_pc']:ranges.append(dict(first,end_pc=last['start_pc']))
    meta=dict(abi=1,input=graph['input'],output=graph['output'],tensors=ts,nodes=report_nodes,profile_ranges=ranges,
              task_abi=1 if task_engine else None,task_segments=segments,special_segments=specials,
              rtl_parameters={'TASK_LUT_WORD_CACHE':1} if lut_cache else {},
              npu_core_starts=sum(s['fc_jobs'] for s in segments)+len(specials)+sum(len(n.get('jobs',[])) for n in nodes if n['backend']=='NPU' and 'segment' not in n),
              quantization='Symmetric per-tensor INT8; per-layer INT8 weights; rounded fixed-point CPU boundaries',
              input_shape=ts[graph['input']]['shape'],code_bytes=len(program.words)*4,data_bytes=DATA_TOP-mem.top,
              free_bytes=mem.top-len(program.words)*4,allocations=mem.allocations,
              code_sha256=hashlib.sha256(bytes(mem.image[:len(program.words)*4])).hexdigest())
    return Package(graph,nodes,mem,program,meta)
