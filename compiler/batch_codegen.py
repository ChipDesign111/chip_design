"""Batch 2..4 RAW weight reuse with one INT32 [batch,32] scratch block.

Descriptor words: input, weights, bias, output, N, K, batch, input stride,
output stride, full N, full K, right weights, bottom weights, mult, shift.
The original scalar CPU dot-product entry handles the compact fringes.
"""


def emit_batch_runtime(a, accumulator):
    # Persistent registers: x4 descriptor, x13 output offset, x14 full K,
    # x23 sample, x24 batch*32, x27 batch, x28 outer return address.
    # Nested scalar dot products return through x1; local helpers through x26.
    a.label('fc_batch_runtime'); a.addi(28, 1, 0)
    a.lw(27, 4, 24); a.sw(27, 2, 0x18); a.slli(24, 27, 5)
    a.lw(14, 4, 40); a.li(13, 0)
    a.label('batch_n_block')
    a.li(23, 0); a.li(8, accumulator); a.li(9, 32)
    a.lw(7, 4, 8); a.slli(17, 13, 2); a.add(7, 7, 17)
    a.label('batch_bias_samples')
    a.la(26, 'batch_bias_return'); a.jump('batch_copy_bias')
    a.label('batch_bias_return'); a.addi(8, 8, 128); a.addi(23, 23, 1)
    a.branch('bltu', 23, 27, 'batch_bias_samples')
    a.lw(3, 4, 4); a.mul(17, 13, 14); a.add(3, 3, 17); a.li(12, 0)
    a.label('batch_k_block')
    a.lw(5, 4); a.add(5, 5, 12); a.li(23, 0)
    a.label('batch_input_sample'); a.addi(18, 5, 0)
    a.li(19, 0x70000040); a.branch('beq', 23, 0, 'batch_input_address')
    a.li(19, 0x70000c00); a.li(17, 1); a.branch('beq', 23, 17, 'batch_input_address')
    a.li(19, 0x70001000); a.addi(17, 23, -2); a.slli(17, 17, 6); a.add(19, 19, 17)
    a.label('batch_input_address'); a.li(15, 16)
    a.label('batch_input_words')
    for lane in range(4):
        a.lw(17, 18, lane*4); a.sw(17, 19, lane*4)
    a.addi(18, 18, 16); a.addi(19, 19, 16); a.addi(15, 15, -4)
    a.branch('bne', 15, 0, 'batch_input_words')
    a.lw(17, 4, 28); a.add(5, 5, 17); a.addi(23, 23, 1)
    a.branch('bltu', 23, 27, 'batch_input_sample')
    a.sw(3, 2, 0x20); a.li(17, 1); a.sw(17, 2); a.li(15, 100000)
    a.label('batch_poll_done'); a.lw(17, 2, 4); a.andi(18, 17, 2)
    a.branch('beq', 18, 0, 'batch_tile_done'); a.addi(15, 15, -1)
    a.branch('beq', 15, 0, 'fail'); a.jump('batch_poll_done')
    a.label('batch_tile_done'); a.li(18, 1); a.branch('bne', 17, 18, 'fail')
    # RAW_INDEX = sample*32 + output. The SRAM scratch uses the same order.
    a.li(8, accumulator); a.li(15, 0); a.label('batch_read_partial')
    a.sw(15, 2, 0x80); a.li(16, 1000)
    a.label('batch_poll_ready'); a.lw(17, 2, 0x88); a.andi(17, 17, 1)
    a.branch('bne', 17, 0, 'batch_partial_ready'); a.addi(16, 16, -1)
    a.branch('beq', 16, 0, 'fail'); a.jump('batch_poll_ready')
    a.label('batch_partial_ready'); a.lw(21, 2, 0x84); a.lw(19, 8)
    a.add(21, 19, 21); a.sw(21, 8); a.addi(8, 8, 4); a.addi(15, 15, 1)
    a.branch('bltu', 15, 24, 'batch_read_partial')
    a.li(17, 2); a.sw(17, 2); a.li(17, 2048); a.add(3, 3, 17)
    a.addi(12, 12, 64); a.branch('bltu', 12, 14, 'batch_k_block')
    # Right columns add to the same biased INT32 accumulators, before quant.
    a.lw(10, 4, 20); a.sub(10, 10, 14)
    a.branch('beq', 10, 0, 'batch_quant_core')
    a.lw(6, 4, 44); a.mul(17, 13, 10); a.add(6, 6, 17)
    a.lw(5, 4); a.add(5, 5, 14); a.li(8, accumulator); a.li(9, 32); a.li(23, 0)
    a.label('batch_right_sample'); a.li(12, 2)
    a.la(1, 'batch_right_return'); a.jump('fc_cpu_segment')
    a.label('batch_right_return'); a.lw(17, 4, 28); a.add(5, 5, 17)
    a.addi(8, 8, 128); a.addi(23, 23, 1)
    a.branch('bltu', 23, 27, 'batch_right_sample')
    a.label('batch_quant_core'); a.li(5, accumulator); a.li(23, 0)
    a.lw(6, 4, 12); a.add(6, 6, 13)
    a.label('batch_quant_sample'); a.li(7, 32)
    a.la(26, 'batch_quant_return'); a.jump('batch_quantize')
    a.label('batch_quant_return'); a.lw(17, 4, 32); a.addi(17, 17, -32)
    a.add(6, 6, 17); a.addi(23, 23, 1)
    a.branch('bltu', 23, 27, 'batch_quant_sample')
    a.addi(13, 13, 32); a.lw(17, 4, 36)
    a.branch('bltu', 13, 17, 'batch_n_block')
    # Bottom rows are compact CPU work. Reuse the first scratch row per sample.
    a.lw(9, 4, 16); a.sub(9, 9, 13); a.branch('beq', 9, 0, 'batch_return')
    a.li(23, 0); a.label('batch_bottom_sample'); a.li(8, accumulator)
    a.lw(7, 4, 8); a.slli(17, 13, 2); a.add(7, 7, 17)
    a.la(26, 'batch_bottom_bias_return'); a.jump('batch_copy_bias')
    a.label('batch_bottom_bias_return'); a.lw(5, 4); a.lw(17, 4, 28)
    a.mul(17, 23, 17); a.add(5, 5, 17); a.lw(6, 4, 48); a.lw(10, 4, 20)
    a.li(12, 2); a.la(1, 'batch_bottom_return'); a.jump('fc_cpu_segment')
    a.label('batch_bottom_return'); a.li(5, accumulator); a.lw(6, 4, 12)
    a.lw(17, 4, 32); a.mul(17, 23, 17); a.add(6, 6, 17); a.add(6, 6, 13)
    a.addi(7, 9, 0); a.la(26, 'batch_bottom_quant_return'); a.jump('batch_quantize')
    a.label('batch_bottom_quant_return'); a.addi(23, 23, 1)
    a.branch('bltu', 23, 27, 'batch_bottom_sample')
    a.label('batch_return'); a.li(17, 1); a.sw(17, 2, 0x18); a.jalr(0, 28)

    a.label('batch_copy_bias'); a.li(15, 0); a.label('batch_bias_word')
    a.slli(18, 15, 2); a.add(19, 7, 18); a.lw(21, 19)
    a.add(19, 8, 18); a.sw(21, 19); a.addi(15, 15, 1)
    a.branch('bltu', 15, 9, 'batch_bias_word'); a.jalr(0, 26)

    # Exactly the graph frontend's signed INT8 boundary, including negative
    # ties. Coefficients already prove the multiply and rounded sum fit INT32.
    a.label('batch_quantize'); a.lw(17, 4, 52); a.lw(25, 4, 56); a.li(18, 0)
    a.branch('beq', 25, 0, 'batch_quant_round_ready')
    a.addi(19, 25, -1); a.li(20, 1); a.sll(18, 20, 19)
    a.label('batch_quant_round_ready'); a.li(30, -128); a.li(31, 127)
    a.label('batch_quant_word'); a.lw(10, 5); a.mul(10, 10, 17); a.add(10, 10, 18)
    a.register('sra', 10, 10, 25, 5, 0x20)
    a.branch('bge', 10, 30, 'batch_clip_low'); a.addi(10, 30, 0); a.label('batch_clip_low')
    a.branch('bge', 31, 10, 'batch_clip_high'); a.addi(10, 31, 0); a.label('batch_clip_high')
    a.sb(10, 6); a.addi(5, 5, 4); a.addi(6, 6, 1); a.addi(7, 7, -1)
    a.branch('bne', 7, 0, 'batch_quant_word'); a.jalr(0, 26)
