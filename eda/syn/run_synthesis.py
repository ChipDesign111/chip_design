"""Run a reproducible TSMC180 Genus synthesis (Python 3.8+).

Licensed libraries remain external and are never copied into the repository.
"""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tq(value):
    value = str(value)
    if any(c in value for c in '{}\r\n'):
        raise ValueError('Unsupported Tcl path: ' + value)
    return '{' + value + '}'


def source_revision():
    try:
        revision = subprocess.check_output(['git','rev-parse','HEAD'],cwd=str(ROOT),stderr=subprocess.DEVNULL).decode().strip()
        dirty = subprocess.call(['git','diff','--quiet','HEAD','--','rtl'],cwd=str(ROOT))
        return revision + ('+working-tree' if dirty else '')
    except (OSError,subprocess.CalledProcessError):
        return 'unversioned; exact inputs recorded by SHA-256'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', type=Path, default=ROOT/'eda/work/synthesis')
    ap.add_argument('--pdk', type=Path, default=Path(os.environ.get('CHIP_PDK_ROOT', '/lec/pdk/tsmc180')))
    ap.add_argument('--sram', type=Path, default=Path(os.environ.get('CHIP_SRAM_ROOT', '/lec/lab4/soc_cv32e40p_template_pnr-stu/src/macro/RA1SHD_2048x32M8')))
    ap.add_argument('--genus', default='genus')
    ap.add_argument('--cpus', type=int, default=8)
    ap.add_argument('--source-revision', help='Source label for archive-based runs without .git; exact input hashes are always recorded')
    args = ap.parse_args()
    out = args.out.resolve()
    if (out/'console.log').exists():
        raise RuntimeError('Existing synthesis evidence: choose a fresh --out directory')
    out.mkdir(parents=True, exist_ok=True)
    std = args.pdk/'tcb018gbwp7t_290a/TSMCHOME/digital'
    lib = std/'Front_End/timing_power_noise/NLDM/tcb018gbwp7t_270a/tcb018gbwp7ttc.lib'
    sram_lib = args.sram/'RA1SHD_2048x32M8_tt_1p8_25C_syn.lib'
    lef = std/'Back_End/lef/tcb018gbwp7t_270a/lef/tcb018gbwp7t_6lm.lef'
    cap = std/'Back_End/lef/tcb018gbwp7t_270a/techfiles/captable/t018lo_1p6m_typical.captable'
    macro_lefs = [args.sram/'RA1SHD_2048x32M8.vclef', args.sram/'RA1SHD_2048x32M8_ant.lef']
    inputs = [lib,sram_lib,lef,cap]+macro_lefs
    for p in inputs:
        if not p.is_file():
            raise FileNotFoundError(str(p))
    files = []
    lines = ['+define+SYNTHESIS', '+define+CHIP_USE_RA1SHD']
    for entry in (ROOT/'rtl/filelist.f').read_text().splitlines():
        entry = entry.strip()
        if not entry or entry.startswith('//'):
            continue
        if entry.startswith('+incdir+'):
            lines.append('+incdir+'+str(ROOT/entry[8:]))
        else:
            p = ROOT/entry
            if not p.is_file():
                raise FileNotFoundError(str(p))
            files.append(p)
            lines.append(str(p))
    (out/'rtl.f').write_text('\n'.join(lines)+'\n')
    # Includes/macros affect elaboration even when absent from the .sv filelist.
    source_inputs = sorted(p for p in (ROOT/'rtl').rglob('*') if p.is_file())
    config = [
        'set design_root '+tq(ROOT), 'set output_root '+tq(out),
        'set script_root '+tq(SCRIPTS),
        'set std_lib '+tq(lib), 'set sram_lib '+tq(sram_lib),
        'set captable '+tq(cap),
        'set lef_files [list '+' '.join(tq(p) for p in [lef]+macro_lefs)+']',
        'set cpu_count '+str(args.cpus),
    ]
    (out/'run_config.tcl').write_text('\n'.join(config)+'\n')
    manifest = {
        'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'source_revision':args.source_revision or source_revision(),
        'scope':'complete CPU+DMA+NPU SoC, TT 1.8V 25C, 20ns system clock',
        'defines':['SYNTHESIS','CHIP_USE_RA1SHD'],
        'source_sha256':{p.relative_to(ROOT).as_posix():sha(p) for p in source_inputs},
        'compiled_source_files':[p.relative_to(ROOT).as_posix() for p in files],
        'flow_sha256':{p.relative_to(ROOT).as_posix():sha(p) for p in SCRIPTS.glob('*') if p.is_file()},
        'library_sha256':{str(p):sha(p) for p in inputs},
        'memory_mapping':'one RA1SHD main SRAM; NPU banks mapped to standard cells',
    }
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2))
    cmd = [args.genus,'-no_gui','-abort_on_error','-f',str(SCRIPTS/'genus.tcl'),'-log','genus']
    with (out/'console.log').open('w') as log:
        result = subprocess.run(cmd,cwd=str(out),stdout=log,stderr=subprocess.STDOUT)
    manifest['exit_code'] = result.returncode
    manifest['finished_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    for p in source_inputs:
        if sha(p)!=manifest['source_sha256'][p.relative_to(ROOT).as_posix()]:
            raise RuntimeError('RTL changed during synthesis: '+str(p))
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2))
    print('Genus exit code: '+str(result.returncode),flush=True)
    raise SystemExit(result.returncode)


if __name__=='__main__':
    main()
