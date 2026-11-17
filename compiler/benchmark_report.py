"""Freeze same-integer-contract task benchmarks, with cycle and traffic tables."""
import argparse,gzip,hashlib,json,re,shutil
from pathlib import Path


FILES=['firmware.bin','firmware.hex','firmware.S','manifest.json','reference.json','actual_output.json',
       'actual_tensors.hex','profile.json','task_validation.json','special_validation.json',
       'task_trace.csv','special_trace.csv','task_plan.json','task_plan.md']


def read(p):return json.loads(p.read_text())


def freeze(source,target):
    target.mkdir(parents=True)
    for name in FILES:
        p=source/name
        if p.is_file():shutil.copyfile(p,target/name)
    for name in ['soc.log','profile.csv']:
        p=source/name
        if p.is_file():(target/(name+'.gz')).write_bytes(gzip.compress(p.read_bytes(),mtime=0))


def category(exclusive):
    names={
        'FC MAC ISSUE':['npu_issue'],
        'Weight unready':['npu_wait_weight'],
        'Weight ready control':['npu_tile_ready_control'],
        'Task descriptor/input/bias/output DMA':['task_descriptor_dma','task_input_dma','task_bias_dma','task_output_dma'],
        'Task quant/activation/LUT/packing':['task_post_select','task_fc_rescale','task_activation_prepare','task_activation_rescale','task_lut_dma','task_pack_store'],
        'Internal handoff':['task_internal_copy'],
        'Task control':['task_validate','task_fc_setup','task_fc_control','task_commit','task_error_drain'],
        'CPU input/bias/result copies':['cpu_input_copy','cpu_bias_copy','cpu_result_copy'],
        'CPU schedule/launch/poll tail':['cpu_schedule','cpu_launch','cpu_poll'],
        'CPU quantization loop':['cpu_quant'],
        'CPU activation':['cpu_activation'],
        'CPU elementwise':['cpu_elementwise'],
        'CPU FC fallback':['cpu_fc'],
        'Legacy quant/drain/argmax':['npu_quant','npu_quant_drain','npu_finish_argmax']}
    result={label:sum(exclusive.get(k,0) for k in keys) for label,keys in names.items()}
    used={k for keys in names.values() for k in keys}
    result['Boot/finish/other']=sum(v for k,v in exclusive.items() if k not in used)
    assert sum(result.values())==sum(exclusive.values())
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['baseline','models','micro','expanded','output']:p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args()
    if a.output.exists():raise ValueError('Freeze into a new output directory')
    a.output.mkdir(parents=True)
    old=read(a.baseline/'summary.json');previous={(r['group'],r['name']):r for r in old['records']}
    model_result=read(a.models/'result.json');micro_result=read(a.micro/'result.json');expanded=read(a.expanded/'result.json')
    assert all(r['passed'] for r in [model_result,micro_result,expanded])
    assert model_result['soc'] and expanded['soc']
    records=[]
    for c in model_result['cases']:
        name=c['name'];source=a.models/name;base=a.baseline/'baseline'/('models_'+name)
        assert read(source/'reference.json')==read(base/'reference.json'),name
        profile=read(source/'profile.json');before=previous['models',name]
        assert profile['observed_edges']==sum(profile['exclusive_wall_cycles'].values())
        manifest=read(source/'manifest.json')
        records.append(dict(group='models',name=name,baseline_cycles=before['observed_cycles'],cycles=c['observed_cycles'],
            change_percent=100*(c['observed_cycles']/before['observed_cycles']-1),
            baseline_fc_starts=before['jobs'],fc_starts=manifest['npu_core_starts'],
            cpu_segment_starts=len(manifest['task_segments'])+len(manifest['special_segments']),
            descriptors=sum(s['count'] for s in manifest['task_segments']),
            before=before,after=profile,before_categories=category(before['exclusive_wall_cycles']),
            after_categories=category(profile['exclusive_wall_cycles'])))
        freeze(source,a.output/'frozen'/'models'/name)
    for c in micro_result['cases']:
        backend=c['backend'];name=c['name'];source=a.micro/(name+'_'+backend)
        before=previous['micro',name+('_cpu' if backend=='cpu' else '_npu')]
        base=a.baseline/'baseline'/('micro_'+name+('_cpu' if backend=='cpu' else '_npu'))
        assert read(source/'reference.json')==read(base/'reference.json'),name
        records.append(dict(group='micro',name=name,requested=backend,actual_backend=c['actual_backend'],
            baseline_cycles=before['observed_cycles'],cycles=c['cycles'],
            change_percent=100*(c['cycles']/before['observed_cycles']-1),after=c['profile']))
        freeze(source,a.output/'frozen'/'micro'/(name+'_'+backend))
    for fixture in micro_result['fixtures']:
        name=fixture['name']+'.npz'
        assert (a.micro/'fixtures'/name).read_bytes()==(a.baseline/'baseline/micro_fixtures'/name).read_bytes()
    shutil.copytree(a.micro/'fixtures',a.output/'frozen/micro_fixtures')
    for backend in ['auto','cpu']:
        control=a.micro/('k1_n1_b1_'+backend+'_control')
        if control.is_dir():freeze(control,a.output/'frozen/micro'/control.name)
    for case in expanded['cases']:
        freeze(a.expanded/case['name'],a.output/'frozen/expanded'/case['name'])
    for name in ['act_relu6_cpu','act_leaky_cpu']:
        freeze(a.expanded/name,a.output/'frozen/expanded'/name)
    for name,result in [('models',model_result),('micro',micro_result),('expanded',expanded)]:
        (a.output/(name+'_result.json')).write_text(json.dumps(result,indent=2)+'\n')
    lines=['# 同整数规则的功能性能冻结','',
        '以下为完整SoC RTL实际CPU运行，包含调度、取指、SRAM及DMA；没有减掉启动或CPU交接。',
        '每个原有模型和FC微基准的整数参考与阶段一完全一致，六个微基准的权重/输入/校准NPZ逐字节相同。',
        '物理时序、面积、SDF和Lab5需要另外验收，此表不代表物理完成。','',
        '| Model | Before cycles | After cycles | Change | FC starts before/after | CPU segments after | Descriptors |',
        '| --- | ---: | ---: | ---: | ---: | ---: | ---: |']
    for r in records:
        if r['group']=='models':lines.append(f"| {r['name']} | {r['baseline_cycles']} | {r['cycles']} | {r['change_percent']:+.2f}% | {r['baseline_fc_starts']}/{r['fc_starts']} | {r['cpu_segment_starts']} | {r['descriptors']} |")
    lines += ['', '## 周期分解','',
        '按每拍互斥分账：MAC核心忙时优先归其状态，其余任务忙时归任务状态，再归最近已接受CPU指令阶段。',
        '硬件计数比上述bench观察周期少5拍，二者时间边界沿用冻结基准；下表合计为硬件计数。',
        'CPU仍可能与NPU并行，此分账不是CPU停顿原因证明；AXI等待视图与此重叠，不能重复相加。','']
    for name in ['mixed0','trained_har0']:
        r=next(r for r in records if r['group']=='models' and r['name']==name)
        lines += [f'### {name}','','| Category | Before | After |','| --- | ---: | ---: |']
        for label in r['before_categories']:
            lines.append(f"| {label} | {r['before_categories'][label]} | {r['after_categories'][label]} |")
        lines.append('')
    lines += ['## 数据流量','',
        'CPU LSU有效字节与实际SRAM端口字节是两个层次，不相加。SRAM端口读包括指令和重复读，写按BE计数；',
        'DMA按两端分别列出，输出方向的R来自NPU而非主SRAM。描述符、输入、bias、LUT也是实际开销。','',
        '| Model | CPU SRAM R/W before | CPU SRAM R/W after | SRAM port R/W before | SRAM port R/W after | DMA SRAM R after | DMA NPU R after | DMA SRAM W effective after |',
        '| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |']
    for r in records:
        if r['group']!='models':continue
        bt=r['before']['traffic'];at=r['after']['traffic'];roles=r['after']['dma_role_traffic']
        pair=lambda t,prefix:f"{t.get(prefix+'read_bytes',0)}/{t.get(prefix+'write_bytes',0)}"
        sr=sum(v.get('read_bytes',0) for k,v in roles.items() if k!='output')
        nr=roles.get('output',{}).get('read_bytes',0);sw=roles.get('output',{}).get('write_effective_bytes',0)
        lines.append(f"| {r['name']} | {pair(bt,'sram_cpu_')} | {pair(at,'sram_cpu_')} | {pair(bt,'sram_port_')} | {pair(at,'sram_port_')} | {sr} | {nr} | {sw} |")
    lines += ['', '### DMA任务组成','',
        '| Model | Weights R | Descriptors R | Input R | Bias R | LUT R | Packed output R / effective W |',
        '| --- | ---: | ---: | ---: | ---: | ---: | ---: |']
    for r in records:
        if r['group']!='models':continue
        roles=r['after']['dma_role_traffic'];values=[roles.get(k,{}).get('read_bytes',0) for k in ['weight','descriptor','input','bias','lut']]
        output=roles.get('output',{})
        lines.append('| '+r['name']+' | '+' | '.join(str(v) for v in values)+f" | {output.get('read_bytes',0)}/{output.get('write_effective_bytes',0)} |")
    lines += ['', '### 逐张量交接','',
        '以下是SRAM命令覆盖每个逻辑张量的次数与字节。字节排除stride padding；一次字节load可能导致整个32位字重复读取。',
        '它同时覆盖CPU和DMA对该张量的SRAM访问；内部/融合张量的新值由被动整数trace验证。','']
    for name in ['mixed0','trained_har0']:
        r=next(r for r in records if r['group']=='models' and r['name']==name)
        lines += [f'#### {name}','','| Tensor | SRAM read commands before/after | SRAM write commands before/after | Covered R bytes before/after | Covered W bytes before/after |',
                  '| --- | ---: | ---: | ---: | ---: |']
        before={t['name']:t for t in r['before']['tensors']};after=r['after']['tensor_traffic']
        for tensor in sorted(set(before)|set(after)):
            b=before.get(tensor,{});n=after.get(tensor,{})
            values=[f"{b.get(k,0)}/{n.get(k,0)}" for k in ['macro_read_commands','macro_write_commands','macro_read_bytes','macro_write_bytes']]
            lines.append('| '+tensor+' | '+' | '.join(values)+' |')
        lines.append('')
    lines += ['## 小FC启动开销','', '| Shape | Requested / actual | Before | After | Change |','| --- | --- | ---: | ---: | ---: |']
    for r in records:
        if r['group']=='micro':lines.append(f"| {r['name']} | {r['requested']} / {r['actual_backend']} | {r['baseline_cycles']} | {r['cycles']} | {r['change_percent']:+.2f}% |")
    lines += ['', '1→1自动选CPU；微基准的无探针对照确认被动监控不改变该程序的周期/硬件计数。',
        '原专用四样本2700拍是另一个独立程序，不能用这些不同batch或INT8输出的网络代替其验收。','',
        '## 新覆盖模型','', '| Configuration | Cycles | CPU segments | Descriptors | MODE0 segments |','| --- | ---: | ---: | ---: | ---: |']
    for c in expanded['cases']:lines.append(f"| {c['name']} | {c['observed_cycles']} | {c['segments']} | {c['descriptors']} | {c['special_segments']} |")
    lines += ['', '大CPU回退模型256→20、batch4完整运行330899拍；代码、数据和权重仍在8KiB内。',
        '新激活的CPU参考内核和原软件MMIO对照不等同于声称旧编译器已经支持所有新算子。','']
    (a.output/'README.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    result=dict(status='functional_performance_frozen',baseline=str(a.baseline.resolve()),
        source_runs=dict(models=str(a.models.resolve()),micro=str(a.micro.resolve()),expanded=str(a.expanded.resolve())),records=records)
    (a.output/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
    manifest={p.relative_to(a.output).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in a.output.rglob('*') if p.is_file()}
    (a.output/'files_sha256.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print('TASK_BENCHMARK_FROZEN '+str(a.output))


if __name__=='__main__':main()
