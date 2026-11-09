"""Passively profile existing full-SoC benchmark firmware on unchanged RTL."""
import argparse
import json
from pathlib import Path
import re
import shutil

from run_soc_xcelium import ROOT, FIELDS, PASS_RE, execute, sha, source_hashes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bench', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--mode', action='append', required=True)
    parser.add_argument('--seed', action='append', type=int)
    parser.add_argument('--timeout', type=int, default=600)
    args = parser.parse_args()
    xrun = shutil.which('xrun')
    if not xrun:
        parser.error('xrun not found; load the EDA environment first')
    bench = args.bench.resolve()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    build = out / 'build'
    build.mkdir()
    sources = []
    for line in (ROOT / 'rtl/filelist.f').read_text().splitlines():
        line = line.strip()
        if not line or line.startswith('//'):
            continue
        sources.append('+incdir+' + str(ROOT / line[8:]) if line.startswith('+incdir+') else str(ROOT / line))
    sources.extend(['+incdir+' + str(ROOT / 'test/int8'), str(ROOT / 'test/int8/tb_soc_profile.sv')])
    filelist = build / 'sources.f'
    filelist.write_text('\n'.join(sources) + '\n')
    snapshot = build / 'xcelium.d'
    source_manifest = source_hashes()
    source_manifest['test/int8/tb_soc_profile.sv'] = sha(ROOT / 'test/int8/tb_soc_profile.sv')
    source_manifest['test/int8/run_firmware_profile.py'] = sha(Path(__file__))
    report = {
        'status': 'RUNNING', 'source_sha256': source_manifest, 'cases': [],
        'scope': 'Unmodified tb_soc plus passive monitor; real start/done/SRAM acceptance boundaries',
        'instruction_count': 'Existing CV32E40P minstret event, not fetch requests; the core implements this event at legal ID issue with architectural retirement-count semantics',
        'event_phase_rule': 'Events are assigned to wall-clock windows, not reconstructed retired-PC attribution',
        'cycle_rule': 'setup + npu + post_npu = elapsed; post_npu includes finishing poll, golden checks and statistics publication',
        'load_use_rule': 'Existing CPU load-use event counts hazard occurrences, not every stalled cycle',
    }

    def save():
        (out / 'results.json').write_text(json.dumps(report, indent=2) + '\n')

    try:
        _, elapsed = execute([xrun, '-64bit', '-sv', '-timescale', '1ns/1ps',
                              '-f', str(filelist), '-top', 'tb_soc_profile', '-elaborate',
                              '-xmlibdirname', str(snapshot), '-l', str(build / 'xrun.log'),
                              '+notimingchecks', '-nospecify'], build, args.timeout)
        report['compile_seconds'] = elapsed
        save()
        for mode in args.mode:
            for seed in args.seed or [0, 1, 2, 10000]:
                original = bench / mode / ('seed_' + str(seed))
                case = out / mode / ('seed_' + str(seed))
                case.mkdir(parents=True)
                for name in ('firmware.hex', 'firmware.S', 'firmware_meta.json'):
                    shutil.copyfile(original / name, case / name)
                text, elapsed = execute([xrun, '-64bit', '-R', '-xmlibdirname', str(snapshot),
                                         '-l', str(case / 'xrun.log')], case, args.timeout)
                functional = PASS_RE.search(text)
                profile = re.search(r'^INT8_PROFILE (.+)$', text, re.M)
                if not functional or not profile:
                    raise RuntimeError('Missing functional PASS or profile: ' + str(case))
                fields = dict((k, int(v)) for k, v in re.findall(r'(\w+)=(\d+)', profile.group(1)))
                if fields['setup_cycles'] + fields['npu_cycles'] + fields['post_npu_cycles'] != fields['elapsed_cycles']:
                    raise RuntimeError('Profile intervals do not add up')
                baseline_log = (original / 'console.log').read_text(errors='replace') if (original / 'console.log').exists() else ''
                previous = PASS_RE.search(baseline_log)
                if previous and previous.groups() != functional.groups():
                    raise RuntimeError('Passive monitor changed functional run: ' + str(case))
                report['cases'].append({
                    'mode': mode, 'seed': seed, 'profile': fields,
                    'functional': dict(zip(FIELDS, map(int, functional.groups()))),
                    'matches_original_benchmark': bool(previous),
                    'firmware_sha256': sha(case / 'firmware.hex'), 'wall_seconds': elapsed,
                })
                save()
                print(mode, seed, fields, flush=True)
        report['status'] = 'PASS'
    except Exception as exc:
        report['status'] = 'FAIL'
        report['error'] = str(exc)
        raise
    finally:
        save()


if __name__ == '__main__':
    main()
