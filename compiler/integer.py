"""Deployment wrapper preserving every byte of the existing integer firmware."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

from .runtime import (BASE, build_dynamic, build_optimized, plan, reference,
                      source_hashes)


class IntegerPackage:
    def __init__(self, layers, inputs, force_cpu):
        self.layers, self.inputs, self.force_cpu = deepcopy(layers), list(inputs), force_cpu
        plan(self.layers, self.inputs)

    def write(self, directory, inputs=None):
        x = list(self.inputs if inputs is None else inputs)
        if len(x) != len(self.inputs):
            raise ValueError('Runtime input shape differs from compiled shape')
        directory = Path(directory)
        p = plan(self.layers, x)
        meta = (build_dynamic(directory, self.layers, x, backend='cpu', benchmark=True)
                if self.force_cpu else build_optimized(directory, self.layers, x, benchmark=True))
        image = b''.join(int(w, 16).to_bytes(4, 'little') for w in (directory/'firmware.hex').read_text().splitlines())
        (directory/'firmware.bin').write_bytes(image)
        allocations = {item['name']: item for item in p['allocations']}
        tensors = {'input': dict(address=BASE+allocations['input']['offset'], shape=[1, len(x)],
                                 stride=len(x), dtype='int8')}
        values = {'input': [x]}
        for i, (output, row) in enumerate(zip(p['outputs'], reference(self.layers, x))):
            name = 'layer_%d' % i
            width = output['bytes_per_value']
            tensors[name] = dict(address=output['address'], shape=[1, len(row)],
                                 stride=len(row)*width, dtype='int8' if width == 1 else 'int32')
            values[name] = [row]
        golden_ranges = [[BASE+a['offset'], BASE+a['offset']+a['bytes']]
                         for a in p['allocations'] if a['name'].startswith('golden_')]
        meta.update(target='int22-raw-v1', kind='integer', input='input', output='layer_%d' % (len(self.layers)-1),
                    tensors=tensors, nodes=[dict(name='layer_%d' % i) for i in range(len(self.layers))],
                    npu_core_starts=0 if self.force_cpu else meta['tile_count'],
                    dma_ranges=meta.get('dma_ranges', []), golden_ranges=golden_ranges,
                    cpu_unroll=4, task_engine=False, source_sha256=source_hashes(),
                    code_sha256=hashlib.sha256(image[:meta['code_bytes']]).hexdigest())
        (directory/'manifest.json').write_text(json.dumps(meta, indent=2)+'\n')
        (directory/'reference.json').write_text(json.dumps(values, indent=2)+'\n')
        self.metadata = meta
        return values


def compile_layers(layers, inputs, force_cpu=False):
    """Keep Layer's ReLU/64-bit requantization and optional INT32 final scores."""
    return IntegerPackage(layers, inputs, force_cpu)
