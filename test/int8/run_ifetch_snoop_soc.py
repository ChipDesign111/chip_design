"""Exercise real SoC SRAM writes/aliases with an explicitly driven fetch port."""
import argparse
import json
from pathlib import Path
import re
import shutil

from run_soc_xcelium import ROOT, elaborate, execute, sha, source_hashes


def inputs():
    result = {name: value for name, value in source_hashes().items()
              if Path(name).suffix in ('.sv', '.svh', '.v', '.f')}
    for name in ('tb_ifetch_snoop_soc.sv', 'run_ifetch_snoop_soc.py', 'run_soc_xcelium.py'):
        path = ROOT / 'test/int8' / name
        result[path.relative_to(ROOT).as_posix()] = sha(path)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--xrun', default='xrun')
    args = parser.parse_args()
    executable = shutil.which(args.xrun)
    if not executable:
        parser.error('xrun not found')
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    before = inputs()
    report = {'status': 'RUNNING', 'source_sha256': before,
              'scope': 'Real AXI SRAM/Debug SBA writes and explicitly driven CPU fetch; not firmware execution, JTAG TAP, or SDF'}
    try:
        snapshot, _ = elaborate(executable, out / 'build', 'tb_ifetch_snoop_soc', 600)
        case = out / 'snoop'
        case.mkdir()
        text, _ = execute([executable, '-64bit', '-R', '-xmlibdirname', str(snapshot),
                           '-l', str(case / 'xrun.log')], case, 600)
        match = re.search(r'IFETCH_SNOOP_SOC PASS checks=(\d+) accepted_writes=(\d+) alias_writes=(\d+) zero_strobes=(\d+)', text)
        if not match or 'SNOOP_SOC_FAIL' in text:
            raise RuntimeError('Missing successful boundary checks')
        report.update(zip(('checks', 'accepted_writes', 'alias_writes', 'zero_strobes'), map(int, match.groups())))
        if before != inputs():
            raise RuntimeError('Sources changed during simulation')
        report['status'] = 'PASS'
        print(match[0])
    except Exception as error:
        report.update(status='FAIL', error=str(error))
        raise
    finally:
        (out / 'results.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
