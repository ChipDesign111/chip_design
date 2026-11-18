"""Original trained HAR MODE=0 versus the current four-way scalar CPU baseline."""
import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from compiler.runtime import source_hashes
from run_generic_soc import execute
from har_benchmark import build


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--vsim', default='vsim')
    parser.add_argument('--out', type=Path)
    parser.add_argument('--seed', type=int, action='append', help='Default 10000, the first trained four-sample fixture')
    parser.add_argument('--batch', type=int, action='append', choices=(1, 2, 3, 4), help='Default compares batch 1,2,4')
    args = parser.parse_args()
    stamp = datetime.now(timezone(timedelta(hours=8))).strftime('%Y%m%d_%H%M%S')
    out = (args.out or ROOT/'test/int8/runs'/('har_bench_'+stamp)).resolve()
    out.mkdir(parents=True, exist_ok=False)
    source = source_hashes()
    names = ('test/int8/run.py', 'test/int8/firmware.py', 'test/int8/har_benchmark.py',
             'test/int8/run_har_benchmark.py', 'test/int8/tb_har_benchmark.sv',
             'test/int8/har_uci24.json', 'model/reference/tile_layout.py',
             'model/export/weights_int8.npz', 'model/export/quant_params.json')
    source.update({name: sha(ROOT/name) for name in names})
    report = dict(status='RUNNING', source_sha256=source, cases=[], clock_period_ns=10,
                  arithmetic='Original HAR INT22 wrap, ReLU/UINT16 requantization, INT22 scores and lowest-index signed argmax',
                  timing='Accepted SRAM BEGIN/END; includes parameter/input preparation, CPU or NPU inference and hidden/scores/class SRAM publication; all golden checks and statistics after END',
                  cpu_baseline='Existing scalar RV32IM four-element-unrolled dot products; software wrap22 and exact 64-bit requantization',
                  npu_firmware='Existing reuse8 config/input schedule and MODE=0; output reads become SRAM stores before END',
                  original_2700_note='Original 2700/2695 includes CPU golden checks and uses another timing interval; do not substitute it for paired BEGIN/END cycles')

    def save():
        (out/'result.json').write_text(json.dumps(report, indent=2)+'\n')

    save()
    try:
        sources = []
        for line in (ROOT/'rtl/filelist.f').read_text().splitlines():
            line = line.strip()
            if line and not line.startswith('//'):
                sources.append('+incdir+'+(ROOT/line[8:]).as_posix() if line.startswith('+incdir+') else (ROOT/line).as_posix())
        sources.append((ROOT/'test/int8/tb_har_benchmark.sv').as_posix())
        (out/'soc.f').write_text('\n'.join(sources)+'\n')
        (out/'compile.do').write_text('onerror {quit -code 1}\nvlib work\nvmap work work\nvlog -sv -f soc.f\nquit -code 0\n')
        execute([args.vsim, '-c', '-do', 'do compile.do'], out, 'compile.log', 300)
        for seed in args.seed or [10000]:
            for batch in args.batch or [1, 2, 4]:
                case = dict(seed=seed, batch=batch, useful_macs=batch*2240)
                images = {}
                input_hash = None
                for backend in ('cpu', 'npu'):
                    run = out/('seed_%d_batch_%d' % (seed, batch))/backend
                    meta = build(run, seed, batch, backend)
                    if input_hash is not None and input_hash != meta['input_bytes_sha256']:
                        raise AssertionError('CPU/NPU input mismatch')
                    input_hash = meta['input_bytes_sha256']
                    images[backend] = (run/'firmware.bin').read_bytes()
                    starts = 1 if backend == 'npu' else 0
                    (run/'run.do').write_text('onerror {quit -code 1}\nonbreak {resume}\nvmap work {%s}\nvsim -suppress 12110 -novopt -onfinish stop work.tb_har_benchmark +TILES=%d +BATCH=%d\nrun -all\nset status [examine -radix hex /tb_har_benchmark/magic]\nif {![string equal -nocase $status c0dec0de]} {quit -code 3}\nquit -code 0\n' % ((out/'work').as_posix(), starts, batch))
                    text, seconds = execute([args.vsim, '-c', '-do', 'do run.do'], run, 'soc.log', 300)
                    match = re.search(r'HAR_BENCH_PASS ([^\r\n]+)', text)
                    if not match:
                        raise RuntimeError('Missing genuine HAR benchmark PASS')
                    values = {key: int(value) for key, value in re.findall(r'(\w+)=(\d+)', match[1])}
                    if values['starts'] != starts or values['batch'] != batch:
                        raise AssertionError('Incorrect HAR job/batch count')
                    case[backend] = dict(values, code_bytes=meta['code_bytes'], elapsed_seconds=seconds,
                                         firmware_sha256=sha(run/'firmware.bin'), log_sha256=sha(run/'soc.log'))
                    print('HAR seed=%d batch=%d %s: PASS cycles=%d' % (seed, batch, backend, values['cycles']), flush=True)
                # Independently reconstruct logical row-major matrices from the
                # NPU image and compare every CPU weight/bias/parameter byte.
                image = images['npu']; cpu = images['cpu']
                at = int.from_bytes(image[0x1f0c:0x1f10], 'little')-0x80000000
                first, second = image[at:at+2048], image[0x1800:0x18c0]
                assert cpu[at:at+2048] == bytes(first[(i//2)*64+o*2+i%2] for o in range(32) for i in range(64))
                assert cpu[0x1800:0x18c0] == bytes(second[i*6+o] for o in range(6) for i in range(32))
                assert cpu[0x1900:0x1d00] == image[0x1900:0x1d00]
                assert cpu[0x1f00:0x1f10] == image[0x1f00:0x1f10]
                case.update(input_bytes_sha256=input_hash,
                            speedup=case['cpu']['cycles']/case['npu']['cycles'],
                            logical_operands_identical=True)
                report['cases'].append(case); save()
                print('HAR batch=%d speedup=%.4fx' % (batch, case['speedup']), flush=True)
        for name, digest in source.items():
            if sha(ROOT/name) != digest:
                raise ValueError('Source changed during HAR comparison: '+name)
        report['status'] = 'PASS'
    except Exception as error:
        report.update(status='FAIL', error=str(error))
        raise
    finally:
        save()
    print('Results: '+str(out), flush=True)


if __name__ == '__main__':
    main()
