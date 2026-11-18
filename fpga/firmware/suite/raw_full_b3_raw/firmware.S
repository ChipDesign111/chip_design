    lui x31, 0x80002
    addi x31, x31, -64
    addi x30, x0, 1
    sw x30, 0(x31)
    lui x2, 0x70000
    addi x17, x0, 1
    sw x17, 60(x2)
    sw x17, 24(x2)
    lui x18, 0x70001
    addi x18, x18, -1600
    addi x15, x0, 32
zero_hw_bias:
    sw x0, 0(x18)
    addi x18, x18, 4
    addi x15, x15, -1
    bne x15, x0, zero_hw_bias
    addi x30, x0, -128
    addi x31, x0, 127
    lui x4, 0x80001
    addi x4, x4, 1124
    lui x1, 0x0
    addi x1, x1, 0
    jal x0, fc_batch_runtime
batch_fc_return_1:
    lui x2, 0x70000
    sw x0, 60(x2)
    lw x17, 60(x2)
    beq x17, x0, skip_fail_2
    jal x0, fail
skip_fail_2:
    lui x31, 0x80002
    addi x31, x31, -64
    addi x30, x0, 2
    sw x30, 0(x31)
    lui x17, 0xc0dec
    addi x17, x17, 222
    jal x0, exit
fail:
    lui x17, 0xdeadc
    addi x17, x17, -273
exit:
    lui x18, 0x80002
    addi x18, x18, -32
    sw x17, 0(x18)
halt:
    jal x0, halt
fc_runtime:
    lw x5, 0(x4)
    lw x6, 4(x4)
    lw x7, 8(x4)
    lw x23, 12(x4)
    lw x9, 16(x4)
    lw x10, 20(x4)
    lui x8, 0x80002
    addi x8, x8, -736
    addi x15, x0, 0
fc_bias:
    slli x18,x15,2
    add x19, x7, x18
    lw x21, 0(x19)
    add x19, x8, x18
    sw x21, 0(x19)
    addi x15, x15, 1
    bltu x15, x9, fc_bias
fc_cpu_segment:
    andi x11, x10, -4
    addi x15, x0, 0
cpu_row:
    mul x18,x15,x10
    add x18, x6, x18
    addi x19, x5, 0
    slli x20,x15,2
    add x20, x8, x20
    lw x21, 0(x20)
    addi x16, x0, 0
    beq x11, x0, cpu_tail
    addi x0, x0, 0
    addi x0, x0, 0
cpu_unroll4:
    lb x17,0(x18)
    lb x22,0(x19)
    mul x17,x17,x22
    add x21, x21, x17
    lb x17,1(x18)
    lb x22,1(x19)
    mul x17,x17,x22
    add x21, x21, x17
    lb x17,2(x18)
    lb x22,2(x19)
    mul x17,x17,x22
    add x21, x21, x17
    lb x17,3(x18)
    lb x22,3(x19)
    mul x17,x17,x22
    add x21, x21, x17
    addi x18, x18, 4
    addi x19, x19, 4
    addi x16, x16, 4
    bltu x16, x11, cpu_unroll4
cpu_tail:
    bgeu x16, x10, cpu_row_done
    lb x17,0(x18)
    lb x22,0(x19)
    mul x17,x17,x22
    add x21, x21, x17
    addi x18, x18, 1
    addi x19, x19, 1
    addi x16, x16, 1
    jal x0, cpu_tail
cpu_row_done:
    sw x21, 0(x20)
    addi x15, x15, 1
    bltu x15, x9, cpu_row
    jalr x0,0(x1)
fc_batch_runtime:
    addi x28, x1, 0
    lw x27, 24(x4)
    sw x27, 24(x2)
    slli x24,x27,5
    lw x14, 40(x4)
    addi x13, x0, 0
batch_n_block:
    addi x23, x0, 0
    lui x8, 0x80002
    addi x8, x8, -736
    addi x9, x0, 32
    lw x7, 8(x4)
    slli x17,x13,2
    add x7, x7, x17
batch_bias_samples:
    lui x26, 0x0
    addi x26, x26, 0
    jal x0, batch_copy_bias
batch_bias_return:
    addi x8, x8, 128
    addi x23, x23, 1
    bltu x23, x27, batch_bias_samples
    lw x3, 4(x4)
    mul x17,x13,x14
    add x3, x3, x17
    addi x12, x0, 0
batch_k_block:
    lw x5, 0(x4)
    add x5, x5, x12
    addi x23, x0, 0
batch_input_sample:
    addi x18, x5, 0
    lui x19, 0x70000
    addi x19, x19, 64
    beq x23, x0, batch_input_address
    lui x19, 0x70001
    addi x19, x19, -1024
    addi x17, x0, 1
    beq x23, x17, batch_input_address
    lui x19, 0x70001
    addi x17, x23, -2
    slli x17,x17,6
    add x19, x19, x17
batch_input_address:
    addi x15, x0, 16
batch_input_words:
    lw x17, 0(x18)
    sw x17, 0(x19)
    lw x17, 4(x18)
    sw x17, 4(x19)
    lw x17, 8(x18)
    sw x17, 8(x19)
    lw x17, 12(x18)
    sw x17, 12(x19)
    addi x18, x18, 16
    addi x19, x19, 16
    addi x15, x15, -4
    bne x15, x0, batch_input_words
    lw x17, 28(x4)
    add x5, x5, x17
    addi x23, x23, 1
    bltu x23, x27, batch_input_sample
    sw x3, 32(x2)
    addi x17, x0, 1
    sw x17, 0(x2)
    lui x15, 0x18
    addi x15, x15, 1696
batch_poll_done:
    lw x17, 4(x2)
    andi x18, x17, 2
    beq x18, x0, batch_tile_done
    addi x15, x15, -1
    bne x15, x0, skip_fail_3
    jal x0, fail
skip_fail_3:
    jal x0, batch_poll_done
batch_tile_done:
    addi x18, x0, 1
    beq x17, x18, skip_fail_4
    jal x0, fail
skip_fail_4:
    lui x8, 0x80002
    addi x8, x8, -736
    addi x15, x0, 0
batch_read_partial:
    sw x15, 128(x2)
    addi x16, x0, 1000
batch_poll_ready:
    lw x17, 136(x2)
    andi x17, x17, 1
    bne x17, x0, batch_partial_ready
    addi x16, x16, -1
    bne x16, x0, skip_fail_5
    jal x0, fail
skip_fail_5:
    jal x0, batch_poll_ready
batch_partial_ready:
    lw x21, 132(x2)
    lw x19, 0(x8)
    add x21, x19, x21
    sw x21, 0(x8)
    addi x8, x8, 4
    addi x15, x15, 1
    bltu x15, x24, batch_read_partial
    addi x17, x0, 2
    sw x17, 0(x2)
    lui x17, 0x1
    addi x17, x17, -2048
    add x3, x3, x17
    addi x12, x12, 64
    bltu x12, x14, batch_k_block
    lw x10, 20(x4)
    sub x10, x10, x14
    beq x10, x0, batch_quant_core
    lw x6, 44(x4)
    mul x17,x13,x10
    add x6, x6, x17
    lw x5, 0(x4)
    add x5, x5, x14
    lui x8, 0x80002
    addi x8, x8, -736
    addi x9, x0, 32
    addi x23, x0, 0
batch_right_sample:
    addi x12, x0, 2
    lui x1, 0x0
    addi x1, x1, 0
    jal x0, fc_cpu_segment
batch_right_return:
    lw x17, 28(x4)
    add x5, x5, x17
    addi x8, x8, 128
    addi x23, x23, 1
    bltu x23, x27, batch_right_sample
batch_quant_core:
    lui x5, 0x80002
    addi x5, x5, -736
    addi x23, x0, 0
    lw x6, 12(x4)
    add x6, x6, x13
batch_quant_sample:
    addi x7, x0, 32
    lui x26, 0x0
    addi x26, x26, 0
    jal x0, batch_quantize
batch_quant_return:
    lw x17, 32(x4)
    addi x17, x17, -32
    add x6, x6, x17
    addi x23, x23, 1
    bltu x23, x27, batch_quant_sample
    addi x13, x13, 32
    lw x17, 36(x4)
    bltu x13, x17, batch_n_block
    lw x9, 16(x4)
    sub x9, x9, x13
    beq x9, x0, batch_return
    addi x23, x0, 0
batch_bottom_sample:
    lui x8, 0x80002
    addi x8, x8, -736
    lw x7, 8(x4)
    slli x17,x13,2
    add x7, x7, x17
    lui x26, 0x0
    addi x26, x26, 0
    jal x0, batch_copy_bias
batch_bottom_bias_return:
    lw x5, 0(x4)
    lw x17, 28(x4)
    mul x17,x23,x17
    add x5, x5, x17
    lw x6, 48(x4)
    lw x10, 20(x4)
    addi x12, x0, 2
    lui x1, 0x0
    addi x1, x1, 0
    jal x0, fc_cpu_segment
batch_bottom_return:
    lui x5, 0x80002
    addi x5, x5, -736
    lw x6, 12(x4)
    lw x17, 32(x4)
    mul x17,x23,x17
    add x6, x6, x17
    add x6, x6, x13
    addi x7, x9, 0
    lui x26, 0x0
    addi x26, x26, 0
    jal x0, batch_quantize
batch_bottom_quant_return:
    addi x23, x23, 1
    bltu x23, x27, batch_bottom_sample
batch_return:
    addi x17, x0, 1
    sw x17, 24(x2)
    jalr x0,0(x28)
batch_copy_bias:
    addi x15, x0, 0
batch_bias_word:
    slli x18,x15,2
    add x19, x7, x18
    lw x21, 0(x19)
    add x19, x8, x18
    sw x21, 0(x19)
    addi x15, x15, 1
    bltu x15, x9, batch_bias_word
    jalr x0,0(x26)
batch_quantize:
    lw x17, 52(x4)
    lw x25, 56(x4)
    addi x18, x0, 0
    beq x25, x0, batch_quant_round_ready
    addi x19, x25, -1
    addi x20, x0, 1
    sll x18,x20,x19
batch_quant_round_ready:
    addi x30, x0, -128
    addi x31, x0, 127
batch_quant_word:
    lw x10, 0(x5)
    mul x10,x10,x17
    add x10, x10, x18
    sra x10,x10,x25
    bge x10, x30, batch_clip_low
    addi x10, x30, 0
batch_clip_low:
    bge x31, x10, batch_clip_high
    addi x10, x31, 0
batch_clip_high:
    sb x10,0(x6)
    addi x5, x5, 4
    addi x6, x6, 1
    addi x7, x7, -1
    bne x7, x0, batch_quant_word
    jalr x0,0(x26)
