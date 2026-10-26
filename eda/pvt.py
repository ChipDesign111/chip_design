#!/usr/bin/env python3
"""Deploy, inspect and fetch an isolated read-only available-library PVT run."""
import argparse,hashlib,json,shlex,subprocess,sys,tarfile
from datetime import datetime
from pathlib import Path,PurePosixPath
import remote
ROOT=Path(__file__).resolve().parents[1];DIST=ROOT/'eda/dist'
def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('command',choices=['run','status','fetch']);ap.add_argument('--host',default='chipdesign');ap.add_argument('--eda-upload');ap.add_argument('--output',type=Path);a=ap.parse_args()
    if a.command=='run':
        eda=remote.valid_upload(a.eda_upload or json.loads((DIST/'last_upload.json').read_text())['upload'])
        if not remote.status(a.host,eda)['ready']:raise ValueError('Completed physical input required')
        subprocess.run([sys.executable,str(ROOT/'eda/package_server.py')],cwd=ROOT,check=True)
        parent=PurePosixPath(eda).parent;workspace=parent.parent
        name=datetime.now().strftime('%Y%m%d_%H%M%S')+'_pvt_'+subprocess.check_output(['git','rev-parse','--short','HEAD'],cwd=ROOT).decode().strip();upload=remote.valid_upload(str(parent/name))
        remote.ssh(a.host,'set -e\nmkdir '+shlex.quote(upload)+'\n');remote.scp(a.host,[DIST/'chip_design_eda.tar.gz',DIST/'chip_design_eda.tar.gz.sha256'],upload+'/')
        remote.scp(a.host,[ROOT/'eda/unpack.sh'],str(workspace)+'/unpack.sh');remote.ssh(a.host,'bash '+shlex.quote(str(workspace)+'/unpack.sh')+' '+shlex.quote(upload)+'\n',capture=False)
        remote.save(DIST/'last_pvt.json',{'host':a.host,'upload':upload,'eda_upload':eda})
        cmd='python3 -u deploy/server/postsim/pvt.py --eda-work '+shlex.quote(eda+'/work')+' --output '+shlex.quote(upload+'/pvt')
        print(remote.ssh(a.host,'set -e\nsource /etc/profile.d/eda.sh\ncd '+shlex.quote(upload)+'\nnohup '+cmd+' >logs/pvt.log 2>&1 < /dev/null &\necho $! >logs/pvt.pid\ncat logs/pvt.pid\n'));print(upload);return
    s=json.loads((DIST/'last_pvt.json').read_text());u=remote.valid_upload(s['upload'])
    if a.command=='status':
        script=r'''source /etc/profile.d/eda.sh
python3 - <<'PY'
from pathlib import Path
import json
p=Path(UPLOAD);r=p/'pvt/results.json';pid=int((p/'logs/pvt.pid').read_text());proc=Path('/proc/%d/cmdline'%pid)
print(json.dumps({'upload':str(p),'running':proc.exists() and b'postsim/pvt.py' in proc.read_bytes(),'results':json.loads(r.read_text()) if r.exists() else None,'log':(p/'logs/pvt.log').read_text(errors='replace')[-1800:]}))
PY
'''.replace('UPLOAD',repr(u));print(remote.ssh(a.host,script));return
    out=a.output
    if out is None or (out.exists() and any(out.iterdir())):raise ValueError('Use an empty --output')
    out.mkdir(parents=True,exist_ok=True);remote.scp(a.host,[u+'/pvt/review.tar.gz',u+'/pvt/review_manifest.json'],out,download=True)
    m=json.loads((out/'review_manifest.json').read_text());assert remote.digest(out/'review.tar.gz')==m['archive_sha256']
    with tarfile.open(out/'review.tar.gz') as t:
        for member in t.getmembers():
            if not member.isfile() or member.name not in m['files']:raise ValueError('Unsafe member')
            p=(out/member.name).resolve();p.relative_to(out.resolve());b=t.extractfile(member).read();assert hashlib.sha256(b).hexdigest()==m['files'][member.name];p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
    print('Verified PVT reports: '+str(out))
if __name__=='__main__':main()
