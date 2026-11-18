"""main FX/INT8 frontend targeting this branch's index/ready/data RAW ABI.

The calibrated graph integer contract follows main@4b552b1. An FC's complete
mathematical sum may exceed INT22: only unbiased 64-term blocks run on the NPU,
and the existing CPU INT32 reduction completes the sum before quantization.
"""
import hashlib
from copy import deepcopy
import json
from pathlib import Path
import struct

import numpy as np

from .codegen import Codegen
from .frontend import CompileError, capture
from .runtime import BASE, Layer, pack_layer, source_hashes

DATA_TOP = 0x1fc0


class CapacityError(CompileError):
    """A schedule does not fit SRAM; another schedule may still fit."""


def quantize(value, scale):
    value = np.asarray(value)
    if not np.isfinite(value).all():
        raise CompileError('Nonfinite runtime input or quantization value')
    return np.clip(np.rint(value/scale), -128, 127).astype(np.int8)


def coefficients(ratios, bounds):
    for shift in range(24, -1, -1):
        mult = [int(round(r*(1 << shift))) for r in ratios]
        bound = sum(abs(m)*b for m, b in zip(mult, bounds)) + ((1 << (shift-1)) if shift else 0)
        if all(abs(m) < (1 << 30) for m in mult) and bound < (1 << 31):
            return mult, shift
    raise CompileError('CPU fixed-point rescaling cannot fit INT32')


def rescale(value, mult, shift):
    result = np.asarray(value, dtype=np.int64)*mult
    if shift:
        result = (result+(1 << (shift-1))) >> shift
    return np.clip(result, -128, 127).astype(np.int8)


class Memory:
    def __init__(self):
        self.top = DATA_TOP
        self.image = bytearray(8192)
        self.allocations = []

    def alloc(self, name, size, data=None, alignment=4):
        if size < 0 or alignment < 4 or alignment & (alignment-1):
            raise CompileError('Invalid allocation size/alignment')
        self.top = (self.top-size) & -alignment
        if self.top < 0:
            raise CapacityError('Data exceed 8 KiB SRAM')
        if data is not None:
            if len(data) != size:
                raise CompileError('Internal allocation size mismatch')
            self.image[self.top:self.top+size] = data
        address = BASE+self.top
        self.allocations.append(dict(name=name, address=address, bytes=size))
        return address

    def words(self, name, words):
        data = struct.pack('<%dI' % len(words), *(word & 0xffffffff for word in words))
        return self.alloc(name, len(data), data)

    def check_code_size(self, size):
        if size > self.top:
            raise CapacityError('Code/data overlap: code=%dB available=%dB; SRAM total=8192B' % (size, self.top))


class Package:
    def __init__(self, graph, nodes, memory, program, metadata):
        self.graph, self.nodes, self.memory, self.program, self.metadata = graph, nodes, memory, program, metadata

    def reference(self, x):
        ts = self.graph['tensors']
        values = {self.graph['input']: quantize(x, ts[self.graph['input']]['scale'])}
        for node in self.nodes:
            op = node['op']; args = [values[n].astype(np.int64) for n in node['inputs']]
            if op == 'linear':
                value = args[0] @ node['qweight'].T.astype(np.int64) + node['qbias']
                output = rescale(value, node['mult'][0], node['shift'])
            elif op in ('sigmoid', 'tanh'):
                output = node['lut'][args[0]+128]
            elif op == 'softmax':
                ex = node['lut'][args[0]-args[0].max(axis=1, keepdims=True)+255].astype(np.int64)
                total = ex.sum(axis=1, keepdims=True)
                output = np.clip((ex*node['reciprocal']+total//2)//total, 0, 127).astype(np.int8)
            elif op in ('relu', 'relu6', 'leaky_relu', 'identity'):
                output = rescale(np.maximum(args[0], 0) if op in ('relu', 'relu6') else args[0],
                                 node['mult'][0], node['shift'])
                if op == 'relu6':
                    output = np.minimum(output, node['clamp_max']).astype(np.int8)
                if op == 'leaky_relu':
                    output = np.where(args[0] < 0,
                                      rescale(args[0], node['negative_mult'], node['negative_shift']), output).astype(np.int8)
            elif op == 'mul':
                output = rescale(args[0]*(args[1] if len(args) > 1 else 1), node['mult'][0], node['shift'])
            else:
                value = args[0]*node['mult'][0] + (args[1] if len(args) > 1 else 1)*node['mult'][1]
                if node['shift']:
                    value = (value+(1 << (node['shift']-1))) >> node['shift']
                output = np.clip(value, -128, 127).astype(np.int8)
            values[node['name']] = output
        return values

    def write(self, directory, x):
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        image = bytearray(self.memory.image)
        tensor = self.graph['tensors'][self.graph['input']]
        q = quantize(x, tensor['scale'])
        if list(q.shape) != tensor['shape']:
            raise CompileError('Runtime input shape differs from compiled shape')
        for row, values in enumerate(q):
            start = tensor['address']-BASE+row*tensor['stride']
            image[start:start+len(values)] = values.tobytes()
        (directory/'firmware.hex').write_text(''.join('%08x\n' % w for w in struct.unpack('<2048I', image)))
        (directory/'firmware.bin').write_bytes(image)
        (directory/'firmware.S').write_text('\n'.join(self.program.listing)+'\n')
        (directory/'manifest.json').write_text(json.dumps(self.metadata, indent=2)+'\n')
        values = self.reference(x)
        (directory/'reference.json').write_text(json.dumps({name: value.tolist() for name, value in values.items()}, indent=2)+'\n')
        return values


def compile_model(model, example_input, calibration_inputs=None, force_cpu=False, *, reuse_batch_weights=True):
    # FX executes the model during calibration. A supported in-place activation
    # must not mutate the caller's representative or reusable calibration data.
    calibration = None if calibration_inputs is None else [x.detach().clone() for x in calibration_inputs]
    graph = capture(model, example_input.detach().clone(), calibration)
    try:
        return _compile_graph(graph, force_cpu, reuse_batch_weights)
    except CapacityError as error:
        if force_cpu or not reuse_batch_weights:
            raise
        # A larger batch scratch/code must not reject an existing deployment.
        package = _compile_graph(graph, force_cpu, False)
        package.metadata['batch_weight_reuse_requested'] = True
        package.metadata['batch_weight_reuse_fallback'] = str(error)
        return package


def _compile_graph(captured, force_cpu, reuse_batch_weights):
    # Allocation/codegen mutate these dictionaries. A capacity retry starts
    # from the same calibrated graph and exact integer contract.
    graph = dict(captured, nodes=deepcopy(captured['nodes']), tensors=deepcopy(captured['tensors']))
    nodes, tensors, memory = graph['nodes'], graph['tensors'], Memory()
    if not nodes:
        raise CompileError('At least one supported graph operator is required')
    for name, tensor in tensors.items():
        batch, width = tensor['shape']
        tensor['stride'] = (width+3)//4*4
        tensor['address'] = memory.alloc('tensor:'+name, batch*tensor['stride'])
    linears = [node for node in nodes if node['op'] == 'linear']
    for node in linears:
        batch, n = tensors[node['name']]['shape']
        k = tensors[node['inputs'][0]]['shape'][1]
        node['batch_weight_reuse'] = bool(reuse_batch_weights and not force_cpu and batch > 1 and n >= 32 and k >= 64)
    scratch_words = max((tensors[n['name']]['shape'][0]*32 if n['batch_weight_reuse']
                         else tensors[n['name']]['shape'][1] for n in linears), default=0)
    accumulator = memory.alloc('cpu_int32_accumulators', scratch_words*4) if linears else 0
    raw_starts = 0
    dma_ranges = []
    for node in nodes:
        op = node['op']; src = [tensors[n] for n in node['inputs']]; output = tensors[node['name']]
        node.update(backend='CPU', reason='Registered CPU graph kernel')
        if op == 'linear':
            weights, bias = node.pop('weight'), node.pop('bias')
            sw = max(float(np.abs(weights).max())/127, 1e-12)
            qw = np.clip(np.rint(weights/sw), -127, 127).astype(np.int8)
            qb64 = np.rint(bias/(src[0]['scale']*sw))
            if not np.isfinite(qb64).all() or np.abs(qb64).max() >= (1 << 31):
                raise CompileError(node['name']+': bias cannot fit INT32')
            qb = qb64.astype(np.int32)
            w64 = qw.astype(np.int64)
            lo = qb.astype(np.int64)+np.minimum(-128*w64, 127*w64).sum(axis=1)
            hi = qb.astype(np.int64)+np.maximum(-128*w64, 127*w64).sum(axis=1)
            if lo.min() < -(1 << 31) or hi.max() >= (1 << 31):
                raise CompileError(node['name']+': CPU accumulation may overflow INT32')
            bound = int(max(np.abs(lo).max(), np.abs(hi).max()))
            node.update(qweight=qw, qbias=qb, accumulator_bound=bound, weight_scale=sw)
            node['mult'], node['shift'] = coefficients([src[0]['scale']*sw/output['scale']], [bound])
            batch, k = src[0]['shape']; n = output['shape'][1]
            packed, nf, kf = pack_layer(Layer(qw.tolist(), qb.tolist()))
            if force_cpu:
                packed, nf, kf = qw.tobytes(), 0, 0
            weights_address = memory.alloc(node['name']+':weights', len(packed), packed)
            bias_address = memory.alloc(node['name']+':bias', qb.nbytes, qb.astype('<i4').tobytes())
            if node['batch_weight_reuse']:
                descriptor = [src[0]['address'], weights_address, bias_address, output['address'], n, k,
                              batch, src[0]['stride'], output['stride'], nf, kf,
                              weights_address+nf*kf, weights_address+nf*k, node['mult'][0], node['shift']]
                node['batch_descriptor'] = memory.words(node['name']+':batch_dispatch', descriptor)
            else:
                node['extension'] = memory.words(node['name']+':dispatch', [nf, kf, weights_address+nf*kf, weights_address+nf*k])
                node['descriptors'] = [memory.words(node['name']+':sample_%d' % b,
                                      [src[0]['address']+b*src[0]['stride'], weights_address, bias_address,
                                       output['address']+b*output['stride'], n, k]) for b in range(batch)]
            count = nf//32*(kf//64)*(1 if node['batch_weight_reuse'] else batch)
            node.update(raw_tiles=count,
                        raw_macs=nf*kf*batch, cpu_macs=(n*k-nf*kf)*batch,
                        weight_address=weights_address, weight_bytes=len(packed), bias_address=bias_address)
            if count:
                node.update(backend='RAW+CPU', reason='Prepacked full 32x64 blocks; CPU INT32 reduction and compact fringes')
                dma_ranges.append([weights_address, weights_address+nf*kf])
            raw_starts += count
        elif op == 'softmax':
            reciprocal = int(round(1/output['scale']))
            maximum = min(32767, ((1 << 31)-1)//max(1, reciprocal+output['shape'][1]))
            if maximum < 1:
                raise CompileError('Softmax scale is too small for INT32 normalization')
            lut = np.rint(np.exp(np.arange(-255, 1)*src[0]['scale'])*maximum).astype('<u2')
            node.update(lut=lut, reciprocal=reciprocal,
                        lut_address=memory.alloc(node['name']+':exp_lut', 512, lut.tobytes()))
        elif op in ('sigmoid', 'tanh'):
            values = np.arange(-128, 128, dtype=np.float64)*src[0]['scale']
            fn = (lambda x: 1/(1+np.exp(-np.clip(x, -700, 700)))) if op == 'sigmoid' else np.tanh
            lut = quantize(fn(values), output['scale'])
            node.update(lut=lut, lut_address=memory.alloc(node['name']+':lut', 256, lut.tobytes()))
        else:
            if op in ('add', 'sub'):
                if 'scalar' in node:
                    ratios = [src[0]['scale']/output['scale']*(-1 if op == 'sub' and node['scalar_left'] else 1),
                              node['scalar']/output['scale']*(-1 if op == 'sub' and not node['scalar_left'] else 1)]
                    bounds = [128, 1]
                else:
                    ratios = [src[0]['scale']/output['scale'], src[1]['scale']/output['scale']*(-1 if op == 'sub' else 1)]
                    bounds = [128, 128]
            else:
                ratio = src[0]['scale']*((node['scalar'] if 'scalar' in node else src[1]['scale']) if op == 'mul' else 1)/output['scale']
                ratios, bounds = [ratio], [16384 if op == 'mul' and 'scalar' not in node else 128]
            node['mult'], node['shift'] = coefficients(ratios, bounds)
            if op == 'relu6':
                node['clamp_max'] = min(127, max(0, int(round(6/output['scale']))))
            if op == 'leaky_relu':
                mult, shift = coefficients([src[0]['scale']*node['negative_slope']/output['scale']], [128])
                node.update(negative_mult=mult[0], negative_shift=shift)
    batched_raw = any(n['batch_weight_reuse'] for n in linears)
    single_raw = any(n['raw_tiles'] and not n['batch_weight_reuse'] for n in linears)
    generator = Codegen(memory, tensors, accumulator, bool(raw_starts), single_raw=single_raw, batched_raw=batched_raw)
    for node in nodes:
        node['start_pc'] = BASE+len(generator.a.words)*4
        getattr(generator, 'linear' if node['op'] == 'linear' else 'softmax' if node['op'] == 'softmax' else 'elementwise')(node)
        node['end_pc'] = BASE+len(generator.a.words)*4
    try:
        program = generator.finish(bool(linears))
    except CapacityError:
        raise
    except (ValueError, AssertionError) as error:
        raise CompileError(str(error)) from error
    reported_nodes = [{k: v for k, v in node.items() if k not in ('qweight', 'qbias', 'lut')} for node in nodes]
    metadata = dict(target='int22-raw-v1', kind='pytorch', frontend_commit='4b552b1',
                    input=graph['input'], output=graph['output'], tensors=tensors, nodes=reported_nodes,
                    input_shape=tensors[graph['input']]['shape'], npu_core_starts=raw_starts,
                    npu_batch=tensors[graph['input']]['shape'][0] if batched_raw else 1,
                    batch_weight_reuse_requested=bool(reuse_batch_weights), batch_weight_reuse=batched_raw,
                    batch_weight_reuse_fallback=None, accumulator_scratch_bytes=scratch_words*4,
                    weight_dma_bytes=raw_starts*2048,
                    dma_ranges=dma_ranges, cpu_unroll=4, task_engine=False,
                    raw_registers={'index': 0x80, 'data': 0x84, 'ready': 0x88},
                    accumulator_bits=22, cpu_reduction_bits=32,
                    quantization='Calibrated symmetric INT8; zero point 0; fixed-point round toward +infinity at ties; INT8 graph boundaries',
                    code_bytes=len(program.words)*4, data_bytes=DATA_TOP-memory.top,
                    free_bytes=memory.top-len(program.words)*4, allocations=memory.allocations,
                    code_sha256=hashlib.sha256(memory.image[:len(program.words)*4]).hexdigest(),
                    source_sha256=source_hashes())
    return Package(graph, nodes, memory, program, metadata)
