"""Offline planning and exact integer contract for the INT22 tile runtime.

No hardware accumulator is widened. Each <=64-input tile uses zero bias;
the CPU reduces signed partial sums in INT32 and requantizes with a 64-bit
product. Models that cannot fit the 8 KiB image or whose reductions might
overflow INT32 are rejected before execution.
"""
from dataclasses import dataclass

BASE = 0x80000000
CODE_BYTES = 0x800
WORK_OFFSET = 0x17C0
STATUS_OFFSET = 0x1FE0
TILE_N, TILE_K = 32, 64


@dataclass
class Layer:
    weights: list
    bias: list
    mult: int = 1
    shift: int = 0
    requant: bool = False

    def validate(self, k):
        if type(k) is not int or k <= 0:
            raise ValueError('Input width must be a positive integer')
        if not isinstance(self.weights, (list, tuple)) or not self.weights or any(
                not isinstance(row, (list, tuple)) or len(row) != k for row in self.weights):
            raise ValueError('Layer dimensions are inconsistent')
        if not isinstance(self.bias, (list, tuple)) or len(self.bias) != len(self.weights):
            raise ValueError('Bias length differs from output width')
        if any(type(v) is not int or not -128 <= v <= 127
               for row in self.weights for v in row):
            raise ValueError('Weights must be signed INT8')
        if any(type(v) is not int or not -(1 << 31) <= v < (1 << 31) for v in self.bias):
            raise ValueError('Bias must be signed INT32')
        if type(self.mult) is not int or type(self.shift) is not int or not 0 <= self.mult <= 65535 or not 0 <= self.shift <= 31:
            raise ValueError('Unsupported requantization coefficient or shift')
        if type(self.requant) is not bool:
            raise ValueError('Requantization mode must be boolean')
        for row, bias in zip(self.weights, self.bias):
            # Covers signed INT8 inputs even if the preceding layer is ReLU.
            lo = bias + sum(w * (-128 if w >= 0 else 127) for w in row)
            hi = bias + sum(w * (127 if w >= 0 else -128) for w in row)
            if lo < -(1 << 31) or hi > (1 << 31)-1:
                raise ValueError('CPU INT32 reduction could overflow')


def reference(layers, inputs):
    x = list(inputs)
    results = []
    for layer in layers:
        layer.validate(len(x))
        y = [b + sum(w*v for w, v in zip(row, x))
             for row, b in zip(layer.weights, layer.bias)]
        if layer.requant:
            y = [min(127, (max(0, v)*layer.mult +
                          ((1 << (layer.shift-1)) if layer.shift else 0)) >> layer.shift)
                 for v in y]
        results.append(y)
        x = y
    return results


def tiles(n, k):
    """Compile a matrix into output/input blocks; tails are padded by the CPU."""
    if type(n) is not int or type(k) is not int or n <= 0 or k <= 0:
        raise ValueError('Matrix dimensions must be positive')
    return [(nb, kb, min(TILE_N, n-nb), min(TILE_K, k-kb))
            for nb in range(0, n, TILE_N) for kb in range(0, k, TILE_K)]


def plan(layers, inputs):
    if not layers or not all(isinstance(layer, Layer) for layer in layers) or not inputs or any(type(v) is not int or not -128 <= v <= 127 for v in inputs):
        raise ValueError('A nonempty INT8 model/input is required')
    if any(not layer.requant for layer in layers[:-1]):
        raise ValueError('Intermediate layers must produce ReLU-requantized INT8 activations')
    golden = reference(layers, inputs)
    image = bytearray(8192)
    cursor = CODE_BYTES
    allocations = []

    def allocate(name, data, alignment=4):
        nonlocal cursor
        cursor = (cursor+alignment-1) & -alignment
        start = cursor
        cursor += len(data)
        if cursor > WORK_OFFSET:
            raise ValueError('Compact model and activations exceed the 8 KiB SRAM working set')
        image[start:cursor] = data
        allocations.append({'name': name, 'offset': start, 'bytes': len(data)})
        return BASE+start

    def words(values):
        return b''.join((v & 0xffffffff).to_bytes(4, 'little') for v in values)

    x = allocate('input', bytes(v & 255 for v in inputs))
    acc = allocate('cpu_accumulators', bytes(max(len(l.weights) for l in layers)*4))
    descriptors = []
    outputs = []
    tile_count = 0
    k = len(inputs)
    for index, layer in enumerate(layers):
        n = len(layer.weights)
        layer.validate(k)
        w = allocate('weights_%d' % index, bytes(v & 255 for row in layer.weights for v in row))
        b = allocate('bias_%d' % index, words(layer.bias))
        y = allocate('output_%d' % index, bytes(n if layer.requant else n*4))
        g = allocate('golden_%d' % index, bytes(golden[index]) if layer.requant else words(golden[index]))
        descriptors += [x, w, b, y, n, k, layer.mult, layer.shift, int(layer.requant), g]
        outputs.append({'address': y, 'values': golden[index], 'bytes_per_value': 1 if layer.requant else 4})
        tile_count += len(tiles(n, k))
        x, k = y, n
    desc = allocate('descriptors', words(descriptors))
    return {'image': image, 'descriptors': desc, 'accumulators': acc,
            'layer_count': len(layers), 'tile_count': tile_count,
            'allocations': allocations, 'outputs': outputs,
            'compact_end': cursor, 'work_address': BASE+WORK_OFFSET}
