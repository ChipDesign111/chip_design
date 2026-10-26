#!/usr/bin/env python3
"""Fresh isolated gate/SDF simulation of an existing completed EDA version."""
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import shlex
import subprocess
import sys
import tarfile
import remote

ROOT=Path(__file__).resolve().parents[1]
DIST=ROOT/'eda/dist'

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['run','status','fetch'])
    parser.add_argument('--host',default='chipdesign')
    parser.add_argument('--eda-upload',help='Completed physical upload; defaults to last_upload.json')
    parser.add_argument('--output',type=Path)
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
        name=datetime.now().strftime('%Y%m%d_%H%M%S')+'_postsim_'+subprocess.check_output(['git','rev-parse','--short','HEAD'],cwd=ROOT).decode().strip()
        upload=remote.valid_upload(parent+'/'+name)
        remote.ssh(args.host,'set -e\nmkdir '+shlex.quote(upload)+'\n')
        remote.scp(args.host,[DIST/'chip_design_eda.tar.gz',DIST/'chip_design_eda.tar.gz.sha256'],upload+'/')
        public=str(Path(parent).parent).replace('\\','/')
        remote.scp(args.host,[ROOT/'eda/unpack.sh'],public+'/unpack.sh')
        remote.ssh(args.host,'bash '+shlex.quote(public+'/unpack.sh')+' '+shlex.quote(upload)+'\n',capture=False)
        remote.scp(args.host,list(firmware.glob('firmware*.hex')),upload+'/configs/')
        remote.save(DIST/'last_postsim.json',{'host':args.host,'upload':upload,'eda_upload':eda})
        cmd='python3 -u deploy/server/postsim/run.py --eda-work '+shlex.quote(eda+'/work')+' --run-root '+shlex.quote(upload+'/postsim')+' --firmware '+shlex.quote(upload+'/configs/firmware.hex')
        print(remote.ssh(args.host,'set -e\nsource /etc/profile.d/eda.sh\ncd '+shlex.quote(upload)+'\nnohup '+cmd+' >logs/postsim.log 2>&1 < /dev/null &\necho $! >logs/postsim.pid\ncat logs/postsim.pid\n'))
        print('Postsim upload: '+upload);return
    state=json.loads((DIST/'last_postsim.json').read_text());upload=remote.valid_upload(state['upload'])
    if args.command=='status':
        print(remote.ssh(args.host,'source /etc/profile.d/eda.sh\npython3 - <<\'PY\'\nfrom pathlib import Path\np=Path('+repr(upload)+')\nq=p/"postsim/results.json"\nprint(q.read_text() if q.exists() else (p/"logs/postsim.log").read_text()[-2000:])\nPY\n'));return
    output=args.output
    if output is None:raise ValueError('fetch requires an empty --output directory')
    if output.exists() and any(output.iterdir()):raise ValueError('Use an empty output directory')
    output.mkdir(parents=True,exist_ok=True)
    remote.ssh(args.host,'set -e\nsource /etc/profile.d/eda.sh\npython3 '+shlex.quote(upload+'/deploy/server/postsim/collect.py')+' '+shlex.quote(upload+'/postsim')+'\n',capture=False)
    remote.scp(args.host,[upload+'/postsim/review.tar.gz',upload+'/postsim/review_manifest.json'],output,download=True)
    manifest=json.loads((output/'review_manifest.json').read_text())
    if remote.digest(output/'review.tar.gz')!=manifest['archive_sha256']:raise ValueError('Archive SHA mismatch')
    with tarfile.open(output/'review.tar.gz','r:gz') as tar:
        for member in tar.getmembers():
            if not member.isfile() or member.name not in manifest['files']:raise ValueError('Unsafe member')
            p=(output/member.name).resolve();p.relative_to(output.resolve());data=tar.extractfile(member).read()
            if hashlib.sha256(data).hexdigest()!=manifest['files'][member.name]:raise ValueError('File SHA mismatch')
            p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
    print('Verified post-simulation reports: '+str(output))

if __name__=='__main__':main()
