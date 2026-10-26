#!/usr/bin/env python3
"""Read-only available-library PVT analysis of one completed physical database."""
import argparse,hashlib,json,re,subprocess,sys,tarfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from checks import timing

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,d):p.write_text(json.dumps(d,indent=2)+'\n')
def q(p):
    s=str(p)
    if any(c in s for c in '{}\n'):raise ValueError('Unsafe Tcl path')
    return '{'+s+'}'

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--eda-work',type=Path,required=True);ap.add_argument('--output',type=Path,required=True)
    a=ap.parse_args();work=a.eda_work.resolve();out=a.output.resolve()
    if out.exists():raise ValueError('Choose a new PVT output directory')
    if not (work/'evidence/step_34.json').is_file():raise ValueError('Missing completed physical input')
    out.mkdir(parents=True)
    c=json.loads((work/'config/design.json').read_text());pdk=Path(c['pdk_root'])
    std=pdk/'tcb018gbwp7t_290a/TSMCHOME/digital/Front_End/timing_power_noise/NLDM/tcb018gbwp7t_270a'
    io=pdk/'tpd018nv_280a/TSMCHOME/digital/Front_End/timing_power_noise/NLDM/tpd018nv_280a'
    macro=work/'src/macro/RA1SHD_2048x32M8'
    specs=[('tt','tc','tt_1p8_25C',25,1.8,3.3),('ss','wc','ss_1p62_125C',125,1.62,3.0),
           ('ff0','bc','ff_1p98_0C',0,1.98,3.6),('ffm40','lt','ff_1p98_-40C',-40,1.98,3.6)]
    records={};parts=[]
    for name,suffix,m,temp,vcore,vio in specs:
        libs=[std/('tcb018gbwp7t'+suffix+'.lib'),io/('tpd018nv'+suffix+'.lib'),macro/('RA1SHD_2048x32M8_'+m+'_syn.lib')]
        for p in libs:
            s=p.read_text(errors='replace')[:12000]
            expected=vio if p.parent==io else vcore
            assert abs(float(re.search(r'\bnom_voltage\s*:\s*([-\d.]+)',s).group(1))-expected)<1e-6,p
            assert float(re.search(r'\bnom_temperature\s*:\s*([-\d.]+)',s).group(1))==temp,p
            records[str(p)]=sha(p)
        parts.append('create_library_set -name qa_lib_'+name+' -timing [list '+' '.join(q(p) for p in libs)+']')
        parts.append('create_rc_corner -name qa_rc_'+name+' -temperature '+str(temp)+' -cap_table '+q(pdk/'tcb018gbwp7t_290a/TSMCHOME/digital/Back_End/lef/tcb018gbwp7t_270a/techfiles/captable/t018lo_1p6m_typical.captable'))
        parts.append('create_delay_corner -name qa_delay_'+name+' -library_set qa_lib_'+name+' -rc_corner qa_rc_'+name+' -si_enabled false')
        parts.append('create_analysis_view -name qa_'+name+' -constraint_mode func -delay_corner qa_delay_'+name)
    for p in [work/'evidence/input_manifest.json',work/'evidence/step_34.json',work/'pnr/my_soc_top/backup/step34.enc']:
        records[str(p)]=sha(p)
    save(out/'input_manifest.json',{'eda_work':str(work),'files':records,'available_pvt':specs,'RC_scope':'Same supplied typical captable at each temperature; not foundry min/max RC corners','no_ECO':True})
    driver=out/'pvt.tcl'
    lines=['setMultiCpuUsage -localCpu '+str(c['cpus']),'source '+q(work/'pnr/my_soc_top/backup/step34.enc')]+parts
    views=' '.join('qa_'+x[0] for x in specs)
    lines+=['set_analysis_view -setup {'+views+'} -hold {'+views+'}',
            'set_propagated_clock [get_clocks {sys_clk jtag_clk}]',
            'timeDesign -postRoute -expandedViews -outDir '+q(out/'reports'),
            'timeDesign -postRoute -hold -expandedViews -outDir '+q(out/'reports')]
    for name,*_ in specs:
        lines+=['report_timing -view qa_'+name+' -late -max_paths 5 -path_type full_clock > '+q(out/(name+'_setup.log')),
                'report_timing -view qa_'+name+' -early -max_paths 5 -path_type full_clock > '+q(out/(name+'_hold.log'))]
    lines+=['puts PVT_REPORTED_NO_ECO','exit 0'];driver.write_text('\n'.join(lines)+'\n')
    command=['innovus','-batch','-files',str(driver),'-log',str(out/'pvt')];save(out/'command.json',command)
    with (out/'tool.log').open('w') as f:code=subprocess.call(command,cwd=str(out),stdout=f,stderr=subprocess.STDOUT)
    if code or 'PVT_REPORTED_NO_ECO' not in (out/'tool.log').read_text():raise RuntimeError('Read-only PVT tool failed')
    results={}
    for name,*_ in specs:results[name]=timing(out/'reports'/('qa_'+name),require_clean=False)
    for path,h in records.items():
        if sha(Path(path))!=h:raise RuntimeError('Original input changed: '+path)
    result={'analysis_complete':True,'all_available_pvt_passed':all(x['targets_met'] for v in results.values() for x in v.values()),
            'views':results,'original_inputs_unchanged':True,'scope':'Available matched TT/SS/FF0/FF-40 libraries; same typical RC technology. Not full foundry RC/SI/IR/EM/LVS signoff'}
    save(out/'results.json',result)
    files={str(p.relative_to(out)):sha(p) for p in out.rglob('*') if p.is_file() and (p.suffix in ['.json','.tcl','.log'] or p.name.endswith('.summary.gz')) and p.stat().st_size<25000000}
    with tarfile.open(out/'review.tar.gz','w:gz') as t:
        for n in sorted(files):t.add(out/n,arcname=n,recursive=False)
    save(out/'review_manifest.json',{'archive_sha256':sha(out/'review.tar.gz'),'files':files,'remote_root':str(out)})
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
