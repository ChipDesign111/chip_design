"""Identify the course's native IO/outer-substrate ERC residuals by geometry.

The native ERC report is never edited and ERC Clean is a separate field.
Unknown rules, incomplete markers, or core-region markers require review.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import gdstk


def review(summary, results, gds):
    text=summary.read_text(errors='replace')
    rows={n:(int(h),int(e)) for n,h,e in re.findall(r'(?im)^RULECHECK\s+(\S+)\s+\.+\s+TOTAL Result Count\s*=\s*(\d+)\s*\((\d+)\)',text)}
    total=re.search(r'TOTAL ERC RuleCheck Results Generated:\s*(\d+)\s*\((\d+)\)',text)
    if not rows or not total or any(sum(x[i] for x in rows.values())!=int(total.group(i+1)) for i in [0,1]):
        raise ValueError('Incomplete native ERC summary')
    allowed={'mnpg':{'PVDD1CDG','PVDD2CDG','PVDD2POC'},
             'floating.nxwell_float':{'PVSS1CDG'},'npvss49':{'PVSS1CDG'},
             'floating.psub_float':set()}
    nonzero={n:v for n,v in rows.items() if v[0]}
    errors=['Unknown nonzero ERC rule: '+n for n in nonzero if n not in allowed]
    lines=results.read_text().splitlines();scale=int(lines[0].split()[-1]);polys={n:[] for n in nonzero};rule=None;i=1
    if lines[0].split()[0]!='my_soc_top_postDummy' or scale!=2000:
        raise ValueError('Unexpected ERC top or database units')
    while i<len(lines):
        s=lines[i]
        if s in polys:rule=s
        elif re.match(r'^[A-Za-z_][\w.:-]*$',s):rule=None
        elif rule and re.match(r'^p \d+ \d+$',s):
            count=int(s.split()[2]);xy=[tuple(int(v)/scale for v in a.split()) for a in lines[i+1:i+1+count]]
            if count<3 or len(xy)!=count or any(len(x)!=2 for x in xy):raise ValueError('Incomplete ERC polygon')
            polys[rule].append(xy);i+=count
        i+=1
    lib=gdstk.read_gds(str(gds));top=next(c for c in lib.cells if c.name=='my_soc_top_postDummy')
    core=next(c for c in lib.cells if c.name=='my_soc_top')
    pads=[r for r in core.references if r.cell_name.startswith(('PVD','PVS','PDDW'))]
    envelope=top.bounding_box();markers=[]
    for name,(hier,expanded) in nonzero.items():
        if len(polys[name])!=hier:errors.append('Missing representative marker: '+name)
        for xy in polys[name]:
            box=[[min(p[i] for p in xy) for i in [0,1]],[max(p[i] for p in xy) for i in [0,1]]]
            hits=[]
            for ref in pads:
                b=ref.bounding_box()
                if b and all(b[0][i]<=box[0][i] and box[1][i]<=b[1][i] for i in [0,1]):hits.append(ref.cell_name)
            if name=='floating.psub_float':
                accepted=all(abs(box[k][i]-(envelope[k][i]+(-0.005 if k==0 else 0.005)))<0.00001 for k in [0,1] for i in [0,1])
                reason='Extracted isolated outer substrate enclosing native seal ring'
            else:
                accepted=bool(set(hits)&allowed.get(name,set()))
                reason='Entire representative marker inside measured native protection PAD master'
            if not accepted:errors.append('Marker outside documented native object: '+name)
            markers.append({'rule':name,'bbox_um':box,'native_pad_hits':hits,'accepted_course_residual':accepted,'basis':reason})
    return {'schema':1,'native_erc_hierarchical':int(total.group(1)),'native_erc_expanded':int(total.group(2)),
        'erc_clean':int(total.group(1))==0,'accepted_course_residuals':not errors,'errors':errors,
        'rule_counts':rows,'markers':markers,'native_report_sha256':hashlib.sha256(results.read_bytes()).hexdigest(),
        'reviewer_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'scope':'Course handling of specifically identified native IO and isolated outer-substrate residuals; not a formal foundry waiver or ERC Clean assertion.'}


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('summary',type=Path);p.add_argument('results',type=Path)
    p.add_argument('gds',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
    a.output.write_text(json.dumps(review(a.summary,a.results,a.gds),indent=2)+'\n')
