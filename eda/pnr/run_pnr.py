#!/usr/bin/env python3
"""Run resumable, recorded Innovus stages for the accepted complete SoC netlist."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
STAGES = ('init', 'floorplan', 'io', 'power', 'place', 'cts', 'route', 'finish', 'export')


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(1048576), b''):
            h.update(chunk)
    return h.hexdigest()


def physical_materials(env):
    """Inventory is cross-checked against config.tcl's actual exported list."""
    pdk = Path(env.get('CHIP_PNR_PDK', '/lec/pdk/tsmc180'))
    sram = Path(env.get('CHIP_PNR_SRAM', '/lec/lab4/soc_cv32e40p_template_pnr-stu/src/macro/RA1SHD_2048x32M8'))
    std = pdk/'tcb018gbwp7t_290a/TSMCHOME/digital'
    io = pdk/'tpd018nv_280a/TSMCHOME/digital'
    bond = pdk/'tpb018v_180a/TSMCHOME/digital'
    tech = std/'Back_End/lef/tcb018gbwp7t_270a'
    return [std/'Front_End/timing_power_noise/NLDM/tcb018gbwp7t_270a/tcb018gbwp7ttc.lib',
            io/'Front_End/timing_power_noise/NLDM/tpd018nv_280a/tpd018nvtc.lib',
            sram/'RA1SHD_2048x32M8_tt_1p8_25C_syn.lib',
            tech/'techfiles/captable/t018lo_1p6m_typical.captable', tech/'techfiles/gds2.map',
            tech/'lef/tcb018gbwp7t_6lm.lef',
            io/'Back_End/lef/tpd018nv_280a/mt_2/6lm/lef/tpd018nv_6lm.lef',
            io/'Back_End/lef/tpd018nv_280a/mt_2/6lm/lef/antenna_6lm.lef',
            bond/'Back_End/lef/tpb018v_180a/cup/6lm/lef/tpb018v_6lm.lef',
            sram/'RA1SHD_2048x32M8.vclef', sram/'RA1SHD_2048x32M8_ant.lef',
            std/'Back_End/gds/tcb018gbwp7t_270a/tcb018gbwp7t.gds',
            sram/'RA1SHD_2048x32M8.gds',
            io/'Back_End/gds/tpd018nv_280a/mt_2/6lm/tpd018nv.gds',
            bond/'Back_End/gds/tpb018v_180a/cup/6lm/tpb018v.gds']


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--synthesis', type=Path, default=ROOT/'eda/work/asic-resetfall/synthesis')
    ap.add_argument('--stages', nargs='+', choices=STAGES, default=list(STAGES))
    ap.add_argument('--resume', type=Path)
    ap.add_argument('--die-size', type=float, default=3400.32, help='Initial square die edge in micrometres')
    ap.add_argument('--cpus', type=int, default=8)
    ap.add_argument('--innovus', default='innovus')
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()
    if args.cpus < 1 or args.die_size < 1800:
        ap.error('Invalid CPU count or die edge')
    if len(args.stages) != len(set(args.stages)) or sorted(args.stages, key=STAGES.index) != args.stages:
        ap.error('Stages must be unique and in flow order')
    if args.stages[0] != 'init' and not args.resume:
        ap.error('A later stage requires --resume pointing at its predecessor checkpoint')
    if args.resume and 'init' in args.stages:
        ap.error('Do not reinitialize an already restored design')
    out = args.out.resolve()
    syn = args.synthesis.resolve()
    netlist = syn/'outputs/my_soc_top_postsyn.v'
    sdc = syn/'outputs/my_soc_top.sdc'
    accepted = syn.parent/'verification-final.json'
    verification = json.loads(accepted.read_text())
    if verification.get('status') != 'PASS':
        raise RuntimeError('Input complete-SoC synthesis and simulation audit is not PASS')
    syn_manifest = json.loads((syn/'manifest.json').read_text())
    # Independently bind the actual netlist/SDC to the accepted synthesis export.
    for path in (netlist, sdc):
        if not path.is_file():
            raise RuntimeError('Missing synthesis output: '+str(path))
        if digest(path) != verification['synthesis']['outputs'][path.name]['sha256']:
            raise RuntimeError('Accepted synthesis output hash mismatch: '+str(path))
    if args.resume and not args.resume.resolve().exists():
        raise RuntimeError('Missing resume checkpoint')
    for name in args.stages:
        if not (HERE/(name+'.tcl')).is_file():
            raise RuntimeError('Missing stage script: '+name)
    out.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env.update(CHIP_PNR_OUTPUT=str(out), CHIP_PNR_SYNTHESIS=str(syn),
               CHIP_PNR_DIE_SIZE=str(args.die_size), CHIP_PNR_CPUS=str(args.cpus))
    material_files = physical_materials(env)
    identity = {'source_revision': syn_manifest['source_revision'],
                'netlist_sha256': digest(netlist), 'sdc_sha256': digest(sdc),
                'verification_sha256': digest(accepted), 'die_size_um': args.die_size,
                'material_sha256': {str(p): digest(p) for p in material_files}}
    identity_file = out/'input_identity.json'
    if identity_file.exists() and json.loads(identity_file.read_text()) != identity:
        raise RuntimeError('Existing output directory belongs to different input data')
    identity_file.write_text(json.dumps(identity, indent=2)+'\n')
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    inv = out/'invocations'/(stamp+'-'+args.stages[0])
    inv.mkdir(parents=True)
    script_records = {}
    for path in sorted(HERE.rglob('*')):
        if path.is_file() and path.suffix in ('.tcl', '.py', '.json', '.md') and '__pycache__' not in path.parts:
            data = path.read_bytes()
            saved = inv/'source'/path.relative_to(HERE)
            saved.parent.mkdir(parents=True, exist_ok=True)
            saved.write_bytes(data)
            script_records[str(path.relative_to(ROOT))] = hashlib.sha256(data).hexdigest()
    env.update(CHIP_PNR_INVOCATION=stamp, CHIP_PNR_STAGES=' '.join(args.stages),
               CHIP_PNR_RESUME=str(args.resume.resolve()) if args.resume else '')
    command = [args.innovus, '-no_gui', '-init', str(HERE/'main.tcl'),
               '-log', str(inv/'innovus')]
    record = {'started_utc': datetime.now(timezone.utc).isoformat(), 'command': command,
              'identity': identity, 'stages': args.stages,
              'resume': str(args.resume.resolve()) if args.resume else None,
              'scripts_sha256': script_records,
              'status': 'PREPARED' if args.dry_run else 'RUNNING'}
    state = inv/'manifest.json'
    state.write_text(json.dumps(record, indent=2)+'\n')
    print(str(inv), flush=True)
    if args.dry_run:
        return 0
    with (inv/'console.log').open('wb') as console:
        process = subprocess.run(command, cwd=str(out), env=env,
                                 stdin=subprocess.DEVNULL, stdout=console, stderr=subprocess.STDOUT)
    text = (inv/'console.log').read_text(errors='replace')
    inventory_path = out/'actual_material_inputs.txt'
    used_materials = [Path(line) for line in inventory_path.read_text().splitlines()] if inventory_path.exists() else []
    completed = re.findall(r'^PNR_STAGE_COMPLETE (\w+)\s*$', text, re.M)
    errors = re.findall(r'^.*(?:\*\*ERROR|PNR_STAGE_FAILED|FATAL).*$', text, re.M)
    if set(used_materials) != set(material_files):
        errors.append('Tcl/Python physical input inventories differ or actual inventory was not produced')
    dependencies = ['config', 'settings', 'mmmc', 'main']+args.stages
    if (HERE/'geometry_helpers.tcl').is_file():
        dependencies.append('geometry_helpers')
    for name in dependencies:
        path = HERE/(name+'.tcl')
        if digest(path) != script_records[str(path.relative_to(ROOT))]:
            errors.append('Executed Tcl changed while Innovus was running: '+str(path))
    for path in material_files:
        if digest(path) != identity['material_sha256'][str(path)]:
            errors.append('Physical library changed while Innovus was running: '+str(path))
    ok = process.returncode == 0 and completed == args.stages and 'PNR_INVOCATION_COMPLETE' in text and not errors
    record.update(status='COMPLETED' if ok else 'FAIL', exit_code=process.returncode,
                  completed_stages=completed, errors=errors,
                  finished_utc=datetime.now(timezone.utc).isoformat(),
                  note='Tool execution complete is not a physical/timing verification PASS')
    state.write_text(json.dumps(record, indent=2)+'\n')
    print(json.dumps({'status': record['status'], 'manifest': str(state)}, indent=2), flush=True)
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
