"""Compile fixed INT8 layers into prepacked RAW cores plus scalar CPU edges.

Only complete 32-output x 64-input blocks use RAW. The remaining right columns
and bottom rows stay compact and run on the CPU. Reordering is a permutation,
so weights occupy exactly N*K bytes, without padding or a second weight copy.
The original dynamic-weight RAW generator remains available unchanged.
"""
import json

from generic_firmware import (BENCHMARK_ADDRESS, BENCHMARK_PHASES, RuntimeAssembler,
                              _check_outputs, _cpu_kernel, _finish_outputs,
                              _marker, _phase, build as build_generic)
from generic_runtime import BASE, CODE_BYTES, STATUS_OFFSET, plan


def pack_layer(layer):
    n, k = len(layer.weights), len(layer.weights[0])
    nf, kf = n // 32 * 32, k // 64 * 64
    if not nf or not kf:
        return bytes(v & 255 for row in layer.weights for v in row), 0, 0
    core = [layer.weights[nb+row][kb+pair*2+lane]
            for nb in range(0, nf, 32) for kb in range(0, kf, 64)
            for pair in range(32) for row in range(32) for lane in range(2)]
    right = [layer.weights[row][col] for row in range(nf) for col in range(kf, k)]
    bottom = [v for row in layer.weights[nf:] for v in row]
    return bytes(v & 255 for v in core + right + bottom), nf, kf


def _full_blocks(a):
    # x13/x14 are full N/K. Packed blocks are contiguous in (N-block,K-block)
    # order. DMA reads the immutable model weights directly, not a CPU copy.
    a.addi(3, 6, 0); a.li(11, 0); a.label('opt_n_block'); a.li(12, 0)
    a.label('opt_k_block'); _phase(a, 'input_pack', True)
    a.add(18, 5, 12); a.addi(19, 2, 0x40); a.li(15, 16)
    a.label('opt_input_words')
    for lane in range(4):
        a.lw(17, 18, lane*4); a.sw(17, 19, lane*4)
    a.addi(18, 18, 16); a.addi(19, 19, 16); a.addi(15, 15, -4)
    a.branch('bne', 15, 0, 'opt_input_words')
    _phase(a, 'npu_wait', True)
    a.sw(3, 2, 0x20); a.li(17, 1); a.sw(17, 2); a.li(15, 100000)
    a.label('opt_poll_done'); a.lw(17, 2, 4); a.andi(18, 17, 2)
    a.branch('beq', 18, 0, 'opt_tile_done'); a.addi(15, 15, -1)
    a.branch('beq', 15, 0, 'fail'); a.jump('opt_poll_done')
    a.label('opt_tile_done'); a.li(18, 1); a.branch('bne', 17, 18, 'fail')
    _phase(a, 'read_reduce', True)
    a.li(15, 0); a.label('opt_read_partial'); a.sw(15, 2, 0x80); a.li(16, 1000)
    a.label('opt_poll_ready'); a.lw(17, 2, 0x88); a.andi(17, 17, 1)
    a.branch('bne', 17, 0, 'opt_ready'); a.addi(16, 16, -1)
    a.branch('beq', 16, 0, 'fail'); a.jump('opt_poll_ready')
    a.label('opt_ready'); a.lw(21, 2, 0x84); a.add(18, 11, 15)
    a.slli(20, 18, 2); a.add(20, 8, 20); a.lw(19, 20)
    a.add(21, 19, 21); a.sw(21, 20); a.addi(15, 15, 1)
    a.li(31, 32); a.branch('bltu', 15, 31, 'opt_read_partial')
    a.li(17, 2); a.sw(17, 2); a.li(31, 2048); a.add(3, 3, 31)
    a.addi(12, 12, 64); a.branch('bltu', 12, 14, 'opt_k_block')
    a.addi(11, 11, 32); a.branch('bltu', 11, 13, 'opt_n_block')


def build(directory, layers, inputs, *, benchmark=False):
    p = plan(layers, inputs)
    packed = [pack_layer(layer) for layer in layers]
    raw_tiles = sum(nf // 32 * (kf // 64) for _, nf, kf in packed)
    dispatch = []
    for layer, (_, nf, kf) in zip(layers, packed):
        n, k = len(layer.weights), len(layer.weights[0])
        dispatch.append({'path': 'raw_core_cpu_edges' if nf and kf else 'cpu',
                         'outputs': n, 'inputs': k, 'raw_tiles': nf // 32 * (kf // 64),
                         'raw_macs': nf*kf, 'cpu_macs': n*k-nf*kf,
                         'weight_bytes': n*k})
    if not raw_tiles:
        # Compile-time dispatch: no per-inference decision cost for small nets.
        meta = build_generic(directory, layers, inputs, backend='cpu', benchmark=benchmark)
        meta.update(backend='optimized', tile_count=0, layer_dispatch=dispatch,
                    weight_layout='compact row-major; CPU-only dispatch')
        (directory/'firmware_meta.json').write_text(json.dumps(meta, indent=2)+'\n')
        return meta

    allocations = {entry['name']: entry for entry in p['allocations']}
    extension = []
    dma_ranges = []
    for i, (data, nf, kf) in enumerate(packed):
        allocation = allocations['weights_%d' % i]
        start, count = allocation['offset'], allocation['bytes']
        if len(data) != count:
            raise AssertionError('Packing must preserve the compact weight size')
        p['image'][start:start+count] = data
        k = len(layers[i].weights[0])
        extension += [nf, kf, BASE+start+nf*kf, BASE+start+nf*k]
        if nf and kf:
            dma_ranges.append([BASE+start, BASE+start+nf*kf])
    # CPU no longer needs the old 2048 B weight staging area. Use its first
    # 16 B per layer for immutable dispatch descriptors, without extra SRAM.
    ext_offset = p['work_address'] - BASE
    ext_data = b''.join(value.to_bytes(4, 'little') for value in extension)
    if ext_offset + len(ext_data) > BENCHMARK_ADDRESS-BASE:
        raise ValueError('Optimized descriptors exceed unused staging memory')
    p['image'][ext_offset:ext_offset+len(ext_data)] = ext_data

    a = RuntimeAssembler()
    if benchmark:
        _marker(a, 1)
    a.li(2, 0x70000000); a.li(4, p['descriptors']); a.li(8, p['accumulators'])
    a.li(27, p['layer_count']); a.li(29, p['work_address'])
    a.li(17, 1); a.sw(17, 2, 0x3c); a.sw(17, 2, 0x18)
    a.li(18, 0x700009c0); a.li(15, 32); a.label('opt_zero_bias')
    a.sw(0, 18); a.addi(18, 18, 4); a.addi(15, 15, -1)
    a.branch('bne', 15, 0, 'opt_zero_bias')
    a.label('opt_layer'); _phase(a, 'setup', True)
    for reg, offset in ((5, 0), (6, 4), (7, 8), (23, 12), (9, 16), (10, 20),
                        (24, 24), (25, 28), (26, 32), (28, 36)):
        a.lw(reg, 4, offset)
    a.li(8, p['accumulators']); a.li(15, 0); a.label('opt_copy_bias')
    a.slli(18, 15, 2); a.add(19, 7, 18); a.lw(21, 19)
    a.add(19, 8, 18); a.sw(21, 19); a.addi(15, 15, 1)
    a.branch('bltu', 15, 9, 'opt_copy_bias')
    a.lw(13, 29); a.lw(14, 29, 4)
    a.branch('beq', 13, 0, 'opt_cpu_all'); a.branch('beq', 14, 0, 'opt_cpu_all')
    _full_blocks(a)
    # Right fringe: full output rows, remaining input columns.
    a.sub(10, 10, 14); a.branch('beq', 10, 0, 'opt_bottom')
    a.lw(6, 29, 8); a.add(5, 5, 14); a.addi(9, 13, 0)
    a.li(12, 1); a.jump('opt_cpu_segment')
    # Bottom fringe: remaining output rows, all original input columns.
    a.label('opt_bottom'); a.lw(9, 4, 16); a.sub(9, 9, 13)
    a.branch('beq', 9, 0, 'opt_finish'); a.lw(10, 4, 20)
    a.lw(5, 4); a.lw(6, 29, 12); a.li(8, p['accumulators'])
    a.slli(18, 13, 2); a.add(8, 8, 18); a.li(12, 2); a.jump('opt_cpu_segment')
    a.label('opt_cpu_all'); a.li(12, 2)
    a.label('opt_cpu_segment'); _cpu_kernel(a, True)
    a.li(17, 1); a.branch('beq', 12, 17, 'opt_bottom')
    a.label('opt_finish'); a.li(8, p['accumulators']); a.lw(9, 4, 16)
    _finish_outputs(a, benchmark)
    a.addi(4, 4, 40); a.addi(29, 29, 16); a.addi(27, 27, -1)
    a.branch('bne', 27, 0, 'opt_layer')
    a.sw(0, 2, 0x3c); a.lw(17, 2, 0x3c); a.branch('bne', 17, 0, 'fail')
    if benchmark:
        _marker(a, 2)
        _check_outputs(a, p)
    a.li(17, 0xc0dec0de); a.jump('exit'); a.label('fail'); a.li(17, 0xdeadbeef)
    a.label('exit'); a.li(18, BASE+STATUS_OFFSET); a.sw(17, 18)
    a.label('halt'); a.jump('halt'); a.resolve()
    if len(a.words)*4 > CODE_BYTES:
        raise ValueError('Optimized runtime exceeds its code reservation')
    for i, word in enumerate(a.words):
        p['image'][i*4:i*4+4] = word.to_bytes(4, 'little')
    directory.mkdir(parents=True, exist_ok=True)
    (directory/'firmware.hex').write_text(''.join('%08x\n' % int.from_bytes(p['image'][i:i+4], 'little') for i in range(0, 8192, 4)))
    (directory/'firmware.S').write_text('\n'.join(a.listing)+'\n')
    meta = {k: v for k, v in p.items() if k != 'image'}
    meta.update(backend='optimized', benchmark=benchmark, tile_count=raw_tiles,
                layer_dispatch=dispatch, dma_ranges=dma_ranges,
                code_bytes=len(a.words)*4, accumulator_bits=22, cpu_reduction_bits=32,
                cpu_requant_product_bits=64, weight_layout='prepacked full blocks, compact right fringe, compact bottom rows')
    if benchmark:
        meta.update(benchmark_address=BENCHMARK_ADDRESS,
                    phase_pcs={name: a.labels.get('bench_' + name, 0) for name in BENCHMARK_PHASES})
    (directory/'firmware_meta.json').write_text(json.dumps(meta, indent=2)+'\n')
    return meta
