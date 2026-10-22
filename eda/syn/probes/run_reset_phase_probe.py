"""Compare posedge-only and negedge-release reset with real-cell MAX SDF."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess


def run(command, cwd, log, env=None):
    with log.open('w') as output:
        process = subprocess.run(command, cwd=str(cwd), env=env, stdout=output, stderr=subprocess.STDOUT)
    if process.returncode:
        raise RuntimeError('Command failed: ' + str(log))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--library', type=Path, required=True)
    args = parser.parse_args()
    scripts = Path(__file__).resolve().parent
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    records = []
    for name in ('posedge_only', 'negedge_release'):
        work = out / name
        work.mkdir()
        flags = '+define+NEGEDGE_RELEASE\n' if name == 'negedge_release' else ''
        (work / 'probe.f').write_text(flags + str(scripts / 'reset_phase_probe.sv') + '\n')
        env = dict(os.environ, PROBE_CONFIG=str(args.config.resolve()))
        run(['genus', '-no_gui', '-abort_on_error', '-f', str(scripts / 'reset_phase_genus.tcl'), '-log', 'genus'], work, work / 'synthesis_console.log', env)
        run(['xmsdfc', '-64bit', 'mapped.sdf', '-output', 'mapped.sdf.X'], work, work / 'sdf_compile.log')
        (work / 'sdf.cmd').write_text('COMPILED_SDF_FILE = "' + str(work / 'mapped.sdf.X') + '",\nSCOPE = reset_phase_tb.dut,\nLOG_FILE = "' + str(work / 'sdf_annotation.log') + '",\nMTM_CONTROL = "MAXIMUM";\n')
        cmd = ['xrun', '-64bit', '-sv', '-timescale', '1ns/1ps', str(work / 'mapped.v'), str(args.library.resolve()),
               str(scripts / 'reset_phase_tb.sv'), '-top', 'reset_phase_tb', '+define+NTC+RECREM', '-negdelay',
               '-sdf_cmd_file', 'sdf.cmd', '-sdfstats', 'sdf_unannotated.log', '-l', 'xrun.log']
        run(cmd, work, work / 'simulation_console.log')
        text = (work / 'simulation_console.log').read_text()
        record = {'name': name, 'command': cmd, 'timing_violation_count': len(re.findall(r'Timing violation', text, re.I)),
                  'known_states': re.findall(r'RESET_PHASE_STATE counter=(\S+) known=(\d+)', text),
                  'completed': 'RESET_PHASE_FINISHED' in text}
        records.append(record)
        print(json.dumps(record), flush=True)
    (out / 'results.json').write_text(json.dumps({'scope': 'Independent small reset circuit, not full SoC acceptance', 'cases': records}, indent=2) + '\n')
    assert records[1]['completed'] and records[1]['timing_violation_count'] == 0, records[1]
    assert all(known == '1' for _, known in records[1]['known_states']), records[1]


if __name__ == '__main__':
    main()
