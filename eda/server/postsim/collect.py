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
    inputs=json.loads((root/'input_manifest.json').read_text())
    engine=inputs.get('simulator','vcs');compile=(root/'build/compile.log').read_text(errors='replace')
    failed_negative=0;unmatched_paths=0
    if engine=='vcs':
        warnings=dict(collections.Counter(re.findall(r'Warning-\[([^]]+)\]',sdf)))
        totals=re.findall(r'Total errors:\s*(\d+)',sdf)
        if len(totals)!=1:raise ValueError('Missing/ambiguous SDF annotation totals')
        error_count=int(totals[0]);clamped=warnings.get('SDFCOM_NIOD',0)
    else:
        warnings=dict(collections.Counter(re.findall(r'\*W,([A-Z0-9]+)',compile)))
        error_count=len(re.findall(r'\*[EF],',compile))
        matched=re.search(r'Number of negative path delay that failed to adjust:\s*(\d+)',compile)
        failed_negative=int(matched.group(1)) if matched else 0
        unmatched_paths=warnings.get('SDFNEP',0)
        clamped=warnings.get('SDFNDP',0)
    summary={'audit_tool_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
             'simulator':engine,'annotation_errors':error_count,'warning_categories':warnings,
             'negative_timing_checks_enabled':True,'native_NTC_RECREM_enabled':True,
             'negative_iopath_clamped_by_simulator':clamped,
             'negative_paths_failed_to_adjust':failed_negative,
             'unmatched_paths_printed_lower_bound':unmatched_paths,
             'warning_counts_are_printed_messages_not_uncapped_totals':engine=='xcelium',
             'missing_instances':warnings.get('SDFCOM_CFIIS',0)+warnings.get('SDFINF',0),
             'unmatched_timing_checks':warnings.get('SDFCOM_CFTC',0)+warnings.get('SDFNET',0),'cases':{}}
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
        reported=len(re.findall(r'Timing violation',text,re.I))
        if reported!=len(violations):raise ValueError('Unparsed timing violations; cannot claim clean: '+mode.name)
    summary['binding_complete_for_instances_and_checks']=not (error_count or summary['missing_instances'] or summary['unmatched_timing_checks'] or unmatched_paths)
    summary['negative_path_delay_support_complete']=not (clamped or failed_negative)
    summary['raw_annotation_warnings_retained']=True
    summary['active_window_dynamic_timing_clean']=all(not x['timing_counts'].get('active',0) for x in summary['cases'].values())
    summary['normal_acceptance']={
        'functional_pass':bool(summary['cases']) and all(x['functional_pass'] for x in summary['cases'].values()),
        'sdf_binding_complete':summary['binding_complete_for_instances_and_checks'],
        'dynamic_timing_clean':bool(summary['cases']) and all(not x['timing_violations'] for x in summary['cases'].values()),
        'warnings_are_reported_not_required_to_be_zero':True}
    summary['normal_postsim_pass']=all(summary['normal_acceptance'][k] for k in ['functional_pass','sdf_binding_complete','dynamic_timing_clean'])
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
        if relative.as_posix()=='review_manifest.json':continue
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
