"""Collect measured PVT paths and aggregate tool summaries without inventing TNS."""
from pathlib import Path
import gzip,hashlib,json,re,tarfile
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def text(p):return gzip.decompress(p.read_bytes()).decode(errors='replace') if p.suffix=='.gz' else p.read_text(errors='replace')
def collect(out):
    out=Path(out);inputs=json.loads((out/'input_manifest.json').read_text())
    if 'PVT_REPORTED_NO_ECO' not in (out/'tool.log').read_text():raise ValueError('PVT command sequence did not finish')
    views={}
    for spec in inputs['available_pvt']:
        name=spec[0];views[name]={}
        for mode in ['setup','hold']:
            p=out/(name+'_'+mode+'.log');body=text(p)
            values=[float(x) for x in re.findall(r'Slack Time\s+([-\d.]+)',body)]
            if not values or 'Analysis View: qa_'+name not in body:raise ValueError('Missing/wrong-view timing path: '+str(p))
            views[name][mode]={'wns_ns':min(values),'worst_paths_reported':len(values),'report':str(p),'tns_ns':None,'violating_path_count':None,'nonnegative':min(values)>=0}
    aggregate={}
    for p in (out/'reports').glob('*.summary*'):
        s=text(p);mode='hold' if 'Hold mode' in s else 'setup' if 'Setup mode' in s else None
        if mode is None:continue
        fields=[re.search(x,s) for x in [r'WNS \(ns\):\|\s*([-\d.]+)',r'TNS \(ns\):\|\s*([-\d.]+)',r'Violating Paths:\|\s*(\d+)']]
        if not all(fields) or mode in aggregate:raise ValueError('Invalid aggregate summary')
        aggregate[mode]={'wns_ns':float(fields[0][1]),'tns_ns':float(fields[1][1]),'violating_paths':int(fields[2][1]),'report':str(p)}
    if set(aggregate)!={'setup','hold'}:raise ValueError('Missing aggregate setup/hold summary')
    for mode in aggregate:
        worst=min(v[mode]['wns_ns'] for v in views.values())
        if abs(worst-aggregate[mode]['wns_ns'])>.002:raise ValueError('Aggregate and individual views disagree')
    for path,h in inputs['files'].items():
        if sha(Path(path))!=h:raise ValueError('Original input changed: '+path)
    result={'analysis_complete':True,'all_available_pvt_passed':all(v[mode]['nonnegative'] for v in views.values() for mode in v),
            'views':views,'aggregate':aggregate,'original_inputs_unchanged':True,'collector_sha256':sha(Path(__file__)),
            'scope':'Matched TT/SS125/FF0/FF-40 library WNS and aggregate TNS/path counts; per-view TNS not separately reported; same typical RC technology, not full foundry RC/SI/IR/EM/LVS signoff'}
    (out/'results.json').write_text(json.dumps(result,indent=2)+'\n')
    files={str(p.relative_to(out)):sha(p) for p in out.rglob('*') if p.is_file() and p.name!='review_manifest.json' and (p.suffix in ['.json','.tcl','.log'] or p.name.endswith('.summary.gz')) and p.stat().st_size<25000000}
    with tarfile.open(out/'review.tar.gz','w:gz') as t:
        for n in sorted(files):t.add(out/n,arcname=n,recursive=False)
    (out/'review_manifest.json').write_text(json.dumps({'archive_sha256':sha(out/'review.tar.gz'),'files':files,'remote_root':str(out)},indent=2)+'\n')
    return result
if __name__=='__main__':
    import sys
    print(json.dumps(collect(Path(sys.argv[1])),indent=2))
