"""Compare sequential RAW and native batch reuse on identical graph integers."""
import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import numpy as np
import torch

from compiler import compile_model
from compiler.runtime import source_hashes
from compiler.sim import simulate
from raw_batch_cases import fixtures


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--soc', action='store_true')
    parser.add_argument('--vsim', default='vsim')
    parser.add_argument('--out', type=Path)
    parser.add_argument('--case', action='append', choices=[c[0] for c in fixtures()])
    parser.add_argument('--backend', action='append', choices=('cpu', 'sequential', 'reuse'))
    args = parser.parse_args()
    stamp = datetime.now(timezone(timedelta(hours=8))).strftime('%Y%m%d_%H%M%S')
    out = (args.out or ROOT/'test/int8/runs'/('raw_batch_'+stamp)).resolve()
    out.mkdir(parents=True, exist_ok=False)
    source = source_hashes()
    source.update({p.relative_to(ROOT).as_posix(): sha(p) for p in
                   (Path(__file__), Path(__file__).with_name('raw_batch_cases.py'))})
    report = dict(status='RUNNING', source_sha256=source, soc=args.soc, cases=[],
                  torch_version=torch.__version__, numpy_version=np.__version__,
                  timing='Accepted SRAM BEGIN/END, all graph outputs checked before END and read by SBA',
                  baseline='Unchanged four-way scalar CPU; original per-sample RAW when reuse_batch_weights=False')

    def save():
        (out/'result.json').write_text(json.dumps(report, indent=2)+'\n')

    save()
    try:
        for name, model, x, calibration in fixtures():
            if args.case and name not in args.case:
                continue
            # The CPU oracle uses the same integer contract even when no CPU
            # simulation was requested. The firmware still computes all values.
            oracle = compile_model(model, x, calibration, force_cpu=True)
            packages = {backend: (oracle if backend == 'cpu' else
                        compile_model(model, x, calibration, reuse_batch_weights=backend == 'reuse'))
                        for backend in args.backend or ('sequential', 'reuse')}
            inputs = [x]
            if name in ('full_b4', 'shift0_b2'):
                held = x.clone()
                if name == 'shift0_b2':
                    held[:, 0] = 0
                else:
                    held = held.flip(0)*0.75-0.125
                inputs.append(held)
            for index, value in enumerate(inputs):
                case = dict(case=name+('_held_out' if index else ''), batch=x.shape[0])
                refs = oracle.reference(value.numpy())
                seen = {}
                for backend, package in packages.items():
                    directory = out/case['case']/backend
                    actual_ref = package.write(directory, value.numpy())
                    for key, ref in refs.items():
                        np.testing.assert_array_equal(ref, actual_ref[key], err_msg=case['case']+':'+key)
                    meta = package.metadata
                    key = (sha(directory/'firmware.bin'), meta['npu_core_starts'], meta['npu_batch'])
                    if args.soc:
                        if key in seen:
                            result = dict(seen[key][1], same_firmware_as=seen[key][0])
                        else:
                            result = simulate(directory, args.vsim)
                            seen[key] = (backend, result)
                    else:
                        result = {}
                    result.update(npu_core_starts=meta['npu_core_starts'], npu_batch=meta['npu_batch'],
                                  code_bytes=meta['code_bytes'], free_bytes=meta['free_bytes'],
                                  scratch_bytes=meta['accumulator_scratch_bytes'],
                                  weight_dma_bytes=meta['weight_dma_bytes'],
                                  batch_weight_reuse=meta['batch_weight_reuse'],
                                  fallback=meta['batch_weight_reuse_fallback'],
                                  wide_accumulation=any(n.get('accumulator_bound', 0) > (1 << 21) for n in package.nodes),
                                  linear_shifts=[n['shift'] for n in package.nodes if n['op'] == 'linear'])
                    artifacts = ('firmware.bin', 'firmware.hex', 'firmware.S', 'manifest.json', 'reference.json')
                    if args.soc and 'same_firmware_as' not in result:
                        artifacts += ('actual_output.json', 'simulation.json')
                    result['evidence_sha256'] = {f: sha(directory/f) for f in artifacts}
                    case[backend] = result
                    print('%s %s: PASS%s starts=%d batch=%d%s' %
                          (case['case'], backend, ' cycles=%d' % result['cycles'] if args.soc else '',
                           meta['npu_core_starts'], meta['npu_batch'],
                           ' same='+result['same_firmware_as'] if 'same_firmware_as' in result else ''), flush=True)
                if args.soc and 'sequential' in case and 'reuse' in case:
                    case['reuse_speedup'] = case['sequential']['cycles']/case['reuse']['cycles']
                if args.soc and 'cpu' in case and 'reuse' in case:
                    case['cpu_speedup'] = case['cpu']['cycles']/case['reuse']['cycles']
                report['cases'].append(case); save()
        for name, digest in source.items():
            if sha(ROOT/name) != digest:
                raise ValueError('Source changed during batch comparison: '+name)
        report['status'] = 'PASS'
    except Exception as error:
        report.update(status='FAIL', error=str(error))
        raise
    finally:
        save()
    print('Results: '+str(out), flush=True)


if __name__ == '__main__':
    main()
