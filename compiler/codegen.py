"""Current RAW ABI, INT32 CPU reduction, and registered graph CPU kernels.

Elementwise/Softmax kernel schedules follow main@4b552b1. FC work reuses this
branch's four-way RV32IM kernel and prepacked RAW-core/CPU-fringe implementation.
"""
import struct

from .runtime import BASE, _cpu_kernel, _full_blocks, _marker
from .rv32 import Program


class Codegen:
    def __init__(self, memory, tensors, accumulator, has_raw):
        self.m, self.ts, self.acc, self.has_raw = memory, tensors, accumulator, has_raw
        self.a = a = Program()
        _marker(a, 1)
        if has_raw:
            a.li(2, 0x70000000); a.li(17, 1)
            a.sw(17, 2, 0x3c); a.sw(17, 2, 0x18)
            a.li(18, 0x700009c0); a.li(15, 32); a.label('zero_hw_bias')
            a.sw(0, 18); a.addi(18, 18, 4); a.addi(15, 15, -1)
            a.branch('bne', 15, 0, 'zero_hw_bias')
        self.clips()

    def clips(self):
        self.a.li(30, -128); self.a.li(31, 127)

    def quant(self, node, already_scaled=False):
        a = self.a
        if not already_scaled:
            a.mul(10, 10, 17)
        if node['shift']:
            a.add(10, 10, 18); a.srai(10, 10, node['shift'])
        low, high = a.fresh('clip_low'), a.fresh('clip_high')
        a.branch('bge', 10, 30, low); a.addi(10, 30, 0); a.label(low)
        a.branch('bge', 31, 10, high); a.addi(10, 31, 0); a.label(high)

    def setup_quant(self, node):
        self.a.li(17, node['mult'][0])
        self.a.li(18, (1 << (node['shift']-1)) if node['shift'] else 0)

    def linear(self, node):
        a = self.a
        dst = self.ts[node['name']]
        for sample, descriptor in enumerate(node['descriptors']):
            done = a.fresh('fc_return')
            a.li(4, descriptor); a.li(29, node['extension'])
            a.la(1, done); a.jump('fc_runtime'); a.label(done)
            self.clips(); self.setup_quant(node)
            a.li(5, self.acc); a.li(6, dst['address']+sample*dst['stride'])
            a.li(7, dst['shape'][1]); loop = a.fresh('fc_quant'); a.label(loop)
            a.lw(10, 5); self.quant(node); a.sb(10, 6)
            a.addi(5, 5, 4); a.addi(6, 6, 1); a.addi(7, 7, -1)
            a.branch('bne', 7, 0, loop)

    def matrix_runtime(self):
        a = self.a
        a.label('fc_runtime')
        for reg, offset in ((5, 0), (6, 4), (7, 8), (23, 12), (9, 16), (10, 20)):
            a.lw(reg, 4, offset)
        a.li(8, self.acc); a.li(15, 0); a.label('fc_bias')
        a.slli(18, 15, 2); a.add(19, 7, 18); a.lw(21, 19)
        a.add(19, 8, 18); a.sw(21, 19); a.addi(15, 15, 1)
        a.branch('bltu', 15, 9, 'fc_bias')
        if self.has_raw:
            a.lw(13, 29); a.lw(14, 29, 4)
            a.branch('beq', 13, 0, 'fc_cpu_all'); a.branch('beq', 14, 0, 'fc_cpu_all')
            _full_blocks(a)
            a.sub(10, 10, 14); a.branch('beq', 10, 0, 'fc_bottom')
            a.lw(6, 29, 8); a.add(5, 5, 14); a.addi(9, 13, 0)
            a.li(12, 1); a.jump('fc_cpu_segment')
            a.label('fc_bottom'); a.lw(9, 4, 16); a.sub(9, 9, 13)
            a.branch('beq', 9, 0, 'fc_return'); a.lw(10, 4, 20)
            a.lw(5, 4); a.lw(6, 29, 12); a.li(8, self.acc)
            a.slli(18, 13, 2); a.add(8, 8, 18); a.li(12, 2); a.jump('fc_cpu_segment')
            a.label('fc_cpu_all'); a.li(12, 2); a.label('fc_cpu_segment')
        _cpu_kernel(a, False)
        if self.has_raw:
            a.li(17, 1); a.branch('beq', 12, 17, 'fc_bottom'); a.label('fc_return')
        a.jalr(0, 1)

    def softmax(self, node):
        a = self.a; src = self.ts[node['inputs'][0]]; dst = self.ts[node['name']]
        batch, n = dst['shape']; a.li(17, node['lut_address']); a.li(19, node['reciprocal'])
        for sample in range(batch):
            start = src['address']+sample*src['stride']
            a.li(5, start); a.li(7, n); a.li(14, -128)
            loop, skip = a.fresh('softmax_max'), a.fresh('keep_max'); a.label(loop); a.lb(10, 5)
            a.branch('bge', 14, 10, skip); a.addi(14, 10, 0); a.label(skip)
            a.addi(5, 5, 1); a.addi(7, 7, -1); a.branch('bne', 7, 0, loop)
            a.li(5, start); a.li(7, n); a.li(15, 0)
            loop = a.fresh('softmax_sum'); a.label(loop); a.lb(10, 5)
            a.sub(10, 10, 14); a.addi(10, 10, 255); a.slli(10, 10, 1)
            a.add(10, 10, 17); a.lhu(10, 10); a.add(15, 15, 10)
            a.addi(5, 5, 1); a.addi(7, 7, -1); a.branch('bne', 7, 0, loop)
            a.li(5, start); a.li(6, dst['address']+sample*dst['stride']); a.li(7, n)
            a.srai(18, 15, 1); loop, clip = a.fresh('softmax_normalize'), a.fresh('softmax_clip')
            a.label(loop); a.lb(10, 5); a.sub(10, 10, 14); a.addi(10, 10, 255)
            a.slli(10, 10, 1); a.add(10, 10, 17); a.lhu(10, 10)
            a.mul(10, 10, 19); a.add(10, 10, 18); a.divu(10, 10, 15)
            a.branch('bge', 31, 10, clip); a.addi(10, 31, 0); a.label(clip); a.sb(10, 6)
            a.addi(5, 5, 1); a.addi(6, 6, 1); a.addi(7, 7, -1); a.branch('bne', 7, 0, loop)

    def elementwise(self, node):
        a = self.a; src = self.ts[node['inputs'][0]]; dst = self.ts[node['name']]
        batch, n = dst['shape']; op = node['op']
        if op not in ('sigmoid', 'tanh'):
            self.setup_quant(node)
        else:
            a.li(17, node['lut_address'])
        if op in ('add', 'sub'):
            a.li(19, node['mult'][1])
        if op == 'relu6':
            a.li(19, node['clamp_max'])
        if op == 'leaky_relu':
            a.li(19, node['negative_mult'])
            a.li(20, (1 << (node['negative_shift']-1)) if node['negative_shift'] else 0)
        for sample in range(batch):
            a.li(5, src['address']+sample*src['stride'])
            a.li(6, dst['address']+sample*dst['stride']); a.li(7, n)
            if len(node['inputs']) == 2:
                other = self.ts[node['inputs'][1]]; a.li(12, other['address']+sample*other['stride'])
            loop = a.fresh('cpu_'+op); a.label(loop); a.lb(10, 5)
            if op in ('relu', 'relu6'):
                label = a.fresh('relu'); a.branch('bge', 10, 0, label); a.addi(10, 0, 0); a.label(label)
            if op in ('sigmoid', 'tanh'):
                a.addi(10, 10, 128); a.add(10, 10, 17); a.lb(10, 10)
            else:
                if op in ('add', 'sub', 'mul') and len(node['inputs']) == 2:
                    a.lb(11, 12); a.addi(12, 12, 1)
                    if op == 'mul':
                        a.mul(10, 10, 11)
                    else:
                        a.mul(10, 10, 17); a.mul(11, 11, 19); a.add(10, 10, 11)
                if op in ('add', 'sub') and len(node['inputs']) == 1:
                    a.mul(10, 10, 17); a.add(10, 10, 19)
                if op == 'leaky_relu':
                    positive, finished = a.fresh('leaky_positive'), a.fresh('leaky_done')
                    a.branch('bge', 10, 0, positive); a.mul(10, 10, 19)
                    if node['negative_shift']:
                        a.add(10, 10, 20); a.srai(10, 10, node['negative_shift'])
                    self.quant(dict(node, shift=0), True); a.jump(finished); a.label(positive)
                    self.quant(node); a.label(finished)
                else:
                    self.quant(node, op in ('add', 'sub'))
                if op == 'relu6':
                    clipped = a.fresh('relu6_cap'); a.branch('bge', 19, 10, clipped)
                    a.addi(10, 19, 0); a.label(clipped)
            a.sb(10, 6); a.addi(5, 5, 1); a.addi(6, 6, 1); a.addi(7, 7, -1)
            a.branch('bne', 7, 0, loop)

    def finish(self, linear_present):
        a = self.a
        if self.has_raw:
            a.li(2, 0x70000000); a.sw(0, 2, 0x3c); a.lw(17, 2, 0x3c)
            a.branch('bne', 17, 0, 'fail')
        _marker(a, 2)
        a.li(17, 0xc0dec0de); a.jump('exit'); a.label('fail'); a.li(17, 0xdeadbeef)
        a.label('exit'); a.li(18, BASE+0x1fe0); a.sw(17, 18); a.label('halt'); a.jump('halt')
        if linear_present:
            self.matrix_runtime()
        a.resolve()
        code = struct.pack('<%dI' % len(a.words), *a.words)
        if len(code) > self.m.top:
            raise ValueError('Code/data overlap: code=%dB available=%dB; SRAM total=8192B' % (len(code), self.m.top))
        self.m.image[:len(code)] = code
        return a
