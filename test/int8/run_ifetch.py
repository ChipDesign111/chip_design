"""Exercise instruction-buffer handshakes, debug fetches, reset and invalidation."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--xrun', default='xrun')
    parser.add_argument('--out', type=Path)
    parser.add_argument('--rtl', type=Path)
    parser.add_argument('--expect-uncached-failure', action='store_true')
    args = parser.parse_args()
    out = (args.out or ROOT / 'test/int8/runs' /
           datetime.now().strftime('%Y%m%d_%H%M%S_ifetch')).resolve()
    if out.exists() and any(out.iterdir()):
        parser.error('Use a fresh output directory')
    out.mkdir(parents=True, exist_ok=True)
    rtl = (args.rtl or ROOT / 'rtl/soc/my_ifetch.sv').resolve()
    paths = [ROOT / 'rtl/axi/axi_pkg.sv', rtl, ROOT / 'test/int8/tb_ifetch.sv']
    sources = {str(path): digest(path) for path in paths}
    sources[str(ROOT / 'rtl/include/axi/typedef.svh')] = digest(ROOT / 'rtl/include/axi/typedef.svh')
    sources[str(Path(__file__).resolve())] = digest(Path(__file__).resolve())
    command = [args.xrun, '-64bit', '-sv', '-timescale', '1ns/1ps',
               '+incdir+' + str(ROOT / 'rtl/include'),
               *map(str, paths), '-top', 'tb_ifetch', '-l', str(out / 'xrun.log')]
    if args.expect_uncached_failure:
        command += ['+define+IFETCH_LEGACY', '+ONLY_UNCACHED']
    result = subprocess.run(command, cwd=out, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, timeout=180)
    (out / 'console.log').write_bytes(result.stdout)
    text = result.stdout.decode(errors='replace')
    marker = re.search(r'IFETCH_PASS checks=(\d+) grants=(\d+) responses=(\d+) bursts=(\d+)', text)
    errors = re.findall(r'^.*(?:\*[EF],|IFETCH_FAIL|FATAL).*$', text, re.MULTILINE)
    if args.expect_uncached_failure:
        # Xcelium reports an intentional $fatal as *F,FATSEV, which is the
        # expected runtime failure here. Any compiler/error diagnostic fails.
        passed = (re.search(r'^IFETCH_FAIL fetch_timeout addr=00000804$', text, re.MULTILINE) is not None and
                  '*F,FATSEV' in text and
                  not re.search(r'IFETCH_PASS|IFETCH_UNCACHED_PASS|\*E,|\*F,(?!FATSEV)', text))
    else:
        passed = result.returncode == 0 and marker is not None and not errors
    unchanged = sources == {name: digest(Path(name)) for name in sources}
    passed = passed and unchanged
    report = dict(status='PASS' if passed else 'FAIL',
                  finished_utc=datetime.now(timezone.utc).isoformat(),
                  negative_control=args.expect_uncached_failure,
                  command=command, exit_code=result.returncode,
                  source_sha256=sources, sources_unchanged=unchanged, errors=errors,
                  checks=int(marker[1]) if marker else None,
                  console_sha256=digest(out / 'console.log'),
                  scope='Standalone RTL protocol regression, synthetic AXI memory; not SoC or SDF acceptance')
    (out / 'result.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(text[-4000:])
    print('IFETCH REGRESSION ' + report['status'] + ' ' + str(out))
    if not passed:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
