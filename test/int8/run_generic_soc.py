"""Exercise CPU-driven tiled GEMV and multilayer INT8 inference.

--reference-only runs portable planner/numerical tests without a simulator.
The default also executes descriptor-driven RV32IM firmware on the complete
CV32E40P/AXI/DMA/NPU RTL, with all model data inside the 8 KiB SRAM image.
"""
import argparse
import hashlib
import json
from pathlib import Path
import random
import re
import subprocess
import time

from generic_runtime import Layer, plan, reference, tiles
from generic_firmware import build

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


def fixtures():
    rng = random.Random(260518)
    def matrix(n, k, lo=-128, hi=127):
        return [[rng.randint(lo, hi) for _ in range(k)] for _ in range(n)]
    return [
        ('tail_33x65', [Layer(matrix(33, 65), [rng.randint(-100000, 100000) for _ in range(33)])],
         [rng.randint(-128, 127) for _ in range(65)]),
        ('beyond_int22', [Layer([[-128]*129], [17])], [-128]*129),
        ('three_layers', [Layer(matrix(9, 17), [71, -93, 17, 100, -7, 33, 51, -19, 0], 1064, 20, True),
                          Layer(matrix(5, 9), [123, -45, 11, 37, -29], 65535, 24, True),
                          Layer(matrix(3, 5), [100000, -300000, 7])],
         [rng.randint(-128, 127) for _ in range(17)]),
        # Third sum is 65537: *65535 = 2^32-1. Adding round(31)
        # carries across the low limb and must produce hidden value 2.
        ('requant_64bit', [Layer([[127]*65, [-128]*65, [1]*65], [1900000000, -1900000000, 57282],
                                65535, 31, True),
                            Layer([[127, -128, 1]], [-123])], [127]*65),
    ]


def tiled_reference(layer, x):
    sums = list(layer.bias)
    for nb, kb, nt, kt in tiles(len(layer.weights), len(x)):
        for row in range(nt):
            partial = sum(layer.weights[nb+row][kb+i]*x[kb+i] for i in range(kt))
            assert -(1 << 21) <= partial < (1 << 21)
            sums[nb+row] += partial
    if layer.requant:
        sums = [min(127, (max(v, 0)*layer.mult + ((1 << (layer.shift-1)) if layer.shift else 0)) >> layer.shift)
                for v in sums]
    return sums


def reference_checks():
    rng = random.Random(18)
    checks = 0
    for k in (1, 2, 3, 63, 64, 65, 127, 128, 129, 193):
        for n in (1, 2, 31, 32, 33, 65):
            x = [rng.randint(-128, 127) for _ in range(k)]
            for mult, shift, requant in ((1, 0, False), (0, 0, True), (65535, 31, True), (1064, 20, True)):
                layer = Layer([[rng.randint(-128, 127) for _ in range(k)] for _ in range(n)],
                              [rng.randint(-1000000, 1000000) for _ in range(n)], mult, shift, requant)
                assert tiled_reference(layer, x) == reference([layer], x)[0]
                checks += 1
    def rejects(layers, x):
        nonlocal checks
        try:
            plan(layers, x)
        except ValueError:
            checks += 1
        else:
            raise AssertionError('Planner accepted invalid model')
    rejects([Layer([[127]*129], [(1 << 31)-1])], [1]*129)
    rejects([Layer([[0]], [1 << 31])], [1])
    rejects([Layer([[0]], [0.5])], [1])
    rejects([Layer([[0]], [0], 1.0)], [1])
    rejects([Layer([[0]], [0], 1, 2.0)], [1])
    rejects([Layer([[0]], [0], 65536)], [1])
    rejects([Layer([[0]], [0], 1, 32)], [1])
    rejects([Layer([[128]], [0])], [1])
    rejects([Layer([[0]], [0])], [-129])
    rejects([Layer([[0]], [0]), Layer([[0]], [0])], [1])
    rejects([Layer([[0]*256 for _ in range(64)], [0]*64)], [1]*256)
    rejects([Layer([], [])], [1])
    rejects([Layer([[0]], [0])], [])
    for _, layers, inputs in fixtures():
        p = plan(layers, inputs)
        assert p['compact_end'] <= 0x17c0
        current = inputs
        for layer, expected in zip(layers, reference(layers, inputs)):
            current = tiled_reference(layer, current)
            assert current == expected
            checks += 1
    return checks


def hashes():
    paths = list((ROOT/'rtl').rglob('*.sv')) + list((ROOT/'rtl').rglob('*.svh'))
    paths += [HERE/name for name in ('generic_runtime.py', 'generic_firmware.py', 'run_generic_soc.py', 'tb_generic_soc.sv', 'assembler.py')]
    paths += [ROOT/'rtl/filelist.f']
    return {str(p.relative_to(ROOT)).replace('\\', '/'): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(paths)}


def execute(command, cwd, log, timeout):
    start = time.monotonic()
    result = subprocess.run(command, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)
    output = result.stdout.decode(errors='replace')
    (cwd/log).write_text(output, encoding='utf-8')
    if result.returncode or re.search(r'FATAL:|# \*\* (?:Fatal|Error):', output):
        raise RuntimeError('%s failed: %s' % (log, output[-4000:]))
    return output, round(time.monotonic()-start, 3)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference-only', action='store_true')
    parser.add_argument('--out', type=Path)
    parser.add_argument('--vsim', default='vsim')
    parser.add_argument('--case', action='append', choices=[f[0] for f in fixtures()])
    parser.add_argument('--timeout', type=int, default=300)
    args = parser.parse_args()
    checks = reference_checks()
    print('GENERIC_REFERENCE_PASS checks=%d' % checks, flush=True)
    if args.reference_only:
        return
    out = (args.out or HERE/'runs'/('generic_%s' % time.strftime('%Y%m%d_%H%M%S'))).resolve()
    out.mkdir(parents=True, exist_ok=False)
    source = hashes()
    (out/'source_manifest.json').write_text(json.dumps(source, indent=2)+'\n')
    sources = []
    for line in (ROOT/'rtl/filelist.f').read_text().splitlines():
        if line.startswith('+incdir+'):
            sources.append('+incdir+'+(ROOT/line[8:]).as_posix())
        elif line.strip():
            sources.append((ROOT/line).as_posix())
    sources.append((HERE/'tb_generic_soc.sv').as_posix())
    (out/'soc.f').write_text('\n'.join(sources)+'\n')
    (out/'compile.do').write_text('onerror {quit -code 1}\nvlib work\nvmap work work\nvlog -sv -f soc.f\nquit -code 0\n')
    execute([args.vsim, '-c', '-do', 'do compile.do'], out, 'compile.log', args.timeout)
    results = []
    for name, layers, inputs in fixtures():
        if args.case and name not in args.case:
            continue
        directory = out/name
        metadata = build(directory, layers, inputs)
        # Reuse the compiled design, never a different RTL or injected result.
        (directory/'run.do').write_text('onerror {quit -code 1}\nonbreak {resume}\nvmap work {%s}\nvsim -suppress 12110 -novopt -onfinish stop work.tb_generic_soc +TILES=%d\nrun -all\nset status [examine -radix hex /tb_generic_soc/magic]\nif {![string equal -nocase $status c0dec0de]} {quit -code 3}\nquit -code 0\n' % ((out/'work').as_posix(), metadata['tile_count']))
        output, elapsed = execute([args.vsim, '-c', '-do', 'do run.do'], directory, 'soc.log', args.timeout)
        match = re.search(r'GENERIC_SOC_PASS cycles=(\d+) tiles=(\d+)', output)
        if not match or int(match[2]) != metadata['tile_count']:
            raise RuntimeError('Missing generic CPU PASS or incorrect tile count')
        results.append({'case': name, 'cycles': int(match[1]), 'tiles': int(match[2]),
                        'layers': len(layers), 'elapsed_seconds': elapsed,
                        'code_bytes': metadata['code_bytes'], 'compact_data_end': metadata['compact_end'],
                        'firmware_sha256': hashlib.sha256((directory/'firmware.hex').read_bytes()).hexdigest()})
        print('%s: PASS cycles=%s tiles=%s' % (name, match[1], match[2]), flush=True)
    if hashes() != source:
        raise RuntimeError('Source changed during generic regression')
    (out/'result.json').write_text(json.dumps({'passed': True, 'reference_checks': checks, 'cases': results,
                                             'scope': 'RTL functional simulation, complete CPU/AXI/DMA path; no EDA timing claim'}, indent=2)+'\n')
    print('Results: '+str(out), flush=True)


if __name__ == '__main__':
    main()
