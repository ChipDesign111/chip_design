"""Compare real RV32IM CPU GEMV with CPU + RAW on the same full SoC RTL.

Both backends consume identical compact SRAM data. BEGIN/END store acceptance
defines the interval, including RAW setup, packing, DMA, polling and reduction.
Every output is checked before END by a passive monitor, and after END by CPU.
"""
import argparse
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import random
import re
import subprocess
import time

from generic_firmware import BENCHMARK_PHASES, build
from generic_runtime import BASE, CODE_BYTES, Layer, plan
from run_generic_soc import HERE, ROOT, execute, fixtures, hashes, reference_checks


def cases():
    rng = random.Random(261118)
    full = ('full_32x64', [Layer([[rng.randint(-128, 127) for _ in range(64)] for _ in range(32)],
                               [rng.randint(-100000, 100000) for _ in range(32)])],
            [rng.randint(-128, 127) for _ in range(64)])
    return [full] + fixtures()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def manifest():
    source = hashes()
    for name in ('run_gemv_benchmark.py', 'tb_gemv_benchmark.sv'):
        source['test/int8/' + name] = sha(HERE / name)
    return source


def write_words(path, values):
    path.write_text(''.join('%08x\n' % (value & 0xffffffff) for value in values))


def prepare(directory, layers, inputs, backend):
    p = plan(layers, inputs)
    if p['layer_count'] > 32:
        raise ValueError('Benchmark monitor supports at most 32 layers')
    meta = build(directory, layers, inputs, backend=backend, benchmark=True)
    expected = bytearray(p['image'])
    layout = [len(layers)]
    allocations = {entry['name']: entry for entry in p['allocations']}
    for i, output in enumerate(p['outputs']):
        start = output['address'] - BASE
        width = output['bytes_per_value']
        values = b''.join((v & ((1 << (width * 8)) - 1)).to_bytes(width, 'little') for v in output['values'])
        expected[start:start + len(values)] = values
        golden = allocations['golden_%d' % i]
        layout += [BASE + start, BASE + start + len(values),
                   BASE + golden['offset'], BASE + golden['offset'] + golden['bytes']]
    write_words(directory / 'expected.hex',
                [int.from_bytes(expected[i:i+4], 'little') for i in range(0, 8192, 4)])
    write_words(directory / 'bench_layout.hex', layout + [0] * (129 - len(layout)))
    write_words(directory / 'phase_pcs.hex', [meta['phase_pcs'][name] for name in BENCHMARK_PHASES])
    data = p['image'][CODE_BYTES:]
    meta['compact_data_sha256'] = hashlib.sha256(data).hexdigest()
    return meta


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--vsim', default='vsim')
    parser.add_argument('--out', type=Path)
    parser.add_argument('--case', action='append', choices=[case[0] for case in cases()])
    parser.add_argument('--timeout', type=int, default=300)
    args = parser.parse_args()
    stamp = datetime.now(timezone(timedelta(hours=8))).strftime('%Y%m%d_%H%M%S')
    out = (args.out or HERE / 'runs' / ('gemv_bench_' + stamp)).resolve()
    out.mkdir(parents=True, exist_ok=False)
    source = manifest()
    report = {
        'status': 'RUNNING', 'created_at': stamp, 'timezone': 'Asia/Shanghai',
        'git_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'git_status': subprocess.check_output(['git', 'status', '--short'], cwd=ROOT, text=True),
        'source_sha256': source, 'clock_period_ns': 10,
        'scope': 'Full CV32E40P/AXI/DMA/NPU RTL, behavioural SRAM, batch=1; not physical timing signoff',
        'timing_rule': 'Accepted SRAM BEGIN to END stores, cold reset per backend; includes initialization, runtime weight packing, input transfer, NPU/DMA, result reduction and requantization, excludes image loading and all golden checks',
        'phase_rule': 'Passive wall-clock windows at legal ID issue of generated phase labels; sum equals total, not an instruction retirement trace; npu_wait includes START/poll overhead',
        'cpu_baseline': 'Scalar RV32IM signed LB/MUL/ADD, four-element unroll plus scalar tail; shared bias, output and exact 64-bit requantization code',
        'speedup_rule': 'cpu.cycles / raw.cycles; greater than 1 means RAW is faster',
        'cases': [],
    }

    def save():
        (out / 'result.json').write_text(json.dumps(report, indent=2) + '\n')

    save()
    try:
        report['reference_checks'] = reference_checks()
        sources = []
        for line in (ROOT / 'rtl/filelist.f').read_text().splitlines():
            line = line.strip()
            if not line or line.startswith('//'):
                continue
            sources.append('+incdir+' + (ROOT / line[8:]).as_posix() if line.startswith('+incdir+')
                           else (ROOT / line).as_posix())
        sources.append((HERE / 'tb_gemv_benchmark.sv').as_posix())
        (out / 'soc.f').write_text('\n'.join(sources) + '\n')
        (out / 'compile.do').write_text('onerror {quit -code 1}\nvlib work\nvmap work work\nvlog -sv -f soc.f\nquit -code 0\n')
        _, report['compile_seconds'] = execute([args.vsim, '-c', '-do', 'do compile.do'], out, 'compile.log', args.timeout)
        for name, layers, inputs in cases():
            if args.case and name not in args.case:
                continue
            directory = out / name
            directory.mkdir()
            model = {'inputs': inputs, 'layers': [asdict(layer) for layer in layers]}
            (directory / 'model.json').write_text(json.dumps(model, indent=2) + '\n')
            k = len(inputs)
            macs = 0
            for layer in layers:
                macs += len(layer.weights) * k
                k = len(layer.weights)
            case = {'case': name, 'layers': len(layers), 'useful_macs': macs,
                    'model_sha256': sha(directory / 'model.json')}
            data_hash = None
            for backend in ('cpu', 'raw'):
                run = directory / backend
                metadata = prepare(run, layers, inputs, backend)
                if data_hash is not None and data_hash != metadata['compact_data_sha256']:
                    raise RuntimeError('Backend compact data mismatch')
                data_hash = metadata['compact_data_sha256']
                firmware_hash = sha(run / 'firmware.hex')
                expected_tiles = metadata['tile_count'] if backend == 'raw' else 0
                (run / 'run.do').write_text('onerror {quit -code 1}\nonbreak {resume}\nvmap work {%s}\nvsim -suppress 12110 -novopt -onfinish stop work.tb_gemv_benchmark +TILES=%d\nrun -all\nset status [examine -radix hex /tb_gemv_benchmark/magic]\nif {![string equal -nocase $status c0dec0de]} {quit -code 3}\nquit -code 0\n' % ((out / 'work').as_posix(), expected_tiles))
                text, elapsed = execute([args.vsim, '-c', '-do', 'do run.do'], run, 'soc.log', args.timeout)
                match = re.search(r'GEMV_BENCH_PASS ([^\r\n]+)', text)
                if not match:
                    raise RuntimeError('Missing genuine benchmark PASS: ' + str(run))
                counters = {key: int(value) for key, value in re.findall(r'(\w+)=(\d+)', match[1])}
                if sum(counters[name + '_cycles'] for name in BENCHMARK_PHASES) != counters['cycles']:
                    raise RuntimeError('Invalid phase cycle sum')
                if counters['tiles'] != expected_tiles or firmware_hash != sha(run / 'firmware.hex'):
                    raise RuntimeError('Task count or firmware identity changed')
                case[backend] = dict(counters, code_bytes=metadata['code_bytes'],
                                     firmware_sha256=firmware_hash, elapsed_seconds=elapsed)
                print('%s %s: PASS cycles=%d' % (name, backend, counters['cycles']), flush=True)
            case['compact_data_sha256'] = data_hash
            case['speedup'] = case['cpu']['cycles'] / case['raw']['cycles']
            case['raw_mac_fill_ratio'] = macs / (case['raw']['tiles'] * 32 * 64)
            report['cases'].append(case)
            save()
            print('%s speedup=%.4fx' % (name, case['speedup']), flush=True)
        if manifest() != source:
            raise RuntimeError('RTL or benchmark sources changed during measurement')
        report['status'] = 'PASS'
    except Exception as error:
        report.update(status='FAIL', error=str(error))
        raise
    finally:
        save()
    print('Results: ' + str(out), flush=True)


if __name__ == '__main__':
    main()
