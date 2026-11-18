"""Matched original HAR arithmetic: wrap22 -> ReLU/requant -> wrap22 -> argmax.

The NPU path uses the existing reuse8 firmware loader/copy schedule. The CPU
path uses the existing four-element RV32IM dot product with the same trained
integer operands. Both publish hidden/scores/classes to the same SRAM slots
before END, and compare the same golden words strictly after END.
"""
import hashlib
import json
from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from compiler.rv32 import Program
from compiler.runtime import _cpu_kernel, _marker
from generic_firmware import _finish_outputs
from firmware import build as build_har
from run import make_case

BASE = 0x80000000
ACTUAL = 0x1d00
DESCRIPTORS = 0x800
ACCUMULATORS = 0xa00


def build_cpu(directory, seed, batch):
    mem = make_case(seed)
    if not 1 <= batch <= mem[0x1f08//4]:
        raise ValueError('Batch must select a prefix of the original fixture')
    mem[0x1f08//4] = batch
    w1 = mem[0x1f0c//4]-BASE
    image = bytearray(struct.pack('<2048I', *mem))
    first, second = bytes(image[w1:w1+2048]), bytes(image[0x1800:0x18c0])
    # The CPU consumes the same logical weights in compact row-major order.
    image[w1:w1+2048] = bytes(first[(i//2)*64+o*2+i%2] for o in range(32) for i in range(64))
    image[0x1800:0x18c0] = bytes(second[i*6+o] for o in range(6) for i in range(32))
    descriptors = []
    mult, shift = mem[0x1f00//4], mem[0x1f04//4]
    for sample in range(batch):
        output = BASE+ACTUAL+sample*64
        descriptors += [BASE+0x1a00+sample*64, BASE+w1, BASE+0x1900, output, 32, 64, mult, shift, 1]
        descriptors += [output, BASE+0x1800, BASE+0x1980, output+32, 6, 32, 1, 0, 0]
    data = struct.pack('<%dI' % len(descriptors), *descriptors)
    image[DESCRIPTORS:DESCRIPTORS+len(data)] = data
    a = Program(); _marker(a, 1)
    for sample in range(batch):
        for layer in range(2):
            done = a.fresh('layer_return')
            a.li(4, BASE+DESCRIPTORS+(sample*2+layer)*36)
            a.la(1, done); a.jump('cpu_layer'); a.label(done)
        a.li(5, BASE+ACTUAL+sample*64+32); a.lw(19, 5)
        a.li(7, 1); a.li(21, 0); loop, keep = a.fresh('argmax'), a.fresh('keep_class')
        a.label(loop); a.lw(20, 5, 4); a.branch('bge', 19, 20, keep)
        a.addi(19, 20, 0); a.addi(21, 7, 0); a.label(keep)
        a.addi(5, 5, 4); a.addi(7, 7, 1); a.li(17, 6); a.branch('bltu', 7, 17, loop)
        a.li(18, BASE+ACTUAL+sample*64+56); a.sw(21, 18)
    _marker(a, 2)
    for sample in range(batch):
        a.li(5, BASE+ACTUAL+sample*64); a.li(6, BASE+0x1c00+sample*64); a.li(7, 15)
        loop = a.fresh('verify'); a.label(loop); a.lw(8, 5); a.lw(9, 6)
        a.branch('bne', 8, 9, 'fail'); a.addi(5, 5, 4); a.addi(6, 6, 4)
        a.addi(7, 7, -1); a.branch('bne', 7, 0, loop)
    a.li(17, 0xc0dec0de); a.jump('exit'); a.label('fail'); a.li(17, 0xdeadbeef)
    a.label('exit'); a.li(18, BASE+0x1fe0); a.sw(17, 18); a.label('halt'); a.jump('halt')
    a.label('cpu_layer')
    for reg, offset in ((5, 0), (6, 4), (7, 8), (23, 12), (9, 16), (10, 20),
                        (24, 24), (25, 28), (26, 32)):
        a.lw(reg, 4, offset)
    a.li(8, BASE+ACCUMULATORS); a.li(15, 0); a.label('bias')
    a.slli(18, 15, 2); a.add(19, 7, 18); a.lw(21, 19)
    a.add(19, 8, 18); a.sw(21, 19); a.addi(15, 15, 1); a.branch('bltu', 15, 9, 'bias')
    _cpu_kernel(a, False)
    # Wrapping once after the sum equals wrapping after each addition. Every
    # unwrapped HAR sum fits INT32 (<=64 INT8 products plus one INT22 bias).
    a.li(15, 0); a.label('wrap22'); a.slli(20, 15, 2); a.add(20, 8, 20)
    a.lw(21, 20); a.slli(21, 21, 10); a.srai(21, 21, 10); a.sw(21, 20)
    a.addi(15, 15, 1); a.branch('bltu', 15, 9, 'wrap22')
    _finish_outputs(a, True); a.jalr(0, 1); a.resolve()
    if len(a.words)*4 > DESCRIPTORS:
        raise ValueError('CPU benchmark code overlaps descriptors')
    image[:len(a.words)*4] = struct.pack('<%dI' % len(a.words), *a.words)
    directory.mkdir(parents=True, exist_ok=True)
    (directory/'firmware.hex').write_text(''.join('%08x\n' % w for w in struct.unpack('<2048I', image)))
    (directory/'firmware.S').write_text('\n'.join(a.listing)+'\n')
    return dict(seed=seed, batch=batch, mode='cpu_unroll4', code_bytes=len(a.words)*4, benchmark=True)


def build(directory, seed=10000, batch=4, backend='npu'):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    if backend == 'cpu':
        meta = build_cpu(directory, seed, batch)
    elif backend == 'npu':
        build_har(directory, seed, benchmark=True, batch_override=batch)
        meta = json.loads((directory/'firmware_meta.json').read_text())
    else:
        raise ValueError('Unknown HAR backend')
    image = b''.join(int(w, 16).to_bytes(4, 'little') for w in (directory/'firmware.hex').read_text().splitlines())
    expected = bytearray(image)
    layout = [batch*3]
    for sample in range(batch):
        for offset, size in ((0, 32), (32, 24), (56, 4)):
            actual, golden = ACTUAL+sample*64+offset, 0x1c00+sample*64+offset
            expected[actual:actual+size] = image[golden:golden+size]
            layout += [BASE+actual, BASE+actual+size, BASE+golden, BASE+golden+size]
    def words(name, values):
        (directory/name).write_text(''.join('%08x\n' % v for v in values))
    words('bench_layout.hex', layout+[0]*(129-len(layout)))
    words('expected.hex', struct.unpack('<2048I', expected))
    words('phase_pcs.hex', [0]*7)
    source = int.from_bytes(image[0x1f0c:0x1f10], 'little')
    dma = [2, source, source+2048, BASE+0x1800, BASE+0x18c0]
    words('dma_ranges.hex', dma+[0]*(65-len(dma)))
    (directory/'firmware.bin').write_bytes(image)
    meta.update(backend=backend, useful_macs=batch*(64*32+32*6),
                arithmetic='Signed INT22 wrap per layer, ReLU/UINT16 requant with exact 64-bit product, INT22 scores, signed argmax with lowest-index tie',
                input_bytes_sha256=hashlib.sha256(image[0x1a00:0x1a00+batch*64]).hexdigest())
    (directory/'benchmark_meta.json').write_text(json.dumps(meta, indent=2)+'\n')
    return meta
