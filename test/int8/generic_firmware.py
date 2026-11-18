"""Generate a descriptor-driven RV32IM INT22 tile runtime for CV32E40P.

The CPU packs weights and input tails at runtime, polls actual DMA/NPU
completion, reduces signed partial sums, and computes every layer output.
Golden values are used only for comparisons after the output was computed.
"""
import json
from assembler import Assembler
from generic_runtime import BASE, CODE_BYTES, STATUS_OFFSET, plan

BENCHMARK_ADDRESS = BASE + 0x1FC0  # After the 2048 B staging area, before STATUS.
BENCHMARK_PHASES = ('setup', 'input_pack', 'weight_pack', 'npu_wait',
                    'read_reduce', 'postprocess', 'cpu_mac')


class RuntimeAssembler(Assembler):
    def __init__(self):
        super().__init__()
        self.compact_li = True

    def immediate(self, name, rd, rs, imm, funct3):
        if not -2048 <= imm <= 2047:
            raise ValueError('Immediate is out of range')
        self.emit(((imm & 4095) << 20) | (rs << 15) | (funct3 << 12) | (rd << 7) | 0x13,
                  '%s x%d,x%d,%d' % (name, rd, rs, imm))

    def slli(self, rd, rs, count):
        self.immediate('slli', rd, rs, count, 1)

    def sll(self, rd, left, right):
        self.register('sll', rd, left, right, 1)

    def srl(self, rd, left, right):
        self.register('srl', rd, left, right, 5)

    def register(self, name, rd, left, right, funct3, funct7=0):
        self.emit((funct7 << 25) | (right << 20) | (left << 15) |
                  (funct3 << 12) | (rd << 7) | 0x33,
                  '%s x%d,x%d,x%d' % (name, rd, left, right))

    def bit_or(self, rd, left, right):
        self.register('or', rd, left, right, 6)

    def sltu(self, rd, left, right):
        self.register('sltu', rd, left, right, 3)

    def mul(self, rd, left, right):
        self.register('mul', rd, left, right, 0, 1)

    def mulhu(self, rd, left, right):
        self.register('mulhu', rd, left, right, 3, 1)

    def lbu(self, rd, rs, offset=0):
        self.emit(((offset & 4095) << 20) | (rs << 15) | (4 << 12) | (rd << 7) | 3,
                  'lbu x%d,%d(x%d)' % (rd, offset, rs))

    def lb(self, rd, rs, offset=0):
        self.emit(((offset & 4095) << 20) | (rs << 15) | (rd << 7) | 3,
                  'lb x%d,%d(x%d)' % (rd, offset, rs))

    def sb(self, value, rs, offset=0):
        imm = offset & 4095
        self.emit(((imm >> 5) << 25) | (value << 20) | (rs << 15) |
                  ((imm & 31) << 7) | 0x23, 'sb x%d,%d(x%d)' % (value, offset, rs))

    def resolve(self):
        super().resolve()
        kinds = {'beq': 0, 'bne': 1, 'blt': 4, 'bge': 5, 'bltu': 6, 'bgeu': 7}
        for item in self.fixups:
            if item[0] in kinds:
                index = item[1]
                self.words[index] = (self.words[index] & ~0x7000) | (kinds[item[0]] << 12)


def _phase(a, name, benchmark):
    if benchmark:
        a.label('bench_' + name)


def _marker(a, value):
    a.li(31, BENCHMARK_ADDRESS); a.li(30, value); a.sw(30, 31)


def _raw_kernel(a, benchmark):
    a.li(11, 0); a.label('n_block'); a.li(12, 0); a.label('k_block')
    # Input MMIO accepts aligned whole words, so pack four byte operands.
    _phase(a, 'input_pack', benchmark)
    a.li(16, 0); a.label('pack_input'); a.li(17, 0)
    for lane in range(4):
        a.add(18, 12, 16); a.addi(18, 18, lane); a.li(20, 0)
        a.branch('bgeu', 18, 10, 'input_zero_%d' % lane)
        a.add(19, 5, 18); a.lbu(20, 19); a.label('input_zero_%d' % lane)
        if lane: a.slli(20, 20, lane*8)
        a.bit_or(17, 17, 20)
    a.add(19, 2, 16); a.sw(17, 19, 0x40)
    a.addi(16, 16, 4); a.li(31, 64); a.branch('bltu', 16, 31, 'pack_input')
    # A word contains [output0 lane0, output0 lane1, output1 lane0,
    # output1 lane1]. The final input/output tile is explicitly zero padded.
    _phase(a, 'weight_pack', benchmark)
    a.li(16, 0); a.addi(22, 3, 0); a.label('pack_k_pair')
    a.li(15, 0); a.label('pack_output_pair'); a.li(17, 0)
    for lane in range(4):
        a.add(18, 11, 15); a.addi(18, 18, lane//2)
        a.add(19, 12, 16); a.addi(19, 19, lane % 2); a.li(21, 0)
        a.branch('bgeu', 18, 9, 'weight_zero_%d' % lane)
        a.branch('bgeu', 19, 10, 'weight_zero_%d' % lane)
        a.mul(20, 18, 10); a.add(20, 20, 19); a.add(20, 20, 6); a.lbu(21, 20)
        a.label('weight_zero_%d' % lane)
        if lane: a.slli(21, 21, lane*8)
        a.bit_or(17, 17, 21)
    a.sw(17, 22); a.addi(22, 22, 4); a.addi(15, 15, 2)
    a.li(31, 32); a.branch('bltu', 15, 31, 'pack_output_pair')
    a.addi(16, 16, 2); a.li(31, 64); a.branch('bltu', 16, 31, 'pack_k_pair')
    _phase(a, 'npu_wait', benchmark)
    a.li(17, 1); a.sw(17, 2); a.li(15, 100000); a.label('poll_done')
    a.lw(17, 2, 4); a.andi(18, 17, 2); a.branch('beq', 18, 0, 'tile_done')
    a.addi(15, 15, -1); a.branch('beq', 15, 0, 'fail'); a.jump('poll_done')
    a.label('tile_done'); a.li(18, 1); a.branch('bne', 17, 18, 'fail')
    _phase(a, 'read_reduce', benchmark)
    a.li(15, 0); a.label('read_partial')
    a.add(18, 11, 15); a.branch('bgeu', 18, 9, 'partials_done')
    a.sw(15, 2, 0x80); a.li(16, 1000); a.label('poll_raw')
    a.lw(17, 2, 0x88); a.andi(17, 17, 1); a.branch('bne', 17, 0, 'partial_ready')
    a.addi(16, 16, -1); a.branch('beq', 16, 0, 'fail'); a.jump('poll_raw')
    a.label('partial_ready'); a.lw(21, 2, 0x84)
    a.slli(20, 18, 2); a.add(20, 20, 8); a.lw(19, 20); a.add(21, 19, 21); a.sw(21, 20)
    a.addi(15, 15, 1); a.li(31, 32); a.branch('bltu', 15, 31, 'read_partial')
    a.label('partials_done'); a.li(17, 2); a.sw(17, 2)
    a.addi(12, 12, 64); a.branch('bltu', 12, 10, 'k_block')
    a.addi(11, 11, 32); a.branch('bltu', 11, 9, 'n_block')


def _cpu_kernel(a, benchmark):
    # Scalar RV32IM, four independent byte pairs per loop iteration. No NPU,
    # DSP extensions, padded work, or golden values participate in this path.
    _phase(a, 'cpu_mac', benchmark)
    a.andi(11, 10, -4); a.li(15, 0); a.label('cpu_row')
    a.mul(18, 15, 10); a.add(18, 6, 18); a.addi(19, 5, 0)
    a.slli(20, 15, 2); a.add(20, 8, 20); a.lw(21, 20); a.li(16, 0)
    a.branch('beq', 11, 0, 'cpu_tail'); a.label('cpu_unroll4')
    for lane in range(4):
        a.lb(17, 18, lane); a.lb(22, 19, lane)
        a.mul(17, 17, 22); a.add(21, 21, 17)
    a.addi(18, 18, 4); a.addi(19, 19, 4); a.addi(16, 16, 4)
    a.branch('bltu', 16, 11, 'cpu_unroll4')
    a.label('cpu_tail'); a.branch('bgeu', 16, 10, 'cpu_row_done')
    a.lb(17, 18); a.lb(22, 19); a.mul(17, 17, 22); a.add(21, 21, 17)
    a.addi(18, 18, 1); a.addi(19, 19, 1); a.addi(16, 16, 1); a.jump('cpu_tail')
    a.label('cpu_row_done'); a.sw(21, 20)
    a.addi(15, 15, 1); a.branch('bltu', 15, 9, 'cpu_row')


def _finish_outputs(a, benchmark):
    # Convert only after all K blocks. RV32 MUL/MULHU form the exact 64-bit
    # nonnegative product; rounding carries into the upper limb.
    _phase(a, 'postprocess', benchmark)
    a.li(15, 0); a.label('finish_output'); a.slli(20, 15, 2); a.add(20, 20, 8); a.lw(21, 20)
    a.branch('beq', 26, 0, 'store_score'); a.branch('blt', 21, 0, 'quant_zero')
    a.mul(17, 21, 24); a.mulhu(18, 21, 24)
    a.branch('beq', 25, 0, 'quant_shifted')
    a.addi(19, 25, -1); a.li(20, 1); a.sll(20, 20, 19)
    a.add(19, 17, 20); a.sltu(20, 19, 17); a.add(18, 18, 20); a.addi(17, 19, 0)
    a.srl(17, 17, 25); a.li(19, 32); a.sub(19, 19, 25)
    a.sll(20, 18, 19); a.bit_or(17, 17, 20); a.srl(18, 18, 25)
    a.label('quant_shifted'); a.branch('bne', 18, 0, 'quant_saturate')
    a.li(19, 128); a.branch('bgeu', 17, 19, 'quant_saturate'); a.addi(21, 17, 0); a.jump('store_hidden')
    a.label('quant_saturate'); a.li(21, 127); a.jump('store_hidden')
    a.label('quant_zero'); a.li(21, 0)
    a.label('store_hidden'); a.add(20, 23, 15); a.sb(21, 20)
    if not benchmark:
        a.add(20, 28, 15); a.lbu(19, 20); a.branch('bne', 21, 19, 'fail')
    a.jump('output_next')
    a.label('store_score'); a.slli(20, 15, 2); a.add(18, 23, 20); a.sw(21, 18)
    if not benchmark:
        a.add(20, 28, 20); a.lw(19, 20); a.branch('bne', 21, 19, 'fail')
    a.label('output_next'); a.addi(15, 15, 1); a.branch('bltu', 15, 9, 'finish_output')


def _check_outputs(a, p):
    # Every layer is checked after END, including intermediate activations.
    a.li(4, p['descriptors']); a.li(27, p['layer_count']); a.label('check_layer')
    for reg, offset in ((23, 12), (9, 16), (26, 32), (28, 36)):
        a.lw(reg, 4, offset)
    a.li(15, 0); a.label('check_output'); a.branch('beq', 26, 0, 'check_score')
    a.add(18, 23, 15); a.lbu(21, 18); a.add(18, 28, 15); a.lbu(19, 18)
    a.jump('check_equal'); a.label('check_score'); a.slli(20, 15, 2)
    a.add(18, 23, 20); a.lw(21, 18); a.add(18, 28, 20); a.lw(19, 18)
    a.label('check_equal'); a.branch('bne', 21, 19, 'fail')
    a.addi(15, 15, 1); a.branch('bltu', 15, 9, 'check_output')
    a.addi(4, 4, 40); a.addi(27, 27, -1); a.branch('bne', 27, 0, 'check_layer')


def build(directory, layers, inputs, *, backend='raw', benchmark=False):
    if backend not in ('raw', 'cpu'):
        raise ValueError('Unknown GEMV backend: ' + backend)
    p = plan(layers, inputs)
    a = RuntimeAssembler()
    if benchmark:
        _marker(a, 1)
    # Persistent registers: x2 MMIO, x3 W1 staging, x4 descriptor, x8 CPU
    # accumulator buffer, x27 remaining layers. No stack or hidden memory.
    if backend == 'raw':
        a.li(2, 0x70000000); a.li(3, p['work_address'])
    a.li(4, p['descriptors']); a.li(8, p['accumulators']); a.li(27, p['layer_count'])
    if backend == 'raw':
        a.li(17, 1); a.sw(17, 2, 0x3c); a.sw(17, 2, 0x18); a.sw(3, 2, 0x20)
        # W2 deliberately remains reset/invalid: RAW mode must never need it.
        a.li(18, 0x700009c0); a.li(15, 32); a.label('clear_bias')
        a.sw(0, 18); a.addi(18, 18, 4); a.addi(15, 15, -1); a.branch('bne', 15, 0, 'clear_bias')
    a.label('layer'); _phase(a, 'setup', benchmark)
    for reg, offset in ((5, 0), (6, 4), (7, 8), (23, 12), (9, 16), (10, 20),
                        (24, 24), (25, 28), (26, 32), (28, 36)):
        a.lw(reg, 4, offset)
    # Initialize CPU sums from bias exactly once per layer, never per K tile.
    a.li(15, 0); a.label('copy_bias'); a.slli(18, 15, 2)
    a.add(19, 7, 18); a.lw(21, 19); a.add(19, 8, 18); a.sw(21, 19)
    a.addi(15, 15, 1); a.branch('bltu', 15, 9, 'copy_bias')
    (_raw_kernel if backend == 'raw' else _cpu_kernel)(a, benchmark)
    _finish_outputs(a, benchmark)
    a.addi(4, 4, 40); a.addi(27, 27, -1); a.branch('bne', 27, 0, 'layer')
    # Leave the legacy default mode available after the generic task sequence.
    if backend == 'raw':
        a.sw(0, 2, 0x3c); a.lw(17, 2, 0x3c); a.branch('bne', 17, 0, 'fail')
    if benchmark:
        _marker(a, 2)
        _check_outputs(a, p)
    a.li(17, 0xc0dec0de); a.jump('exit')
    a.label('fail'); a.li(17, 0xdeadbeef)
    a.label('exit'); a.li(18, BASE+STATUS_OFFSET); a.sw(17, 18); a.label('halt'); a.jump('halt')
    a.resolve()
    if len(a.words)*4 > CODE_BYTES:
        raise ValueError('Runtime code exceeds its SRAM reservation')
    for index, word in enumerate(a.words):
        p['image'][index*4:index*4+4] = word.to_bytes(4, 'little')
    directory.mkdir(parents=True, exist_ok=True)
    (directory/'firmware.hex').write_text(''.join('%08x\n' % int.from_bytes(p['image'][i:i+4], 'little') for i in range(0, 8192, 4)))
    (directory/'firmware.S').write_text('\n'.join(a.listing)+'\n')
    meta = {k: v for k, v in p.items() if k != 'image'}
    meta.update(code_bytes=len(a.words)*4, accumulator_bits=22, cpu_reduction_bits=32,
                cpu_requant_product_bits=64, hardware_training=False)
    if benchmark or backend != 'raw':
        meta.update(backend=backend, benchmark=benchmark)
    if benchmark:
        meta.update(benchmark_address=BENCHMARK_ADDRESS,
                    phase_pcs={name: a.labels.get('bench_' + name, 0) for name in BENCHMARK_PHASES})
    (directory/'firmware_meta.json').write_text(json.dumps(meta, indent=2)+'\n')
    return meta
