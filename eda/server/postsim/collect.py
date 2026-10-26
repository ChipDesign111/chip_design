#!/usr/bin/env python3
"""Collect bounded simulation evidence without licensed models or large views."""
from pathlib import Path
import collections
import hashlib
import json
import re
import sys
import tarfile

def audit(root):
    sdf=(root/'build/sdf.log').read_text(errors='replace')
    warnings=dict(collections.Counter(re.findall(r'Warning-\[([^]]+)\]',sdf)))
    totals=re.findall(r'Total errors:\s*(\d+)',sdf)
    if len(totals)!=1:raise ValueError('Missing/ambiguous SDF annotation totals')
    error_count=int(totals[0])
    summary={'annotation_errors':error_count,'warning_categories':warnings,
             'negative_timing_checks_enabled':True,'native_NTC_RECREM_enabled':True,
             'negative_iopath_clamped_by_simulator':warnings.get('SDFCOM_NIOD',0),
             'missing_instances':warnings.get('SDFCOM_CFIIS',0),
             'unmatched_timing_checks':warnings.get('SDFCOM_CFTC',0),'cases':{}}
    for mode in sorted(root.glob('sdf_*')):
        if not mode.is_dir():continue
        text=(mode/'simulation.log').read_text(errors='replace')
        start=float(re.search(r'ACTIVE_START time_ns=([\d.]+)',text).group(1))
        end=float(re.search(r'ACTIVE_END time_ns=([\d.]+)',text).group(1))
        violations=[]
        for m in re.finditer(r'Timing violation in (.*?)\n\s*(\$\w+\(.*?;)',text,re.S):
            times=[int(x)/1000 for x in re.findall(r':(\d+)',m[2])]
            if not times:raise ValueError('Cannot classify timing event')
            time=max(times);phase='initial_reset' if time<start else 'final_reset' if time>=end else 'active'
            violations.append({'instance':m[1].strip(),'time_ns':time,'phase':phase,'check':m[2].strip()})
        values=re.search(r'FUNCTIONAL_PASS cycles=(\d+) npu_cycles=(\d+) dma_mac_overlap=(\d+) read_overlap=(\d+) write_overlap=(\d+)',text)
        if not values or 'POSTSIM_DONE' not in text:raise ValueError('Incomplete functional run')
        clocks=[float(x) for x in re.findall(r'CLOCK_AT_CORE time_ns=([\d.]+)',text)]
        summary['cases'][mode.name]={'functional_pass':True,
            **dict(zip(['observed_cpu_cycles','npu_cycles','dma_mac_overlap','read_overlap','write_overlap'],map(int,values.groups()))),
            'active_start_ns':start,'active_end_ns':end,'clock_core_edges_ns':clocks,
            'timing_counts':dict(collections.Counter(x['phase'] for x in violations)),
            'timing_violations':violations}
    summary['binding_complete_for_instances_and_checks']=not (error_count or summary['missing_instances'] or summary['unmatched_timing_checks'])
    summary['active_window_dynamic_timing_clean']=all(not x['timing_counts'].get('active',0) for x in summary['cases'].values())
    summary['scope']='Full notifier/message checking in all SDF runs; reset events retained, not masked. Unsupported negative IOPATH clamps remain explicit; not complete signoff.'
    (root/'audit.json').write_text(json.dumps(summary,indent=2)+'\n')
    return summary

def main():
    root=Path(sys.argv[1]).resolve()
    if not (root/'results.json').is_file():raise ValueError('Simulation matrix not complete')
    audit(root)
    files={}
    for q in root.rglob('*'):
        if not q.is_file():continue
        relative=q.relative_to(root)
        if any(x in relative.parts for x in ['csrc','simv.daidir','inputs','objs']):continue
        if q.suffix in ['.json','.log','.tcl'] and q.stat().st_size<25*1024*1024:
            files[relative.as_posix()]=hashlib.sha256(q.read_bytes()).hexdigest()
    archive=root/'review.tar.gz'
    with tarfile.open(str(archive),'w:gz') as tar:
        for name in sorted(files):tar.add(str(root/name),arcname=name,recursive=False)
    manifest={'archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'files':files,'remote_root':str(root),
              'excludes':'Licensed models, netlist/SDF, binaries, compilation databases and large logs remain server-side'}
    (root/'review_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({'archive':str(archive),'files':len(files),'bytes':archive.stat().st_size}))

if __name__=='__main__':main()
