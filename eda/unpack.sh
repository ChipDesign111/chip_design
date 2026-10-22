#!/usr/bin/env bash
# Public server entry point. Install at ~/Desktop/fullstack_chipdesign/unpack.sh.
set -euo pipefail
if [ -r /etc/profile.d/eda.sh ]; then source /etc/profile.d/eda.sh; fi
eda_public_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
exec "${EDA_PYTHON:-python3}" - "$eda_public_root" "$@" <<'PY'
import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import html
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import tarfile
import tempfile
from urllib.parse import quote


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for data in iter(lambda: stream.read(1048576), b''):
            h.update(data)
    return h.hexdigest()


def write(path, value):
    if path.is_symlink():
        raise ValueError('Refusing output symlink: ' + str(path))
    with path.open('w', encoding='utf-8', newline='\n') as stream:
        stream.write(value)


def index(root, uploads):
    entries = sorted((p for p in uploads.iterdir() if p.is_dir() and not p.is_symlink()), reverse=True)
    rows = ''.join('<tr><td><a href="%s">%s</a></td><td>%s</td></tr>' %
                   (quote('uploads/' + p.name + '/README.html'), html.escape(p.name),
                    html.escape(json.loads((p / 'upload.json').read_text(encoding='utf-8')).get('git_commit', '')))
                   for p in entries if (p / 'README.html').is_file() and (p / 'upload.json').is_file())
    page = '''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>上传版本索引</title>
<style>body{font-family:"Noto Sans CJK SC",sans-serif;max-width:1100px;margin:36px auto;padding:0 24px;line-height:1.8;color:#203044;background:#f5f7fa}table{border-collapse:collapse;background:white;width:100%%}td,th{border:1px solid #d7dfe8;padding:12px;text-align:left}a{color:#075ea9}pre{background:#152b40;color:white;padding:20px;white-space:pre-wrap}</style>
<h1>fullstack_chipdesign：按上传版本隔离</h1><p>每次上传先在uploads下新建目录，将压缩包放入该目录。顶层unpack.sh是唯一公共解压入口；解压、脚本、配置、日志、报告及结果全部留在对应上传目录内。不同版本不共享deploy、work或配置，没有全局current_run。</p>
<h2>上传版本</h2><table><tr><th>版本（点击查看GUI说明）</th><th>部署源码提交</th></tr>%s</table>
<h2>公共解压</h2><pre>bash unpack.sh uploads/本次新建目录</pre><p>解压器校验包与源码SHA，拒绝在已有版本中覆盖不同原包，不启动EDA。进入对应版本目录后执行bash run_all.sh启动或继续该版本。</p>
<h2>保留资料</h2><ul><li><a href="lab4/">lab4/</a>：完整保留的原Lab 4工程、资料与辅助内容。</li><li><a href="history/">history/</a>：历史有效结果；旧绝对路径代表当时来源，不作为当前上传输入。</li></ul>
<p>顶层只保留公共解压器、版本索引、uploads及保留资料。运行和收集结果只使用版本自己的脚本。原始上传包留在各版本根目录，交付包清理也只作用于对应版本的work。</p></html>''' % rows
    text = '# 按上传版本隔离的服务器工作区\n\n双击README.html查看版本索引。\n\n- unpack.sh：公共解压器。\n- uploads/每次新建目录/：原包、deploy、configs、work、logs、results、docs及全部操作脚本。\n- lab4/：原Lab 4内容完整保留。\n- history/：历史有效结果，非当前输入。\n\n每次上传新建目录；用bash unpack.sh uploads/目录解压，再进入该目录运行bash run_all.sh。没有全局deploy、runs、config或current_run。\n'
    for name, body in [('README.html', page), ('README.md', text)]:
        fd, temporary = tempfile.mkstemp(prefix='.readme_', dir=str(root))
        os.close(fd)
        path = Path(temporary)
        write(path, body)
        os.replace(str(path), str(root / name))


parser = argparse.ArgumentParser(description='Unpack one independent uploads/<version> directory')
parser.add_argument('workspace', type=Path)
parser.add_argument('upload', type=Path, help='Absolute path or uploads/<version> relative to the public script')
args = parser.parse_args()
root = args.workspace.resolve()
uploads = root / 'uploads'
if uploads.is_symlink():
    raise ValueError('uploads must be a real directory')
uploads.mkdir(exist_ok=True)
candidate = args.upload.expanduser()
if not candidate.is_absolute():
    candidate = root / candidate
if candidate.is_symlink() or candidate.parent.resolve() != uploads.resolve():
    raise ValueError('Each upload must be a real, direct child of <workspace>/uploads')
upload = candidate.resolve()
if not upload.is_dir() or not re.fullmatch(r'[A-Za-z0-9_.-]+', upload.name):
    raise ValueError('Create a new ASCII upload directory first')
archive, checksum = upload / 'chip_design_eda.tar.gz', upload / 'chip_design_eda.tar.gz.sha256'
for path in [archive, checksum, upload / 'deploy', upload / 'upload.json']:
    if path.is_symlink():
        raise ValueError('Upload inputs cannot be symlinks: ' + str(path))
line = checksum.read_text(encoding='utf-8').strip().split()
if len(line) != 2 or line[1] != archive.name or not re.fullmatch(r'[0-9a-fA-F]{64}', line[0]):
    raise ValueError('Invalid upload checksum file')
actual = digest(archive)
if actual.lower() != line[0].lower():
    raise ValueError('Upload archive checksum mismatch')
lock = upload / '.unpack.lock'
fd = os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
os.close(fd)
staging = None
try:
    deploy, record_path = upload / 'deploy', upload / 'upload.json'
    if deploy.exists():
        previous = json.loads(record_path.read_text(encoding='utf-8')) if record_path.is_file() else {}
        if previous.get('archive_sha256') != actual:
            raise ValueError('This upload already contains another archive; create a NEW upload directory')
        source = json.loads((deploy / 'source.json').read_text(encoding='utf-8'))
        for name, data in source['files'].items():
            path = deploy / name
            path.resolve().relative_to(deploy.resolve())
            if path.is_symlink() or digest(path) != data['sha256']:
                raise ValueError('Existing deployment changed: ' + name)
    else:
        staging = Path(tempfile.mkdtemp(prefix='.unpack_', dir=str(upload)))
        with tarfile.open(str(archive), 'r:gz') as tar:
            members = tar.getmembers()
            names = [m.name for m in members]
            if len(names) != len(set(names)) or sum(m.size for m in members) > 512 * 1024 * 1024:
                raise ValueError('Duplicate entries or oversized deployment')
            for member in members:
                relative = PurePosixPath(member.name)
                if (relative.is_absolute() or '..' in relative.parts or '\\' in member.name
                        or not relative.parts or relative.parts[0] not in ['server', 'rtl', 'docs', 'source.json']
                        or not (member.isfile() or member.isdir())):
                    raise ValueError('Unsafe deployment member: ' + member.name)
                target = staging.joinpath(*relative.parts)
                target.resolve().relative_to(staging.resolve())
                if member.isdir():
                    target.mkdir(parents=True, exist_ok=True)
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with tar.extractfile(member) as src, target.open('wb') as dst:
                        shutil.copyfileobj(src, dst, 1048576)
            source = json.loads((staging / 'source.json').read_text(encoding='utf-8'))
            actual_files = {m.name for m in members if m.isfile()}
            if actual_files != set(source['files']) | {'source.json'}:
                raise ValueError('Deployment entries do not match source.json')
            for name, data in source['files'].items():
                if digest(staging / name) != data['sha256']:
                    raise ValueError('Deployment payload checksum mismatch: ' + name)
        os.rename(str(staging), str(deploy))
        staging = None
        record = {'archive_sha256': actual, 'git_commit': source.get('git_commit'),
                  'upload': str(upload), 'extracted_at': datetime.now(timezone(timedelta(hours=8))).isoformat()}
        write(record_path, json.dumps(record, ensure_ascii=False, indent=2) + '\n')
    subprocess.run(['bash', str(deploy / 'server/bin/workspace.sh'), '--root', str(upload)], check=True)
    index(root, uploads)
    print('Ready: ' + str(upload) + '\nRun inside this directory: bash ./run_all.sh')
finally:
    if staging is not None:
        staging.resolve().relative_to(upload)
        if staging.parent != upload or not staging.name.startswith('.unpack_'):
            raise ValueError('Unexpected extraction staging path')
        shutil.rmtree(str(staging))
    lock.unlink()
PY
