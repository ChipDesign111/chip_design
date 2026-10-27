#!/usr/bin/env python3
"""Fresh isolated gate/SDF simulation of an existing completed EDA version."""
import argparse
from datetime import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import shlex
import subprocess
import sys
import tarfile
import remote

ROOT=Path(__file__).resolve().parents[1]
DIST=ROOT/'eda/dist'

def html_page(markdown):
    spec=importlib.util.spec_from_file_location('postsim_renderer',ROOT/'eda/server/tools/workspace.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return '<!doctype html><meta charset="utf-8"><title>SDF后仿</title><style>body{font-family:sans-serif;max-width:1100px;margin:32px auto;padding:24px;line-height:1.8}table{border-collapse:collapse}td{border:1px solid #ccd;padding:8px}pre{white-space:pre-wrap;overflow-wrap:anywhere}p,code{overflow-wrap:anywhere}</style>'+module.render_markdown(markdown)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['run','status','fetch','timing'])
    parser.add_argument('--host',default='chipdesign')
    parser.add_argument('--eda-upload',help='Completed physical upload; defaults to last_upload.json')
    parser.add_argument('--output',type=Path)
    parser.add_argument('--simulator',choices=['vcs','xcelium'],default='vcs')
    parser.add_argument('--upload',help='An existing isolated post-simulation upload for status/fetch/timing')
    parser.add_argument('--sdf-mode',choices=['tt','pvt-min','pvt-max'],default='tt')
    args=parser.parse_args()
    if args.command=='run':
        eda=remote.valid_upload(args.eda_upload or json.loads((DIST/'last_upload.json').read_text())['upload'])
        if not remote.status(args.host,eda)['ready']:raise ValueError('Physical EDA must be complete')
        sys.path.insert(0,str(ROOT/'test/int8'))
        from firmware import build
        firmware=DIST/('postsim_firmware_'+datetime.now().strftime('%Y%m%d_%H%M%S'));firmware.mkdir(parents=True)
        for seed in [10000]+list(range(10001,10012))+[1,3,5,7]:
            p=firmware/str(seed);p.mkdir();build(p,seed)
            name='firmware.hex' if seed==10000 else 'firmware_%d.hex'%seed
            (firmware/name).write_bytes((p/'firmware.hex').read_bytes())
        subprocess.run([sys.executable,str(ROOT/'eda/package_server.py')],cwd=ROOT,check=True)
        parent=str(Path(eda).parent).replace('\\','/')
        name=datetime.now().strftime('%Y%m%d_%H%M%S')+'_postsim_'+args.simulator+'_'+args.sdf_mode+'_'+subprocess.check_output(['git','rev-parse','--short','HEAD'],cwd=ROOT).decode().strip()
        upload=remote.valid_upload(parent+'/'+name)
        remote.ssh(args.host,'set -e\nmkdir '+shlex.quote(upload)+'\n')
        remote.scp(args.host,[DIST/'chip_design_eda.tar.gz',DIST/'chip_design_eda.tar.gz.sha256'],upload+'/')
        public=str(Path(parent).parent).replace('\\','/')
        remote.scp(args.host,[ROOT/'eda/unpack.sh'],public+'/unpack.sh')
        remote.ssh(args.host,'bash '+shlex.quote(public+'/unpack.sh')+' '+shlex.quote(upload)+'\n',capture=False)
        guide='# 本次是已完成版图的后仿运行\n\n物理输入：`'+eda+'`。后仿目录：`'+upload+'`。不重新运行34步，原work不修改。\n\n'+(ROOT/'eda/docs/后仿真操作指南.md').read_text(encoding='utf-8')
        ui=firmware/'gui';ui.mkdir();(ui/'README.md').write_text(guide,encoding='utf-8');(ui/'README.html').write_text(html_page(guide),encoding='utf-8')
        remote.scp(args.host,[ui/'README.md',ui/'README.html'],upload+'/')
        remote.scp(args.host,list(firmware.glob('firmware*.hex')),upload+'/configs/')
        remote.save(DIST/'last_postsim.json',{'host':args.host,'upload':upload,'eda_upload':eda,'simulator':args.simulator,'sdf_mode':args.sdf_mode})
        cmd='python3 -u deploy/server/postsim/run.py --eda-work '+shlex.quote(eda+'/work')+' --run-root '+shlex.quote(upload+'/postsim')+' --firmware '+shlex.quote(upload+'/configs/firmware.hex')+' --simulator '+args.simulator+' --sdf-mode '+args.sdf_mode
        print(remote.ssh(args.host,'set -e\nsource /etc/profile.d/eda.sh\ncd '+shlex.quote(upload)+'\nnohup '+cmd+' >logs/postsim.log 2>&1 < /dev/null &\necho $! >logs/postsim.pid\ncat logs/postsim.pid\n'))
        print('Postsim upload: '+upload);return
    state=json.loads((DIST/'last_postsim.json').read_text());upload=remote.valid_upload(args.upload or state['upload'])
    if args.command=='timing':
        # Run only after simulation, keeping heavy server tools sequential.
        eda=remote.valid_upload(state['eda_upload'])
        tool=ROOT/'eda/server/postsim/sram_timing.tcl'
        output=upload+'/postsim/sram_timing'
        remote.ssh(args.host,'set -e\ntest -f '+shlex.quote(upload+'/postsim/results.json')+'\ntest ! -e '+shlex.quote(output)+'\nmkdir '+shlex.quote(output)+'\n')
        remote.scp(args.host,[tool],output+'/')
        driver='set eda_work {'+eda+'/work}\nset timing_output {'+output+'}\nsource {'+output+'/sram_timing.tcl}\n'
        local=DIST/'sram_timing_driver.tcl';local.write_text(driver,encoding='utf-8')
        remote.scp(args.host,[local],output+'/driver.tcl')
        print(remote.ssh(args.host,'set -e\nsource /etc/profile.d/eda.sh\ncd '+shlex.quote(output)+'\ninnovus -batch -files driver.tcl -log timing >tool.log 2>&1\ngrep SRAM_PORT_TIMING_REPORTED_NO_ECO tool.log\n'))
        remote.save(DIST/'last_sram_timing.json',{'upload':upload,'eda_upload':eda,'output':output,'script_sha256':remote.digest(tool)})
        print('Read-only SRAM timing reports: '+output);return
    if args.command=='status':
        script='''source /etc/profile.d/eda.sh
python3 - <<'PY'
from pathlib import Path
import json
p=Path(UPLOAD)
q=p/'postsim/results.json'
pid=int((p/'logs/postsim.pid').read_text())
live=Path('/proc/%d/cmdline'%pid)
running=live.exists() and b'postsim/run.py' in live.read_bytes()
logs=list((p/'postsim').glob('*/simulation.log'))
count=sum('FUNCTIONAL_PASS' in f.read_text(errors='replace') for f in logs)
plan=p/'postsim/run_plan.json'
print(json.dumps({'upload':str(p),'running':running,'functional_passes':count,
 'expected_cases':len(json.loads(plan.read_text())) if plan.is_file() else 4+len(list((p/'configs').glob('firmware_*.hex'))),
 'complete':q.exists(),'results':json.loads(q.read_text()) if q.exists() else None,
 'last_log':(p/'logs/postsim.log').read_text(errors='replace')[-2000:]}))
PY
'''.replace('UPLOAD',repr(upload))
        print(remote.ssh(args.host,script));return
    output=args.output
    if output is None:raise ValueError('fetch requires an empty --output directory')
    if output.exists() and any(output.iterdir()):raise ValueError('Use an empty output directory')
    output.mkdir(parents=True,exist_ok=True)
    # Version the evaluator in generated analysis space, leaving frozen deploy
    # and original simulation inputs unchanged. The report records its SHA.
    evaluator=upload+'/postsim/analysis_tools'
    remote.ssh(args.host,'set -e\nmkdir -p '+shlex.quote(evaluator)+'\n')
    remote.scp(args.host,[ROOT/'eda/server/postsim/collect.py'],evaluator+'/')
    remote.ssh(args.host,'set -e\nsource /etc/profile.d/eda.sh\npython3 '+shlex.quote(evaluator+'/collect.py')+' '+shlex.quote(upload+'/postsim')+'\n',capture=False)
    remote.scp(args.host,[upload+'/postsim/review.tar.gz',upload+'/postsim/review_manifest.json'],output,download=True)
    manifest=json.loads((output/'review_manifest.json').read_text())
    if remote.digest(output/'review.tar.gz')!=manifest['archive_sha256']:raise ValueError('Archive SHA mismatch')
    with tarfile.open(output/'review.tar.gz','r:gz') as tar:
        for member in tar.getmembers():
            if not member.isfile() or member.name not in manifest['files']:raise ValueError('Unsafe member')
            p=(output/member.name).resolve();p.relative_to(output.resolve());data=tar.extractfile(member).read()
            if hashlib.sha256(data).hexdigest()!=manifest['files'][member.name]:raise ValueError('File SHA mismatch')
            p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
    audit=json.loads((output/'audit.json').read_text());results=json.loads((output/'results.json').read_text())
    md='# SDF完整SoC后仿结果\n\n服务器：`'+upload+'`。本包'+str(len(manifest['files']))+'个文件已核验SHA。\n\n功能通过 '+str(sum(v['functional_pass'] for v in results.values()))+'/'+str(len(results))+'；回标error '+str(audit['annotation_errors'])+'，缺失实例 '+str(audit['missing_instances'])+'，缺失检查 '+str(audit['unmatched_timing_checks'])+'。\n\n工作窗口检查：'+str(audit['active_window_dynamic_timing_clean'])+'。原始复位事件及负IOPATH截零限制仍须查看，不等于全程无违规。\n\n- [完整审核](audit.json)\n- [全部功能结果](results.json)\n- [输入身份](input_manifest.json)\n- [回标原文](build/sdf.log)\n- [SDF运行](sdf_max/simulation.log)\n- [无SDF功能对照](gate_zero/simulation.log)\n\n大网表、SDF、授权模型和编译数据库仅留服务器。本轮不宣称独立签核。\n'
    quality='正常后仿验收（功能、绑定、实际动态时序）：'+str(audit.get('normal_postsim_pass','旧审核未给出此字段'))+'。已定位工具/模型Warning保留说明，不要求所有Warning为零。\n\n绑定完整性：'+str(audit['binding_complete_for_instances_and_checks'])+'；负路径延时支持完整：'+str(audit.get('negative_path_delay_support_complete',False))+'。后者单独说明模型能力，不作为额外的零Warning门槛。\n\n'
    md=md.replace('# SDF完整SoC后仿结果\n\n','# SDF完整SoC后仿结果\n\n'+quality)
    if not (output/'build/sdf.log').is_file():
        md=md.replace('- [回标原文](build/sdf.log)','- 大型回标原文保留在本次服务器postsim/build/sdf.log；本包保留[编译回标摘要](build/compile.log)')
    (output/'README.md').write_text(md,encoding='utf-8');(output/'README.html').write_text(html_page(md),encoding='utf-8')
    print('Verified post-simulation reports: '+str(output))

if __name__=='__main__':main()
