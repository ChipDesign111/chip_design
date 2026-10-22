#!/usr/bin/env python3
"""Current project entry points; deployment is independently managed by eda/remote.py."""
import argparse,json,shutil,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser();s=p.add_subparsers(dest='command',required=True)
    s.add_parser('doctor');s.add_parser('check');t=s.add_parser('test');t.add_argument('--soc',action='store_true');t.add_argument('--vsim',default='vsim');t.add_argument('--count',type=int,default=32)
    a=p.parse_args()
    if a.command=='doctor':
        print(json.dumps({'python':sys.version.split()[0],'tools':{n:shutil.which(n) for n in ['iverilog','vvp','vsim','ssh','scp']},'rtl_test':'Icarus; full SoC additionally ModelSim','EDA':'run eda/remote.py; Genus/Innovus/PDK live on chipdesign'},indent=2));return 0
    if a.command=='check':
        for name in ['check_repo.py','check_hardware.py']:subprocess.run([sys.executable,str(ROOT/'tools'/name)],cwd=ROOT,check=True)
        return 0
    cmd=[sys.executable,str(ROOT/'test/int8/run.py'),'--count',str(a.count),'--trained']
    if a.soc:cmd+=['--soc','--vsim',a.vsim]
    return subprocess.run(cmd,cwd=ROOT).returncode
if __name__=='__main__':raise SystemExit(main())
