"""Compare matched legacy cases and reject a cycle regression above a limit."""
import argparse,json,re
from pathlib import Path

def compare(baseline,candidate,limit=0.05):
    pattern=r'CASE (\d+) PASS cycles=(\d+) fc1=(\d+) fc2=(\d+)'
    def cases(root):return {int(i):tuple(map(int,(c,f1,f2))) for i,c,f1,f2 in re.findall(pattern,(root/'unit.log').read_text())}
    before,after=cases(baseline),cases(candidate)
    if not before or before.keys()!=after.keys():raise ValueError('Unmatched test cases')
    worst=max(after[i][0]/before[i][0]-1 for i in before)
    for i in before:
        if after[i][1:]!=before[i][1:]:raise ValueError('Legacy ISSUE count changed')
    old=json.loads((baseline/'result.json').read_text())['soc_timing']
    new=json.loads((candidate/'result.json').read_text())['soc_timing']
    if not old or not new:raise ValueError('Full SoC timing required')
    soc=new['observed_cycles']/old['observed_cycles']-1
    if max(worst,soc)>limit:raise ValueError('Cycle regression exceeds acceptance limit')
    return dict(passed=True,matched_cases=len(before),unchanged_cases=sum(before[i]==after[i] for i in before),
                max_unit_regression=worst,soc_before=old,soc_after=new,soc_regression=soc,limit=limit)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('baseline',type=Path);p.add_argument('candidate',type=Path)
    p.add_argument('--limit',type=float,default=0.05);a=p.parse_args()
    print(json.dumps(compare(a.baseline,a.candidate,a.limit),indent=2))
