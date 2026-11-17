"""Static task segments, K/N tiling and conservative single-buffer liveness."""
from dataclasses import asdict,replace
import json
from .task_abi import Task,Op,Activation,validate_segment,rescale

ACTS={'identity':Activation.NONE,'relu':Activation.RELU,'relu6':Activation.RELU6,
      'leaky_relu':Activation.LEAKY_RELU,'sigmoid':Activation.SIGMOID,'tanh':Activation.TANH}


def select_special_segments(nodes,tensors,memory,output):
    """MODE0 requires the entire integer/layout contract, not shape alone."""
    users={name:[] for name in tensors}
    for node in nodes:
        for name in node['inputs']:users[name].append(node['name'])
    segments=[]
    for i in range(len(nodes)-2):
        first,act,last=nodes[i:i+3]
        if any('special_segment' in n for n in [first,act,last]):continue
        if not (first['op']=='linear' and first['backend']=='NPU' and act['op']=='relu' and
            last['op']=='linear' and last['backend']=='NPU' and
            act['inputs']==[first['name']] and last['inputs']==[act['name']] and
            users[first['name']]==[act['name']] and users[act['name']]==[last['name']] and
            first['name']!=output and act['name']!=output):continue
        if not (tensors[first['inputs'][0]]['shape'][1]==64 and tensors[first['name']]['shape'][1]==32 and
            tensors[last['name']]['shape'][1]==6 and len(first['jobs'])==len(last['jobs'])==1):continue
        if any(rescale(max(0,q),act['mult'][0],act['shift'])!=max(0,q) for q in range(-128,128)):continue
        m=first['mult'][0];s=first['shift']
        while s and m%2==0:m//=2;s-=1
        if not 0<=m<=65535 or not 0<=s<=31:continue
        if tensors[last['name']]['shape'][0]==1:
            first['specialization_note']='Integer/layout match, but single-sample task path is preferred by measured launch/copy cost'
            continue
        # FC1's generic tile order already matches MODE0. FC2 must be repacked
        # to eight input rows x six outputs per48B packet, with256B range padding.
        address=last['jobs'][0]['source'];payload=last['qweight'].T.copy().tobytes()+bytes(64)
        memory.image[address-0x80000000:address-0x80000000+256]=payload
        segment=dict(index=len(segments),nodes=[n['name'] for n in [first,act,last]],
            multiplier=m,shift=s,weight1=first['jobs'][0]['source'],weight2=address,
            batch=tensors[last['name']]['shape'][0],fc1=first['name'],hidden=act['name'],output=last['name'],
            proof='64/32/6, unbranched FC/ReLU/FC, full INT22 safety, exhaustive INT8 ReLU identity, exact UINT16 scale reduction, explicit W2 layout')
        for node in [first,act,last]:
            node['special_segment']=segment['index'];node['backend']='NPU_SPECIAL';node['reason']=segment['proof']
        tensors[first['name']]['storage']='special_fc';tensors[act['name']]['storage']='special_hidden'
        last['weight_layout']='MODE0 input-row-major6, four48B packets in256B allocation'
        segments.append(segment)
    return segments


def plan_segments(nodes,tensors,memory,output,*,forward=True,fuse=True,lut_cache=False):
    users={name:[] for name in tensors}
    producers={node['name']:node for node in nodes}
    for node in nodes:
        for name in node['inputs']:users[name].append(node['name'])
    def supported(node):
        if 'special_segment' in node:return False
        if node['op']=='linear':return node['backend']=='NPU'
        if node['op'] not in ACTS:return False
        source=producers.get(node['inputs'][0],{})
        # Keep tiny stand-alone operations on CPU; an eligible predecessor FC
        # can still fuse the activation without another hardware launch.
        return (tensors[node['name']]['shape'][0]*tensors[node['name']]['shape'][1]>4 or
                source.get('op')=='linear' and source.get('backend')=='NPU')
    groups=[];group=[]
    for node in nodes:
        if supported(node):group.append(node)
        else:
            if group:groups.append(group);group=[]
    if group:groups.append(group)
    segments=[]
    for group in groups:
        tasks=[];records=[];i=0
        while i<len(group):
            node=group[i];src=tensors[node['inputs'][0]];dst=tensors[node['name']]
            result=node;activation=None
            # Fusion retains the FC INT8 boundary; RTL trace observes both q
            # and activation output, including an elided intermediate tensor.
            if (fuse and node['op']=='linear' and i+1<len(group) and
                group[i+1]['op'] in ACTS and group[i+1]['inputs']==[node['name']] and
                users[node['name']]==[group[i+1]['name']] and node['name']!=output):
                activation=group[i+1];result=activation
                dst=tensors[result['name']];tensors[node['name']]['storage']='fused'
            after=i+2 if activation is not None else i+1
            next_node=group[after] if after<len(group) else None
            width=dst['shape'][1]
            keep=(forward and width<=32 and result['name']!=output and next_node is not None and
                  next_node['inputs']==[result['name']] and users[result['name']]==[next_node['name']] and
                  (next_node['op']!='linear' or len(next_node['jobs'])==1))
            internal=src.get('storage')=='internal'
            if keep:dst['storage']='internal'
            if node['op']=='linear':
                blocks=node['jobs']
            else:
                blocks=[dict(n=min(32,width-no),output_offset=no,last_input=True) for no in range(0,width,32)]
            for block in blocks:
                no=block['output_offset'];last=block['last_input'];act=activation or (node if node['op']!='linear' else None)
                act_mode=ACTS[act['op']] if act is not None and last else Activation.NONE
                act_mult=act['mult'][0] if act is not None and act['op'] not in ('sigmoid','tanh') else 1
                act_shift=act['shift'] if act is not None and act['op'] not in ('sigmoid','tanh') else 0
                kwargs=dict(activation=act_mode,n=block['n'],batch=dst['shape'][0],
                    source=0 if internal else src['address']+(block['input_offset'] if node['op']=='linear' else no),
                    destination=0 if keep or not last else dst['address']+no,
                    input_stride=0 if internal else src['stride'],output_stride=0 if keep or not last else dst['stride'],
                    last_k=last,input_internal=internal,keep_output=keep and last,end_segment=False,
                    act_multiplier=act_mult if last else 1,act_shift=act_shift if last else 0,
                    lut_address=act['lut_address'] if act_mode>=Activation.SIGMOID else 0,
                    lut_cache=lut_cache and act_mode>=Activation.SIGMOID,
                    clamp_max=act.get('clamp_max',127) if act is not None else 127,
                    negative_multiplier=act.get('negative_mult',1) if act is not None else 1,
                    negative_shift=act.get('negative_shift',0) if act is not None else 0)
                if node['op']=='linear':
                    kwargs.update(k=block['k'],weights=block['source'],
                        bias=0 if block['accumulate'] else node['bias_address']+no*4,
                        initialize=not block['accumulate'],fc_multiplier=node['mult'][0],fc_shift=node['shift'],
                        context=nodes.index(node)*65536+no)
                else:kwargs.update(op=Op.ACTIVATION,k=0,weights=0,bias=0,initialize=False,fc_multiplier=0)
                tasks.append(Task(**kwargs))
                records.append(dict(task=len(tasks)-1,fc_node=node['name'] if node['op']=='linear' else None,
                    output_node=result['name'] if last else None,output_offset=no,
                    descriptor=asdict(tasks[-1])))
            node['backend']='NPU';node['reason']='Autonomous task segment'
            if activation is not None:
                activation['backend']='NPU';activation['reason']='Fused activation, preserving FC INT8 boundary'
            i=after
        tasks[-1]=replace(tasks[-1],end_segment=True);records[-1]['descriptor']=asdict(tasks[-1])
        address=memory.alloc(f'task_segment:{len(segments)}',len(tasks)*64,b''.join(t.pack(allow_cache=lut_cache) for t in tasks),alignment=64)
        validate_segment(address,tasks,allow_cache=lut_cache)
        segment=dict(index=len(segments),address=address,count=len(tasks),nodes=[n['name'] for n in group],tasks=records,
                     fc_jobs=sum(t.op==Op.FC for t in tasks),internal_edges=[n['name'] for n in group if tensors[n['name']].get('storage')=='internal'])
        for node in group:node['segment']=segment['index']
        segments.append(segment)
    return segments


def write_plan(directory,metadata):
    execution=[];seen=set();lines=['# SoC execution plan','',
        'INT8 zero-point0; exact rounding/saturation boundaries follow task ABI v1.',
        f"Code {metadata['code_bytes']}B; remaining SRAM {metadata['free_bytes']}B.",'']
    for node in metadata['nodes']:
        if 'special_segment' in node:
            key=('MODE0',node['special_segment'])
            if key in seen:continue
            seen.add(key);segment=metadata['special_segments'][key[1]]
            execution.append(dict(backend='MODE0',**segment))
            lines += [f"MODE0: {' -> '.join(segment['nodes'])}",'',segment['proof'],'']
        elif 'segment' in node:
            key=('TASK',node['segment'])
            if key in seen:continue
            seen.add(key);segment=metadata['task_segments'][key[1]]
            execution.append(dict(backend='TASK',**segment))
            lines += [f"Task segment {segment['index']}: base 0x{segment['address']:08x}, COUNT={segment['count']}",'',
                '| Task | OP | K/N/B | Input | Weights | Output | ACT | INIT/LAST/KEEP | Context |',
                '| --- | --- | --- | --- | --- | --- | --- | --- | --- |']
            for record in segment['tasks']:
                d=record['descriptor'];source='internal' if d['input_internal'] else f"0x{d['source']:08x}"
                destination='internal' if d['keep_output'] else f"0x{d['destination']:08x}"
                lines.append(f"| {record['task']} | {Op(d['op']).name} | {d['k']}/{d['n']}/{d['batch']} | {source} | 0x{d['weights']:08x} | {destination} | {Activation(d['activation']).name} | {int(d['initialize'])}/{int(d['last_k'])}/{int(d['keep_output'])} | {d['context']} |")
            lines.append('')
        else:
            execution.append(dict(backend='CPU',node=node['name'],op=node['op'],reason=node['reason']))
            lines += [f"CPU: {node['name']} ({node['op']}); {node['reason']}",'']
    (directory/'task_plan.json').write_text(json.dumps(dict(abi=1,execution=execution,tensors=metadata['tensors']),indent=2)+'\n')
    (directory/'task_plan.md').write_text('\n'.join(lines)+'\n')
