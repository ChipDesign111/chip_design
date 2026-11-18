"""Host contracts for the main FX frontend and current RAW/quad-CPU backends."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import numpy as np
import torch
from torch import nn

from compiler import compile_layers, compile_model
from compiler.compiler import rescale
from compiler.frontend import CompileError
from raw_compiler_cases import fixtures
from raw_batch_cases import fixtures as batch_fixtures
from run_gemv_benchmark import cases as integer_cases


class CompilerContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        (ROOT/'test/int8/runs').mkdir(parents=True, exist_ok=True)

    def test_existing_integer_images(self):
        old = {c['case']: c for c in json.loads((ROOT/'report/gemv_optimization.json').read_text())['cases']}
        with tempfile.TemporaryDirectory(dir=ROOT/'test/int8/runs') as tmp:
            for name, layers, x in integer_cases():
                for cpu, backend in ((True, 'cpu'), (False, 'optimized')):
                    directory = Path(tmp)/name/backend
                    compile_layers(layers, x, force_cpu=cpu).write(directory)
                    # Historical evidence was collected on Windows. Canonical
                    # CRLF checks keep the same instruction-word identity on Unix.
                    text = (directory/'firmware.hex').read_text().splitlines()
                    digest = hashlib.sha256(('\r\n'.join(text)+'\r\n').encode()).hexdigest()
                    self.assertEqual(digest, old[name][backend]['firmware_sha256'])

    def test_backend_integer_contracts(self):
        for name, model, x, calibration in fixtures():
            accelerated = compile_model(model, x, calibration)
            cpu = compile_model(model, x, calibration, force_cpu=True)
            self.assertEqual(accelerated.metadata['cpu_unroll'], 4)
            for key, value in accelerated.reference(x.numpy()).items():
                np.testing.assert_array_equal(value, cpu.reference(x.numpy())[key], err_msg=name+':'+key)
            self.assertFalse(cpu.metadata['npu_core_starts'])
            self.assertFalse(accelerated.metadata['task_engine'])

    def test_wide_accumulation_still_uses_raw(self):
        _, model, x, calibration = next(c for c in fixtures() if c[0] == 'beyond_int22')
        package = compile_model(model, x, calibration)
        self.assertGreater(package.nodes[0]['accumulator_bound'], 1 << 21)
        self.assertEqual(package.metadata['npu_core_starts'], 1)
        self.assertEqual(package.nodes[0]['backend'], 'RAW+CPU')

    def test_weight_size_no_padding_or_duplicate(self):
        _, model, x, calibration = next(c for c in fixtures() if c[0] == 'tail')
        package = compile_model(model, x, calibration)
        node = package.nodes[0]
        self.assertEqual(node['weight_bytes'], 33*65)
        self.assertEqual(node['raw_tiles'], 1)
        self.assertEqual(node['cpu_macs'], 97)

    def test_graph_has_no_embedded_golden(self):
        for _, model, x, calibration in fixtures():
            p = compile_model(model, x, calibration)
            self.assertFalse(any('golden' in a['name'] for a in p.metadata['allocations']))
            for name, tensor in p.metadata['tensors'].items():
                for row in range(tensor['shape'][0]):
                    at = tensor['address']-0x80000000+row*tensor['stride']
                    self.assertEqual(p.memory.image[at:at+tensor['shape'][1]], bytes(tensor['shape'][1]), name)

    def test_new_input_keeps_program(self):
        _, model, x, calibration = next(c for c in fixtures() if c[0] == 'mixed')
        package = compile_model(model, x, calibration)
        with tempfile.TemporaryDirectory(dir=ROOT/'test/int8/runs') as tmp:
            a, b = Path(tmp)/'a', Path(tmp)/'b'
            package.write(a, x.numpy()); package.write(b, (x*0.75-0.125).numpy())
            size = package.metadata['code_bytes']
            self.assertEqual((a/'firmware.bin').read_bytes()[:size], (b/'firmware.bin').read_bytes()[:size])
            self.assertNotEqual((a/'firmware.bin').read_bytes(), (b/'firmware.bin').read_bytes())

    def test_rounding_negative_ties(self):
        np.testing.assert_array_equal(rescale([-3, -1, 1, 3], 1, 1), [-1, 0, 1, 2])

    def test_batch_reuse_contracts(self):
        for name, model, x, calibration in batch_fixtures():
            reuse = compile_model(model, x, calibration)
            sequential = compile_model(model, x, calibration, reuse_batch_weights=False)
            for key, value in reuse.reference(x.numpy()).items():
                np.testing.assert_array_equal(value, sequential.reference(x.numpy())[key], err_msg=name+':'+key)
            if reuse.metadata['batch_weight_reuse']:
                self.assertEqual(reuse.program.labels['cpu_unroll4'] % 16, 0)
                self.assertEqual(reuse.metadata['npu_batch'], x.shape[0])
                self.assertEqual(reuse.metadata['npu_core_starts']*x.shape[0], sequential.metadata['npu_core_starts'])
                self.assertEqual(reuse.metadata['weight_dma_bytes']*x.shape[0], sequential.metadata['weight_dma_bytes'])
                self.assertLessEqual(reuse.metadata['accumulator_scratch_bytes'], 512)
            else:
                self.assertEqual(reuse.memory.image, sequential.memory.image, name)
            self.assertEqual([n.get('weight_bytes') for n in reuse.nodes],
                             [n.get('weight_bytes') for n in sequential.nodes])

    def test_batch_capacity_falls_back(self):
        _, model, x, calibration = next(c for c in batch_fixtures() if c[0] == 'capacity_b4')
        reuse = compile_model(model, x, calibration)
        sequential = compile_model(model, x, calibration, reuse_batch_weights=False)
        self.assertTrue(reuse.metadata['batch_weight_reuse_requested'])
        self.assertFalse(reuse.metadata['batch_weight_reuse'])
        self.assertIn('Code/data overlap', reuse.metadata['batch_weight_reuse_fallback'])
        self.assertEqual(reuse.memory.image, sequential.memory.image)

    def test_batch_new_input_keeps_program(self):
        _, model, x, calibration = next(c for c in batch_fixtures() if c[0] == 'full_b4')
        package = compile_model(model, x, calibration)
        with tempfile.TemporaryDirectory(dir=ROOT/'test/int8/runs') as tmp:
            a, b = Path(tmp)/'a', Path(tmp)/'b'
            package.write(a, x.numpy()); package.write(b, x.flip(0).numpy())
            size = package.metadata['code_bytes']
            self.assertEqual((a/'firmware.bin').read_bytes()[:size], (b/'firmware.bin').read_bytes()[:size])
            self.assertNotEqual((a/'firmware.bin').read_bytes(), (b/'firmware.bin').read_bytes())

    def test_batch_wide_sums_and_zero_shift(self):
        for name, model, x, calibration in batch_fixtures():
            if name not in ('wide_b3', 'shift0_b2'):
                continue
            p = compile_model(model, x, calibration)
            self.assertTrue(p.metadata['batch_weight_reuse'])
            if name == 'wide_b3':
                self.assertGreater(p.nodes[0]['accumulator_bound'], 1 << 21)
            else:
                self.assertEqual(p.nodes[0]['shift'], 0)

    def test_inplace_capture_preserves_caller_inputs(self):
        x = torch.tensor([[-1.0, 2.0]])
        calibration = [-x, x*0.5]
        before = [v.clone() for v in [x]+calibration]
        p = compile_model(nn.ReLU(inplace=True).eval(), x, calibration)
        for value, original in zip([x]+calibration, before):
            self.assertTrue(torch.equal(value, original))
        np.testing.assert_array_equal(p.reference(x.numpy())[p.metadata['output']], [[0, 127]])

    def test_explicit_rejections(self):
        for model, x in ((nn.Sequential(nn.Hardswish()).eval(), torch.ones(1, 4)),
                         (nn.Linear(128, 128).eval(), torch.ones(1, 128)),
                         (nn.Linear(4, 3).train(), torch.ones(1, 4)),
                         (nn.Linear(4, 3).eval(), torch.ones(5, 4))):
            with self.assertRaises((CompileError, ValueError)):
                compile_model(model, x)

    def test_runtime_input_validation(self):
        _, model, x, calibration = fixtures()[0]
        package = compile_model(model, x, calibration)
        with tempfile.TemporaryDirectory(dir=ROOT/'test/int8/runs') as tmp:
            with self.assertRaises(CompileError):
                package.write(Path(tmp)/'nan', np.full((1, 64), np.nan))
            with self.assertRaises(CompileError):
                package.write(Path(tmp)/'shape', np.ones((1, 65)))


if __name__ == '__main__':
    unittest.main(verbosity=2)
