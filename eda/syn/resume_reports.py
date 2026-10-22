#!/usr/bin/env python3
"""Regenerate reports/exports from a saved mapped Genus checkpoint, Python 3.8+."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess

HERE = Path(__file__).resolve().parent


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def tq(value):
    value=str(value)
    if any(c in value for c in '{}\r\n'):
        raise ValueError('Unsupported Tcl path')
    return '{'+value+'}'


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--from-dir',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--genus',default='genus')
    ap.add_argument('--source-snapshot',type=Path)
    args=ap.parse_args()
    original=args.from_dir.resolve(); out=args.out.resolve()
    setup=original/'backup/my_soc_top.genus_setup.tcl'
    if not setup.is_file():
        raise FileNotFoundError(str(setup))
    if out.exists() and any(out.iterdir()):
        raise RuntimeError('Choose a fresh output directory')
    old=json.loads((original/'manifest.json').read_text())
    old_log=(original/'console.log').read_text(errors='replace')
    diagnostics=re.findall(r'^(?:Error|Fatal)\s*:.*$',old_log,re.M)
    if diagnostics and (len(diagnostics)!=1 or '[TUI-204]' not in diagnostics[0] or "'-early'" not in old_log):
        raise RuntimeError('Original mapping run has unresolved diagnostics; inspect before restoring: '+str(diagnostics))
    out.mkdir(parents=True,exist_ok=True)
    for name in ('reports','outputs','backup'):
        (out/name).mkdir()
    for name in ('check_elaborated.rpt','check_generic.rpt','check_mapped.rpt','messages_elaborated.rpt','timing_intent_elaborated.rpt'):
        p=original/'reports'/name
        if p.is_file():
            (out/'reports'/name).write_bytes(p.read_bytes())
    config=original/'run_config.tcl'
    job='\n'.join([
        'cd '+tq(original),
        'source '+tq(setup),
        'source '+tq(config),
        'set output_root '+tq(out),
        'set script_root '+tq(HERE),
        'cd '+tq(out),
        'source '+tq(HERE/'reports.tcl'),
        'exit',
    ])+'\n'
    (out/'resume.tcl').write_text(job)
    (out/'run_config.tcl').write_bytes(config.read_bytes())
    record=dict(old)
    if args.source_snapshot:
        snapshot=json.loads(args.source_snapshot.read_text())
        if snapshot.get('status')!='PASS' or snapshot['source_revision']!=record['source_revision']:
            raise RuntimeError('Source snapshot is not verified for this revision')
        for name,value in record['source_sha256'].items():
            if snapshot['source_sha256'].get(name)!=value:
                raise RuntimeError('Source snapshot differs from synthesis inputs: '+name)
        record['source_sha256']=snapshot['source_sha256']
        record['source_snapshot']=snapshot
    record.pop('exit_code',None);record.pop('finished_utc',None)
    record.update(started_utc=datetime.now(timezone.utc).isoformat(),
        mapping_checkpoint={
            'directory':str(original),'original_exit_code':old.get('exit_code'),
            'original_diagnostics':diagnostics,
            'reason':'Native Genus 19.17 does not implement report_timing -early; mapped checkpoint retained, native hold report removed',
            'backup_sha256':{p.name:sha(p) for p in (original/'backup').glob('*') if p.is_file()},
        },
        report_flow_sha256={p.name:sha(p) for p in (HERE/'reports.tcl',HERE/'resume_reports.py')})
    (out/'manifest.json').write_text(json.dumps(record,indent=2))
    with (out/'console.log').open('w') as log:
        result=subprocess.run([args.genus,'-no_gui','-abort_on_error','-f',str(out/'resume.tcl'),'-log','genus'],cwd=str(out),stdout=log,stderr=subprocess.STDOUT)
    record.update(exit_code=result.returncode,finished_utc=datetime.now(timezone.utc).isoformat())
    (out/'manifest.json').write_text(json.dumps(record,indent=2))
    print('Report/export recovery exit code: '+str(result.returncode),flush=True)
    raise SystemExit(result.returncode)


if __name__=='__main__':
    main()
