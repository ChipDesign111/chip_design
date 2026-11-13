#!/usr/bin/env python3
"""One project entry: RTL regression -> implementation -> TT SDF -> Lab5.

--only lab5 uploads the same complete source bundle and binds existing physical
results. No implicit rerun of earlier tools and no automatic retry of mutations.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]


def command(script,*args,capture=False):
    argv=[sys.executable,str(ROOT/script)]+list(map(str,args))
    if capture:
        # Only read-only status queries may retry a transient SSH failure.
        for attempt in range(6):
            try:
                return subprocess.check_output(argv,cwd=str(ROOT),text=True,timeout=60)
            except (subprocess.CalledProcessError,subprocess.TimeoutExpired):
                if attempt==5:raise
                time.sleep(5*(attempt+1))
    subprocess.run(argv,cwd=str(ROOT),check=True)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('command',choices=['run'])
    p.add_argument('--only',choices=['all','lab5'],default='all')
    p.add_argument('--start-at',choices=['rtl','implementation'],default='rtl',help='implementation retains source checks and starts fresh synthesis; skips unchanged RTL regression')
    p.add_argument('--host',default='chipdesign')
    p.add_argument('--eda-upload',help='Required when selecting only Lab5')
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    if a.output.exists() and any(a.output.iterdir()):
        raise ValueError('Use a new empty output directory')
    if a.only=='lab5':
        if not a.eda_upload:raise ValueError('--only lab5 requires explicit --eda-upload')
        command('eda/signoff.py','run','--host',a.host,'--eda-upload',a.eda_upload,'--output',a.output)
        return
    if a.eda_upload:raise ValueError('Full flow starts fresh; existing physical input is only for --only lab5')
    a.output.mkdir(parents=True,exist_ok=True)
    journal={'scope':'New RTL-to-Lab5 execution, TT SDF only','stages':[]}
    def stage(name):
        journal['stages'].append({'name':name,'started_utc':datetime.now(timezone.utc).isoformat()})
        (a.output/'pipeline.json').write_text(json.dumps(journal,indent=2),encoding='utf-8')
    try:
        stage('rtl_check_and_regression')
        command('tools/project.py','check')
        if a.start_at=='rtl':
            command('tools/project.py','test','--soc')
        else:
            journal['rtl_regression']='Not rerun: explicit implementation start; source provenance checks still executed'
        stage('synthesis_and_implementation')
        command('eda/remote.py','run','--host',a.host,'--output',a.output/'implementation')
        physical=json.loads((ROOT/'eda/dist/last_upload.json').read_text())['upload']
        stage('postsim_tt')
        command('eda/postsim.py','run','--host',a.host,'--eda-upload',physical,'--simulator','vcs','--sdf-mode','tt')
        simulation=json.loads((ROOT/'eda/dist/last_postsim.json').read_text())['upload']
        idle=0
        while True:
            state=json.loads(command('eda/postsim.py','status','--host',a.host,'--upload',simulation,capture=True))
            if state['complete']:break
            idle=0 if state['running'] else idle+1
            if idle>=3:raise RuntimeError('No active TT simulation and no completed result')
            time.sleep(20)
        stage('sram_half_cycle_timing')
        command('eda/postsim.py','timing','--host',a.host,'--upload',simulation)
        command('eda/postsim.py','fetch','--host',a.host,'--upload',simulation,'--output',a.output/'postsim_tt')
        audit=json.loads((a.output/'postsim_tt/audit.json').read_text())
        if audit.get('normal_postsim_pass') is not True:
            raise RuntimeError('TT SDF functional/binding/dynamic timing acceptance failed')
        stage('lab5')
        command('eda/signoff.py','run','--host',a.host,'--eda-upload',physical,'--output',a.output/'lab5')
        journal['status']='completed'
    except Exception as e:
        journal['status']='failed_or_review_required'
        journal['error']=str(e)
        raise
    finally:
        (a.output/'pipeline.json').write_text(json.dumps(journal,indent=2),encoding='utf-8')


if __name__=='__main__':
    main()
