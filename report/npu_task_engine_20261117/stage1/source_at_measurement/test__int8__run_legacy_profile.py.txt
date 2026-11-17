"""Passive state/traffic baseline for an unchanged frozen legacy firmware image."""
import argparse, hashlib, json, re, shutil, sys
from datetime import datetime
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from compiler.profiling import monitor_source,summarize
from compiler.sim import execute


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--firmware',type=Path,required=True)
    p.add_argument('--vsim',default='vsim')
    args=p.parse_args()
    out=ROOT/'test/int8/runs'/('legacy_profile_'+datetime.now().strftime('%Y%m%d_%H%M%S'))
    out.mkdir()
    shutil.copyfile(args.firmware,out/'firmware.hex')
    tb=(ROOT/'test/int8/tb_soc.sv').read_text().replace('module tb_soc;','module tb_legacy_profile;')
    tb=tb.replace('    integer i;',monitor_source()+'\n    integer i;')
    (out/'tb_legacy_profile.sv').write_text(tb)
    sources=[]
    for line in (ROOT/'rtl/filelist.f').read_text().splitlines():
        if line.startswith('+incdir+'):sources.append('+incdir+'+(ROOT/line[8:]).as_posix())
        elif line.strip():sources.append((ROOT/line).as_posix())
    sources.append((out/'tb_legacy_profile.sv').as_posix())
    (out/'soc.f').write_text('\n'.join(sources)+'\n')
    (out/'soc.do').write_text('\n'.join(['onerror {quit -code 1}','onbreak {resume}',
        'vlib work','vmap work {'+(out/'work').as_posix()+'}','vlog -sv -f soc.f',
        'vsim -suppress 12110 -novopt -onfinish stop work.tb_legacy_profile','run -all',
        'set status [examine -radix hex /tb_legacy_profile/magic]',
        'if {![string equal -nocase $status c0dec0de]} {quit -code 3}','quit -code 0'])+'\n')
    log=execute([args.vsim,'-c','-do','soc.do'],out,'soc','INT8_SOC PASS')
    (out/'manifest.json').write_text(json.dumps(dict(tensors={},profile_ranges=[])))
    profile=summarize(out)
    values={k:int(v) for k,v in re.findall(r'\b(cycles|hw_soc_cycles|npu_cycles)=(\d+)',log)}
    assert values['cycles']==2700 and values['hw_soc_cycles']==profile['observed_edges']==2695
    assert sum(profile['npu_state_cycles'].values())==values['npu_cycles']==952
    result=dict(passed=True,firmware_source=str(args.firmware.resolve()),
        firmware_sha256=hashlib.sha256((out/'firmware.hex').read_bytes()).hexdigest(),
        values=values,profile=profile)
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print('LEGACY_PROFILE_PASS '+str(out))


if __name__=='__main__':main()
