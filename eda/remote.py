#!/usr/bin/env python3
"""Package, deploy, run and retrieve one isolated server upload (Python 3.8+)."""
import argparse
from datetime import datetime
import gzip
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import shlex
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time

EDA = Path(__file__).resolve().parent
DIST = EDA / 'dist'


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for data in iter(lambda: stream.read(1048576), b''):
            h.update(data)
    return h.hexdigest()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def ssh(host, script, capture=True):
    result = subprocess.run(['ssh', '-o', 'ClearAllForwardings=yes', '-o', 'BatchMode=yes', host, 'bash', '-s'],
                            input=script.encode('utf-8'), stdout=subprocess.PIPE if capture else None, check=True)
    return result.stdout.decode('utf-8').strip() if capture else None


def scp(host, files, target, download=False):
    sources = [host + ':' + p for p in files] if download else [str(p) for p in files]
    dest = str(target) if download else host + ':' + target
    subprocess.run(['scp', '-o', 'ClearAllForwardings=yes', '-o', 'BatchMode=yes'] + sources + [dest], check=True)


def valid_upload(value):
    path = PurePosixPath(value)
    if not path.is_absolute() or path.parent.name != 'uploads' or '..' in path.parts or not re.fullmatch(r'[A-Za-z0-9_./-]+', value):
        raise ValueError('Use the full server path ending in uploads/<version>')
    return str(path)


def selection(args):
    if args.upload:
        return args.host, valid_upload(args.upload)
    record = json.loads((DIST / 'last_upload.json').read_text(encoding='utf-8'))
    if args.host != record['host']:
        raise ValueError('Host differs from local last_upload.json; specify --upload explicitly')
    return args.host, valid_upload(record['upload'])


def status(host, upload):
    script = '''set -e
if [ -r /etc/profile.d/eda.sh ]; then source /etc/profile.d/eda.sh; fi
python3 - <<'PY'
from pathlib import Path
import json, os
u = Path(UPLOAD)
work = u/'work'
def number(path):
    return int(path.read_text().strip()) if path.is_file() else None
last = number(work/'evidence/last_step.txt') or 0
code = number(u/'logs/run_exit_code.txt')
running = (work/'evidence/flow.lock').is_file()
pid = number(u/'logs/launcher.pid')
if pid:
    try:
        running = running or (Path('/proc/%d/cwd'%pid).resolve() == u.resolve() and b'run_all.sh' in Path('/proc/%d/cmdline'%pid).read_bytes())
    except (FileNotFoundError, PermissionError): pass
ready = last == 34 and all((work/name).is_file() for name in ['review_delivery.tar.gz','review_delivery.tar.gz.sha256','review_manifest.json','delivery_manifest.json'])
errors = (work/'evidence/unexpected_tool_errors.json').is_file()
if errors: ready = False
phase = 'preparation'
if (work/'evidence/genus_synthesis.log').is_file(): phase = 'Genus synthesis'
if last or list((work/'evidence').glob('innovus_*.log')): phase = 'Innovus %d/34'%last
if last == 34: phase = 'result collection'
if ready: phase = 'ready to download'
print(json.dumps({'upload':str(u),'phase':phase,'last_step':last,'running':running,'exit_code':code,'ready':ready,'unexpected_tool_errors':errors}))
PY
'''.replace('UPLOAD', repr(upload))
    return json.loads(ssh(host, script))


def launch(host, upload, headless=False):
    command = 'bash ./run_all.sh' + (' --headless' if headless else '')
    script = 'set -e\ncd ' + shlex.quote(upload) + '\n'
    script += 'test -f ./check_env.sh && test -f ./run_eda.sh && test -f ./collect_results.sh\n'
    script += 'nohup ' + command + ' >logs/launcher.log 2>&1 < /dev/null &\n'
    script += 'printf "%s\\n" "$!" >logs/launcher.pid\nprintf "Started PID %s\\n" "$!"\n'
    print(ssh(host, script), flush=True)


def wait(host, upload, interval):
    idle = 0
    while True:
        state = status(host, upload)
        print(datetime.now().strftime('%H:%M:%S') + ' ' + json.dumps(state, ensure_ascii=False), flush=True)
        if state['ready'] and state['exit_code'] in [None, 0]:
            return state
        if (state['exit_code'] not in [None, 0] and not state['running']) or state['unexpected_tool_errors']:
            raise RuntimeError('Server stage failed; inspect logs/environment.log, flow.log, collect.log and pipeline.log in ' + upload)
        idle = 0 if state['running'] else idle + 1
        if idle >= 3:
            raise RuntimeError('No active pipeline or complete bundle found. Inspect server logs; use resume after resolving the cause.')
        time.sleep(interval)


def verify_and_extract(directory):
    archive = directory / 'review_delivery.tar.gz'
    fields = (directory / 'review_delivery.tar.gz.sha256').read_text(encoding='utf-8').split()
    if len(fields) != 2 or fields[1] != archive.name or digest(archive) != fields[0]:
        raise ValueError('Review archive checksum mismatch')
    manifest = json.loads((directory / 'review_manifest.json').read_text(encoding='utf-8'))
    if digest(directory / 'delivery_manifest.json') != manifest['full_manifest_sha256']:
        raise ValueError('Full manifest checksum mismatch')
    core = directory / 'core'
    core.mkdir()
    with tarfile.open(str(archive), 'r:gz') as tar:
        members = tar.getmembers()
        if len(members) != len({m.name for m in members}) or {m.name for m in members} != set(manifest['files']) | {'review_manifest.json', 'delivery_manifest.json'}:
            raise ValueError('Unexpected review archive entries')
        if sum(m.size for m in members) > 256 * 1024 * 1024:
            raise ValueError('Review archive exceeds the small-bundle limit')
        for member in members:
            relative = PurePosixPath(member.name)
            if not member.isfile() or relative.is_absolute() or '..' in relative.parts or '\\' in member.name or ':' in member.name:
                raise ValueError('Unsafe review member: ' + member.name)
            target = core.joinpath(*relative.parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            with tar.extractfile(member) as src, target.open('wb') as dst:
                shutil.copyfileobj(src, dst, 1048576)
    for name, data in manifest['files'].items():
        path = core / name
        if path.stat().st_size != data['bytes'] or digest(path) != data['sha256']:
            raise ValueError('Review file changed: ' + name)
    for name in ['review_manifest.json', 'delivery_manifest.json']:
        if digest(core / name) != digest(directory / name):
            raise ValueError('Embedded manifest differs: ' + name)
    identity = digest(core / 'evidence/input_manifest.json')
    if identity != manifest['input_manifest_sha256']:
        raise ValueError('Input identity mismatch')
    for step in range(1, 35):
        stage = json.loads((core / ('evidence/step_%02d.json' % step)).read_text(encoding='utf-8'))
        if stage['input_manifest_sha256'] != identity or not stage['commands_completed']:
            raise ValueError('Incomplete or inherited stage identity: ' + str(step))
    geometry=json.loads((core/'evidence/geometry.json').read_text(encoding='utf-8'))
    config=json.loads((core/'config/design.json').read_text(encoding='utf-8'))
    die=geometry['die_um'];limit=config['max_die_area_mm2']
    if len(die)!=4 or die[:2]!=[0,0] or not all(isinstance(v,(int,float)) and math.isfinite(v) and v>0 for v in die[2:]):
        raise ValueError('Invalid whole Die geometry')
    whole_area=die[2]*die[3]/1e6
    if not isinstance(limit,(int,float)) or not math.isfinite(limit) or not 0<limit<=4.0 or whole_area>limit:
        raise ValueError('Invalid configured whole-Die limit or measured area exceeds it: limit=%s, area=%s mm2' % (limit,whole_area))
    audit=json.loads((core/'evidence/export_audit.json').read_text(encoding='utf-8'))
    if abs(audit['whole_die_area_mm2']-whole_area)>1e-9:
        raise ValueError('Export and floorplan whole Die area differ')
    hierarchy = manifest['compressed_hierarchy_source']
    h, size = hashlib.sha256(), 0
    with gzip.open(str(core / (hierarchy['file'] + '.gz')), 'rb') as stream:
        for data in iter(lambda: stream.read(1048576), b''):
            h.update(data)
            size += len(data)
    if h.hexdigest() != hierarchy['sha256'] or size != hierarchy['bytes']:
        raise ValueError('Compressed hierarchy source mismatch')
    return {'archive_sha256': digest(archive), 'files_verified': len(manifest['files']), 'input_manifest_sha256': identity,
            'remote_upload': str(PurePosixPath(manifest['remote_work']).parent), 'all_34_steps_same_input': True, 'whole_die_area_mm2':whole_area, 'max_whole_die_area_mm2':limit}


def fetch(host, upload, output):
    if not status(host, upload)['ready']:
        raise RuntimeError('Run the three server stages to completion first, or add --wait')
    output = output.expanduser() if output else DIST / 'results' / (PurePosixPath(upload).name + '_' + datetime.now().strftime('%H%M%S'))
    if output.is_symlink():
        raise ValueError('Local output must be a real directory')
    output = output.resolve()
    if output.exists() and any(output.iterdir()):
        raise ValueError('Choose an empty local --output directory: ' + str(output))
    output.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix='.download_', dir=str(output)))
    try:
        names = ['review_delivery.tar.gz', 'review_delivery.tar.gz.sha256', 'review_manifest.json', 'delivery_manifest.json']
        scp(host, [upload + '/work/' + name for name in names], staging, download=True)
        receipt = verify_and_extract(staging)
        if receipt['remote_upload'] != upload:
            raise ValueError('Bundle belongs to a different upload')
        save(staging / 'receipt.json', receipt)
        md = '# 本地EDA结果\n\n服务器版本：`' + upload + '`\n\n压缩包、逐文件及34步输入身份已核对；大型GDS/DEF/SDF/SPEF与数据库保留服务器。\n\n- [逐步运行报告](core/evidence/运行报告.md)：每步做什么、为什么和实际输出。\n- [最终时序与物理检查](core/evidence/step_33.json)：Setup/Hold、DRV、DRC、供电、信号与天线。\n- [最终导出检查](core/evidence/step_34.json)：DEF、SDF、SPEF与GDS结构对应关系。\n- [布局图](core/evidence/34_final_layout.gif)。\n- [原始综合报告](core/syn/my_soc_top/reports/)。\n- [原始后端报告](core/pnr/my_soc_top/reports/)。\n- [大文件服务器位置与SHA](review_manifest.json)。\n\n解读方法见仓库eda/docs/报告查找与分析.md。压缩文本报告用gzip读取或先解压，时间单位为ns。独立晶圆厂签核和SDF回标仿真不在本流程结果中。\n'
        md+='\n含 PAD 的整个 Die：'+str(receipt['whole_die_area_mm2'])+' mm²，上限 '+str(receipt['max_whole_die_area_mm2'])+' mm²。\n'
        (staging / 'README.md').write_text(md, encoding='utf-8')
        import importlib.util
        spec = importlib.util.spec_from_file_location('eda_readme_renderer', EDA / 'server/tools/workspace.py')
        renderer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(renderer)
        page = '<!doctype html><meta charset="utf-8"><style>body{font-family:sans-serif;max-width:1000px;margin:40px auto;line-height:1.8}code{overflow-wrap:anywhere}a{color:#075ea9}</style>' + renderer.render_markdown(md)
        (staging / 'README.html').write_text(page, encoding='utf-8')
        for item in list(staging.iterdir()):
            os.replace(str(item), str(output / item.name))
    finally:
        staging.resolve().relative_to(output.resolve())
        shutil.rmtree(str(staging))
    print('Verified results: ' + str(output) + '\nOpen: ' + str(output / 'README.html'), flush=True)
    return output


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='command', required=True)
    for command in ['run', 'resume', 'status', 'fetch']:
        a = sub.add_parser(command)
        a.add_argument('--host', default='chipdesign')
        a.add_argument('--upload', help='Existing full server uploads/<version> path; defaults to the LOCAL last_upload.json')
        a.add_argument('--output', type=Path, help='Empty LOCAL result directory')
        a.add_argument('--interval', type=int, default=30, choices=range(5, 61))
        if command in ['run', 'resume']:
            a.add_argument('--detach', action='store_true', help='Start server pipeline and return; use fetch --wait later')
            a.add_argument('--headless', action='store_true', help='Skip layout screenshots')
        if command == 'run':
            a.add_argument('--root', help='Public server root; default is $HOME/Desktop/fullstack_chipdesign')
            a.add_argument('--name', help='New ASCII upload directory name')
            a.add_argument('--config', type=Path, help='Optional local design.json copied before environment preparation')
        if command == 'fetch':
            a.add_argument('--wait', action='store_true')
    args = p.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_.@-]*', args.host):
        raise ValueError('Use an SSH alias or user@hostname')
    for executable in ['ssh', 'scp']:
        if not shutil.which(executable):
            raise ValueError('Missing local executable: ' + executable)
    if args.command == 'run':
        if args.upload:
            raise ValueError('run always creates a NEW upload; use resume for an existing upload')
        if args.config:
            json.loads(args.config.read_text(encoding='utf-8-sig'))
        subprocess.run([sys.executable, str(EDA / 'package_server.py')], check=True, cwd=str(EDA.parent))
        home = ssh(args.host, 'printf "%s\\n" "$HOME"\n')
        root = args.root or home + '/Desktop/fullstack_chipdesign'
        if not re.fullmatch(r'/[A-Za-z0-9_./-]+', root) or '..' in PurePosixPath(root).parts:
            raise ValueError('Use an absolute ASCII server root without spaces')
        commit = subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD'], cwd=str(EDA.parent)).decode().strip()
        name = args.name or datetime.now().strftime('%Y%m%d_%H%M%S') + '_' + commit
        if not re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_.-]*', name):
            raise ValueError('Invalid upload name')
        upload = valid_upload(root + '/uploads/' + name)
        ssh(args.host, 'set -e\nmkdir -p ' + shlex.quote(root + '/uploads') + '\nmkdir ' + shlex.quote(upload) + '\n')
        save(DIST / 'last_upload.json', {'host': args.host, 'upload': upload})
        (DIST / 'latest_upload_path.txt').write_text(upload + '\n', encoding='utf-8')
        save(DIST / 'uploads' / (name + '.json'), {'host': args.host, 'upload': upload})
        scp(args.host, [EDA / 'unpack.sh'], root + '/unpack.sh')
        scp(args.host, [DIST / 'chip_design_eda.tar.gz', DIST / 'chip_design_eda.tar.gz.sha256'], upload + '/')
        ssh(args.host, 'set -e\nbash ' + shlex.quote(root + '/unpack.sh') + ' ' + shlex.quote(upload) + '\n', capture=False)
        if args.config:
            # Normalize a possible Windows BOM/newline before copying the user's configuration.
            normalized = DIST / 'selected_design.json'
            save(normalized, json.loads(args.config.read_text(encoding='utf-8-sig')))
            scp(args.host, [normalized], upload + '/configs/design.json')
        host = args.host
        print('Upload: ' + upload, flush=True)
    else:
        host, upload = selection(args)
    if args.command in ['run', 'resume']:
        if args.command == 'resume' and status(host, upload)['running']:
            raise RuntimeError('This upload is already running; use status or fetch --wait')
        launch(host, upload, args.headless)
        if args.detach:
            print('Server continues independently. Later: python eda/remote.py fetch --upload ' + upload + ' --wait', flush=True)
            return
        wait(host, upload, args.interval)
        fetch(host, upload, args.output)
    elif args.command == 'status':
        print(json.dumps(status(host, upload), ensure_ascii=False, indent=2))
    else:
        if args.wait:
            wait(host, upload, args.interval)
        fetch(host, upload, args.output)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('\nLocal waiting stopped. The remote nohup pipeline continues; use fetch --wait later.', file=sys.stderr)
        sys.exit(130)
    except Exception as error:
        print('EDA REMOTE STOP: ' + str(error), file=sys.stderr)
        sys.exit(1)
