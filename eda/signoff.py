#!/usr/bin/env python3
"""Deploy the complete RTL-to-Lab5 source bundle; execute only Lab5 on bound physical results."""
import argparse
from datetime import datetime
import json
from pathlib import Path
import shlex
import subprocess
import sys
import tarfile
import time
import remote

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT/'eda/dist'


def state(host, upload):
    script = '''python3 - <<'PY'
import json
from pathlib import Path
p=Path(UPLOAD)
f=p/'logs/lab5_exit_code.txt'
r=p/'results/lab5.json'
print(json.dumps({'exit_code':int(f.read_text()) if f.exists() else None,
                 'result':json.loads(r.read_text()) if r.exists() else None}))
PY
'''.replace('UPLOAD', repr(upload))
    return json.loads(remote.ssh(host, script))


def fetch(host, upload, output):
    if output.exists() and any(output.iterdir()):
        raise ValueError('Use a new empty local result directory')
    output.mkdir(parents=True, exist_ok=True)
    remote.scp(host, [upload+'/results/lab5_review.tar.gz', upload+'/results/lab5_review_manifest.json'], output, download=True)
    manifest = json.loads((output/'lab5_review_manifest.json').read_text())
    archive = output/'lab5_review.tar.gz'
    if remote.digest(archive) != manifest['archive_sha256']:
        raise ValueError('Review archive SHA mismatch')
    seen = set()
    with tarfile.open(str(archive), 'r:gz') as t:
        for m in t.getmembers():
            if not m.isfile() or m.name not in manifest['files'] or m.name in seen:
                raise ValueError('Unsafe or duplicate review member')
            p = (output/m.name).resolve()
            p.relative_to(output.resolve())
            p.parent.mkdir(parents=True, exist_ok=True)
            data = t.extractfile(m).read()
            if __import__('hashlib').sha256(data).hexdigest() != manifest['files'][m.name]['sha256']:
                raise ValueError('Review file SHA mismatch: '+m.name)
            p.write_bytes(data)
            seen.add(m.name)
    if seen != set(manifest['files']):
        raise ValueError('Incomplete review archive')
    remote.save(output/'receipt.json', {'host':host, 'upload':upload, 'files_verified':len(seen), 'archive_sha256':manifest['archive_sha256']})


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('command', choices=['run','status','fetch'])
    p.add_argument('--host', default='chipdesign')
    p.add_argument('--eda-upload')
    p.add_argument('--upload')
    p.add_argument('--output', type=Path)
    p.add_argument('--detach', action='store_true')
    p.add_argument('--wait', action='store_true')
    args=p.parse_args()
    if args.command=='run':
        if not args.detach and args.output is None:
            raise ValueError('run requires --output or --detach')
        physical=remote.valid_upload(args.eda_upload or json.loads((DIST/'last_upload.json').read_text())['upload'])
        if args.output and args.output.exists() and any(args.output.iterdir()):
            raise ValueError('Use a new empty local result directory')
        if not remote.status(args.host, physical)['ready']:
            raise ValueError('Bound physical implementation is incomplete')
        subprocess.run([sys.executable, str(ROOT/'eda/package_server.py')], cwd=str(ROOT), check=True)
        commit=subprocess.check_output(['git','rev-parse','--short','HEAD'],cwd=str(ROOT),text=True).strip()
        parent=physical.rsplit('/',1)[0]
        upload=parent+'/'+datetime.now().strftime('%Y%m%d_%H%M%S')+'_lab5_'+commit
        remote.ssh(args.host, 'set -e\nmkdir '+shlex.quote(upload)+'\n')
        remote.scp(args.host,[DIST/'chip_design_eda.tar.gz',DIST/'chip_design_eda.tar.gz.sha256'],upload+'/')
        # Reuse the single public unpacker and complete deployment contract.
        public=parent.rsplit('/',1)[0]+'/unpack.sh'
        remote.scp(args.host,[ROOT/'eda/unpack.sh'],public)
        remote.ssh(args.host,'bash '+shlex.quote(public)+' '+shlex.quote(upload)+'\n',capture=False)
        remote.save(DIST/'last_lab5.json',{'host':args.host,'upload':upload,'eda_upload':physical})
        command='python3 -u deploy/server/lab5/run.py --root '+shlex.quote(upload)+' --physical '+shlex.quote(physical)
        remote.ssh(args.host,'set -e\nsource /etc/profile.d/eda.sh\ncd '+shlex.quote(upload)+'\nnohup '+command+' >logs/lab5.log 2>&1 < /dev/null &\necho $! >logs/lab5.pid\n')
        print('Complete deployment; Lab5-only execution: '+upload,flush=True)
        if args.detach:
            return
    else:
        saved=json.loads((DIST/'last_lab5.json').read_text())
        upload=remote.valid_upload(args.upload or saved['upload'])
    if args.command=='status':
        print(json.dumps(state(args.host,upload),ensure_ascii=False,indent=2));return
    if args.output is None:
        raise ValueError('fetch requires --output')
    while True:
        current=state(args.host,upload)
        if current['exit_code'] is not None:
            break
        if args.command=='fetch' and not args.wait:
            raise RuntimeError('Still running; use fetch --wait')
        time.sleep(15)
    fetch(args.host,upload,args.output)
    print(json.dumps(current,ensure_ascii=False,indent=2))
    if current['exit_code']:
        raise SystemExit(current['exit_code'])


if __name__=='__main__':
    main()
