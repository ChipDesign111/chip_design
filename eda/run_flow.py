#!/usr/bin/env python3
"""Complete-SoC RTL -> TSMC180 synthesis -> gate -> SDF flow, Python 3.8+."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--pdk', type=Path, default=Path(os.environ.get('CHIP_PDK_ROOT','/lec/pdk/tsmc180')))
    ap.add_argument('--sram', type=Path, default=Path(os.environ.get('CHIP_SRAM_ROOT','/lec/lab4/soc_cv32e40p_template_pnr-stu/src/macro/RA1SHD_2048x32M8')))
    ap.add_argument('--out',type=Path)
    ap.add_argument('--cpus',type=int,default=8)
    ap.add_argument('--xrun',default='xrun')
    ap.add_argument('--genus',default='genus')
    ap.add_argument('--source-revision',help='Optional source label for an archive-based run without .git')
    ap.add_argument('--dry-run',action='store_true')
    args = ap.parse_args()
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    out = (args.out or ROOT/'eda/work'/('asic_'+stamp)).resolve()
    if out.exists() and any(out.iterdir()):
        ap.error('Choose a fresh output directory')
    out.mkdir(parents=True,exist_ok=True)
    macro = args.sram.resolve()/'RA1SHD_2048x32M8.v'
    cells = args.pdk.resolve()/'tcb018gbwp7t_290a/TSMCHOME/digital/Front_End/verilog/tcb018gbwp7t_270a/tcb018gbwp7t.v'
    pin_base = [sys.executable,str(ROOT/'eda/sim/run_pins.py'),'--sram-model',str(macro),'--xrun',args.xrun]
    cases = ['--only','synthetic','--only','dma']
    syn = out/'synthesis'
    revision_args = ['--source-revision',args.source_revision] if args.source_revision else []
    gate_inputs = ['--netlist',str(syn/'outputs/my_soc_top_postsyn.v'),'--library',str(cells)]
    commands = [
        ('rtl',pin_base+['--mode','rtl','--memory','ra1shd',*cases,'--only','corrupt_download','--out',str(out/'rtl')]),
        ('synthesis',[sys.executable,str(ROOT/'eda/syn/run_synthesis.py'),'--pdk',str(args.pdk.resolve()),'--sram',str(args.sram.resolve()),'--cpus',str(args.cpus),'--genus',args.genus,*revision_args,'--out',str(syn)]),
        ('gate',pin_base+['--mode','gate',*gate_inputs,*cases,'--xrun-arg=-sequdp_nba_delay','--out',str(out/'gate')]),
        ('sdf',pin_base+['--mode','sdf',*gate_inputs,'--sdf',str(syn/'outputs/my_soc_top_tt.sdf'),*cases,'--out',str(out/'sdf')]),
        ('audit',[sys.executable,str(ROOT/'eda/check_results.py'),'--synthesis',str(syn),'--rtl',str(out/'rtl'),'--gate',str(out/'gate'),'--sdf',str(out/'sdf'),'--out',str(out/'verification.json')]),
    ]
    state = {'started_utc':datetime.now(timezone.utc).isoformat(),'status':'PREPARED' if args.dry_run else 'RUNNING',
             'scope':'TT post-synthesis baseline, no placement/CTS/routed parasitics','stages':[]}
    state_path = out/'flow.json'
    for name,command in commands:
        record={'name':name,'command':command,'status':'PREPARED'}
        state['stages'].append(record)
        state_path.write_text(json.dumps(state,indent=2))
        print(name+': '+json.dumps(command),flush=True)
        if args.dry_run:
            continue
        record['status']='RUNNING'
        state_path.write_text(json.dumps(state,indent=2))
        result=subprocess.run(command,cwd=str(ROOT))
        record['exit_code']=result.returncode
        if result.returncode:
            record['status']='FAIL';state['status']='FAIL'
            state_path.write_text(json.dumps(state,indent=2))
            raise SystemExit(result.returncode)
        if name=='synthesis':
            log=(syn/'console.log').read_text(errors='replace')
            errors=re.findall(r'^(?:Error|Fatal)\s*:.*$',log,re.M)
            if errors or 'ASIC_SYNTHESIS_FINISHED' not in log:
                record.update(status='FAIL',errors=errors)
                state['status']='FAIL'
                state_path.write_text(json.dumps(state,indent=2))
                raise RuntimeError('Synthesis did not pass log inspection')
        record['status']='PASS'
        state_path.write_text(json.dumps(state,indent=2))
    state['status']='PREPARED' if args.dry_run else 'PASS'
    state['finished_utc']=datetime.now(timezone.utc).isoformat()
    state_path.write_text(json.dumps(state,indent=2))
    print(str(state_path),flush=True)


if __name__=='__main__':
    main()
