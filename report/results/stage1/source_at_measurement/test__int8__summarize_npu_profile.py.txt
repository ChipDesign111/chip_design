"""Publish a byte-frozen baseline corpus and disjoint cycle/traffic tables."""
import argparse,gzip,hashlib,json,re,shutil,subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def write(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['compiled','micro','legacy','output']:p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    frozen=a.output/'baseline';frozen.mkdir();records=[]
    for group,run in [('models',a.compiled),('micro',a.micro),('legacy',a.legacy)]:
        run=run.resolve();result=read(run/'result.json');assert result['passed']
        case_dirs=([run] if group=='legacy' else [q.parent for q in sorted(run.glob('*/profile.json')) if not q.parent.name.endswith('_control')])
        for directory in case_dirs:
            name=directory.name if group!='legacy' else 'legacy_four_samples'
            profile=read(directory/'profile.json');text=(directory/'soc.log').read_text(errors='replace')
            match=re.search(r'INT8_SOC PASS cycles=(\d+) hw_soc_cycles=(\d+)',text);assert match
            observed,hardware=map(int,match.groups());assert profile['observed_edges']==hardware
            assert sum(profile['exclusive_wall_cycles'].values())==hardware
            dest=frozen/(group+'_'+name);dest.mkdir()
            names=['firmware.hex','manifest.json','profile.json','soc.log']
            if group!='legacy':names+=['firmware.bin','firmware.S','reference.json','actual_output.json','actual_tensors.hex']
            for n in names:shutil.copyfile(directory/n,dest/n)
            with (directory/'profile.csv').open('rb') as source,(dest/'profile.csv.gz').open('wb') as target:
                with gzip.GzipFile(filename='',mode='wb',fileobj=target,mtime=0) as compressed:
                    shutil.copyfileobj(source,compressed)
            names.append('profile.csv.gz')
            for tb in directory.glob('tb_*profile.sv'):
                shutil.copyfile(tb,dest/tb.name);names.append(tb.name)
            if (directory/'tb_compiled_model.sv').exists():
                shutil.copyfile(directory/'tb_compiled_model.sv',dest/'tb_compiled_model.sv');names.append('tb_compiled_model.sv')
            intermediate=[]
            meta=read(directory/'manifest.json')
            for t,traffic in profile['tensor_traffic'].items():
                intermediate.append(dict(name=t,role='input' if t==meta.get('input') else 'output' if t==meta.get('output') else 'intermediate',**traffic))
            records.append(dict(group=group,name=name,observed_cycles=observed,hardware_cycles=hardware,
                jobs=len(profile['jobs']),exclusive_wall_cycles=profile['exclusive_wall_cycles'],
                npu_states=profile['npu_state_cycles'],dma_handshakes=profile['dma_handshake_cycles'],
                node_phase_cycles=profile['cpu_node_stage_cycles'],traffic=profile['traffic'],tensors=intermediate,
                source_run=str(directory),raw_trace_sha256=sha(directory/'profile.csv'),
                artifact_SHA256={n:sha(dest/n) for n in names}))
        if group=='micro':
            shutil.copytree(run/'fixtures',frozen/'micro_fixtures')
    original=read(a.compiled/'result.json');baseline=Path(original['frozen_baseline'])
    baseline_cases={c['name']:c for c in read(baseline/'result.json')['cases']}
    for item in original['cases']:
        name=item['name'];assert (a.compiled/name/'firmware.hex').read_bytes()==(baseline/name/'firmware.hex').read_bytes()
        assert item['observed_cycles']==baseline_cases[name]['observed_cycles'],name
        assert read(a.compiled/name/'reference.json')==read(baseline/name/'reference.json'),name
    write(a.output/'summary.json',dict(status='stage1_passed; stages2_to7_pending',baseline_commit='94636cc',
        hardware_changes_since_baseline=subprocess.check_output(['git','diff','94636cc','--name-only','--','rtl'],cwd=ROOT,text=True).splitlines(),
        original_8_firmware_images_byte_identical=True,source_runs=dict(compiled=str(a.compiled.resolve()),micro=str(a.micro.resolve()),legacy=str(a.legacy.resolve())),
        source_result_SHA256={k:sha(v/'result.json') for k,v in [('compiled',a.compiled),('micro',a.micro),('legacy',a.legacy)]},
        analyzer_SHA256=sha(Path(__file__)),records=records))
    lines=['# 阶段一：冻结的通用路径周期与流量基准','',
        '状态：阶段一测量完成；阶段二至七尚未完成。基线94636cc，RTL未修改；8个原有编译模型的整个8KiB启动镜像与冻结版本逐字节一致。CPU/NPU结果均通过真实SoC逐层SBA读回核对。','',
        '周期表使用硬件统计窗口，原始testbench观测额外包含5拍；不得混用。每拍优先归入忙碌NPU状态，否则归入最近实际接受的CPU指令所属阶段。各列互斥且精确加总。CPU阶段包含该阶段的流水线、取指和数据等待，不是纯ALU计算周期；有效ID接受条件为id_valid && is_decoding，排除了推测/无效PC。','',
        '| 模型 | 硬件总周期 | ISSUE | 权重未就绪 | 就绪控制/其他NPU | CPU配置/启动 | CPU输入/bias/结果搬运 | CPU量化 | CPU激活 | CPU逐元素/点积 | 轮询尾部/其他 |',
        '| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |']
    for r in records:
        if r['group']!='models':continue
        x=r['exclusive_wall_cycles'];get=lambda *ks:sum(x.get(k,0) for k in ks)
        shown=[get('npu_issue'),get('npu_wait_weight'),sum(v for k,v in x.items() if k.startswith('npu_') and k not in ['npu_issue','npu_wait_weight']),get('cpu_schedule','cpu_launch'),get('cpu_input_copy','cpu_bias_copy','cpu_result_copy'),get('cpu_quant'),get('cpu_activation'),get('cpu_elementwise')+get('cpu_fc')]
        shown.append(r['hardware_cycles']-sum(shown))
        lines.append('| '+r['name']+' | '+str(r['hardware_cycles'])+' | '+' | '.join(map(str,shown))+' |')
    lines+=['','CPU阶段按最近一次被ID实际接收的指令PC划分，跨空泡保持，不按无效或推测PC计费。NPU忙时优先分给真实硬件状态；各项之和等于硬件计数。这是可复现的时间分账，不是逐条指令的微架构因果分析。激活/逐元素阶段含各自的访存和循环控制，不等于纯ALU计算时间。','',
        '权重未就绪不能全部解释为AXI数据等待；summary.json另列AR/AW/W背压、R数据未返回、B响应未返回，以及权重未就绪期间DMA忙/闲。DMA读和写是同一份权重的两个端点，不能相加当作两份SRAM权重读取。','',
        '| 模型 | DMA权重读字节 | CPU数据SRAM读/写字节 | 全部SRAM命令读/写字节 |',
        '| --- | ---: | ---: | ---: |']
    for r in records:
        if r['group']!='models':continue
        t=r['traffic'];lines.append(f"| {r['name']} | {t.get('dma_weight_read_bytes',0)} | {t.get('sram_cpu_read_bytes',0)}/{t.get('sram_cpu_write_bytes',0)} | {t.get('sram_port_read_bytes',0)}/{t.get('sram_port_write_bytes',0)} |")
    lines+=['','CPU字节数按实际LSU握手byte-enable统计；全部SRAM命令包括取指、DMA和重复读，读命令按完整32位计数。各层统计不能重复相加。逐张量读写次数、有效字节数及物理命令次数均在summary.json。测量排除镜像装载和程序完成后的SBA验值。','',
        '| K/N/batch | NPU总周期 | CPU总周期 | NPU相对CPU |','| --- | ---: | ---: | ---: |']
    for r in records:
        if r['group']!='micro' or not r['name'].endswith('_npu'):continue
        cpu=next(t for t in records if t['group']=='micro' and t['name']==r['name'][:-3]+'cpu')
        lines.append(f"| {r['name'][:-4]} | {r['observed_cycles']} | {cpu['observed_cycles']} | {r['observed_cycles']/cpu['observed_cycles']:.3f}倍 |")
    lines+=['','每组CPU/NPU使用相同权重、输入、校准及整数结果。1→1同时运行不带探针的对照，周期和全部原有计数一致。微基准模型参数/输入冻结在baseline/micro_fixtures；原有模型定义、权重和校准数据由基线提交及源码SHA固定。','',
        'baseline保存启动镜像、整数参考、实际输出、PC阶段清单、生成的bench、原始SoC日志和周期/流量记录；逐拍CSV使用gzip无损保存，压缩前/后SHA分别记录。没有将期望值嵌入CPU程序。','',
        '这些是RTL周期/流量测量，不是新的时序、面积或EDA验收。后续新硬件仍须完整重跑功能和TT EDA。']
    (a.output/'README.md').write_text('\n'.join(lines)+'\n',encoding='utf-8',newline='\n')
    print('PROFILE_SUMMARY_PASS '+str(a.output))


if __name__=='__main__':main()
