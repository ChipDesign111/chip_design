"""Wait for completed synthesis, then independently audit its saved clocks.

This diagnostic does not modify RTL, production scripts, original reports or
the mapped checkpoint. It requires an EDA-enabled environment and Python 3.6+.
"""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--work-dir', type=Path, required=True)
    cli.add_argument('--coverage-dir', type=Path, required=True)
    cli.add_argument('--timeout-seconds', type=int, default=10800)
    args = cli.parse_args()
    work = args.work_dir.resolve()
    out = args.coverage_dir.resolve()
    scripts = Path(__file__).resolve().parent
    out.mkdir(parents=True, exist_ok=True)
    final = out / 'clock_coverage_audit.json'
    if final.exists() or (out / 'cdc_console.log').exists():
        raise RuntimeError('Existing audit evidence; choose a fresh coverage directory')
    deadline = time.monotonic() + args.timeout_seconds
    print('Waiting for synthesis manifest exit_code=0 and exact finish marker', flush=True)
    while True:
        try:
            manifest = json.loads((work / 'manifest.json').read_text())
        except (OSError, ValueError):
            manifest = {}
        if manifest.get('exit_code') is not None:
            if manifest['exit_code'] != 0:
                raise RuntimeError('Synthesis failed: exit_code=' + str(manifest['exit_code']))
            console = (work / 'console.log').read_text()
            if re.search(r'^ASIC_SYNTHESIS_FINISHED\s*$', console, re.M):
                break
        if time.monotonic() >= deadline:
            raise RuntimeError('Timed out waiting for completed synthesis')
        time.sleep(10)
    setup = work / 'backup/my_soc_top.genus_setup.tcl'
    database = work / 'backup/my_soc_top.g'
    for path in (setup, database, work / 'reports/timing_intent_final.rpt', work / 'outputs/my_soc_top_postsyn.v'):
        if not path.is_file() or path.stat().st_size == 0:
            raise RuntimeError('Completed synthesis is missing evidence: ' + str(path))
    record = {
        'started_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'synthesis_work': str(work),
        'synthesis_manifest_sha256': sha(work / 'manifest.json'),
        'mapped_database_sha256': sha(database),
        'production_sources_modified': False,
    }
    audit_cmd = [sys.executable, str(scripts / 'audit_clock_coverage.py'),
                 '--work-dir', str(work), '--coverage-dir', str(out)]
    subprocess.run(audit_cmd + ['--output', str(out / 'clock_coverage_prequery.json')], check=True)
    env = dict(os.environ, COVERAGE_SETUP=str(setup),
               COVERAGE_INTENT=str(work / 'reports/timing_intent_final.rpt'),
               COVERAGE_GATES=str(out / 'gates.tcl'), COVERAGE_AUDIT_ROOT=str(out))
    print('Synthesis completed; restoring checkpoint for read-only clock queries', flush=True)
    cmd = ['genus', '-no_gui', '-abort_on_error', '-f', str(scripts / 'clock_coverage.tcl'),
           '-log', str(out / 'genus')]
    record['command'] = cmd
    with (out / 'cdc_console.log').open('w') as log:
        process = subprocess.run(cmd, cwd=str(work), env=env, stdout=log, stderr=subprocess.STDOUT)
    record['genus_exit_code'] = process.returncode
    log = (out / 'cdc_console.log').read_text()
    if process.returncode or re.search(r'^\s*(?:Error|Fatal)\s*:', log, re.M):
        raise RuntimeError('Clock query failed; inspect cdc_console.log')
    for marker in ('CLOCK_COVERAGE_FINISHED', 'CLOCK_CROSSING_REPORTS_FINISHED'):
        if not re.search('^' + marker + r'\s*$', log, re.M):
            raise RuntimeError('Missing independent query finish marker: ' + marker)
    subprocess.run(audit_cmd + ['--output', str(final)], check=True)
    result = json.loads(final.read_text())
    assert result['clockless_pins'] == result['mapped_clockless_pins'], result
    assert len(result['inactive_gates']) == 5, result['inactive_gates']
    assert result['all_clockless_pins_explained_by_disabled_icg'], result['inactive_gates']
    assert len(result['cdc']) == 2, result['cdc']
    for crossing in result['cdc'].values():
        assert crossing['reported_paths'] == 10, crossing
        assert crossing['max_delay_exception_references'] == 10, crossing
        assert crossing['worst_reported_slack_ps'] >= 0, crossing
    assert sha(database) == record['mapped_database_sha256'], 'Mapped checkpoint changed during audit'
    record['finished_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    record['pass'] = True
    record['audit_sha256'] = sha(final)
    (out / 'audit_run.json').write_text(json.dumps(record, indent=2) + '\n')
    print('BOOTWAIT_CLOCK_AUDIT_PASS ' + str(final), flush=True)


if __name__ == '__main__':
    main()
