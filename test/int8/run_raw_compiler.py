"""Same-integer-model CPU/RAW SoC comparisons after the PyTorch frontend."""
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

from compiler import compile_layers, compile_model
from compiler.runtime import source_hashes
from compiler.sim import simulate
from raw_compiler_cases import fixtures
from run_gemv_benchmark import cases as integer_cases


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--soc', action='store_true')
    parser.add_argument('--vsim', default='vsim')
    parser.add_argument('--out', type=Path)
    parser.add_argument('--case', action='append', choices=[c[0] for c in fixtures()]+['integer_full', 'integer_tail'])
    args = parser.parse_args()
    stamp = datetime.now(timezone(timedelta(hours=8))).strftime('%Y%m%d_%H%M%S')
    out = (args.out or ROOT/'test/int8/runs'/('raw_frontend_'+stamp)).resolve()
    out.mkdir(parents=True, exist_ok=False)
    source = source_hashes()
    source.update({p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                   for p in [Path(__file__), Path(__file__).with_name('raw_compiler_cases.py'), ROOT/'model/raw_mixed/model.py']})
    report = dict(status='RUNNING', source_sha256=source, torch_version=torch.__version__,
                  numpy_version=np.__version__, soc=args.soc, cpu_unroll=4,
                  target='int22-raw-v1', frontend='main@4b552b1', cases=[])

    def save():
        (out/'result.json').write_text(json.dumps(report, indent=2)+'\n')

    save()
    try:
        for name, model, x, calibration in fixtures():
            if args.case and name not in args.case:
                continue
            compiled = {backend: compile_model(model, x, calibration, force_cpu=(backend == 'cpu'))
                        for backend in ('cpu', 'raw')}
            inputs = [x, x*0.75-0.125] if name == 'mixed' else [x]
            for index, value in enumerate(inputs):
                case = dict(case=name+('_held_out' if index else ''), kind='pytorch')
                refs = None
                for backend, package in compiled.items():
                    directory = out/case['case']/backend
                    actual_ref = package.write(directory, value.numpy())
                    if refs is not None:
                        for key in refs:
                            np.testing.assert_array_equal(refs[key], actual_ref[key])
                    refs = actual_ref
                    result = simulate(directory, args.vsim) if args.soc else {}
                    result.update(code_bytes=package.metadata['code_bytes'], free_bytes=package.metadata['free_bytes'],
                                  npu_core_starts=package.metadata['npu_core_starts'],
                                  code_sha256=package.metadata['code_sha256'],
                                  float_max_abs_error=float(np.abs(actual_ref[package.metadata['output']].astype(float)*package.metadata['tensors'][package.metadata['output']]['scale']-model(value.detach().clone()).detach().numpy()).max()))
                    case[backend] = result
                    print('%s %s: PASS%s' % (case['case'], backend, ' cycles=%d' % result['cycles'] if args.soc else ''), flush=True)
                if args.soc:
                    case['speedup'] = case['cpu']['cycles']/case['raw']['cycles']
                report['cases'].append(case); save()
        old = {c['case']: c for c in json.loads((ROOT/'report/gemv_optimization.json').read_text())['cases']}
        for name, layers, x in integer_cases():
            if name not in ('full_32x64', 'tail_33x65'):
                continue
            label = 'integer_full' if name == 'full_32x64' else 'integer_tail'
            if args.case and label not in args.case:
                continue
            case = dict(case=label, kind='integer')
            for backend in ('cpu', 'raw'):
                directory = out/label/backend
                p = compile_layers(layers, x, force_cpu=(backend == 'cpu')); p.write(directory)
                result = simulate(directory, args.vsim) if args.soc else {}
                if args.soc:
                    prior = old[name]['cpu' if backend == 'cpu' else 'optimized']['cycles']
                    if result['cycles'] != prior:
                        raise AssertionError('Existing integer cycle count changed: '+label+' '+backend)
                    result['previous_cycles'] = prior
                case[backend] = result
                print('%s %s: PASS%s' % (label, backend, ' cycles=%d' % result['cycles'] if args.soc else ''), flush=True)
            if args.soc:
                case['speedup'] = case['cpu']['cycles']/case['raw']['cycles']
            report['cases'].append(case); save()
        for name, digest in source.items():
            if hashlib.sha256((ROOT/name).read_bytes()).hexdigest() != digest:
                raise ValueError('Source changed during frontend regression: '+name)
        report['status'] = 'PASS'
    except Exception as error:
        report.update(status='FAIL', error=str(error))
        raise
    finally:
        save()
    print('Results: '+str(out), flush=True)


if __name__ == '__main__':
    main()
