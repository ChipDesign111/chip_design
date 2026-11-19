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
    lui x21, 0x80002
    addi x21, x21, -64
    addi x24, x0, 0
    addi x5, x0, -2
    csrw mcountinhibit, x5 # enable mcycle, inhibit other counters
    lui x5, 0x4c495
    addi x5, x5, 1605
    sw x5, 0(x21)
    addi x5, x0, 1
    sw x5, 4(x21)
    addi x5, x0, 0
    sw x5, 12(x21)
    addi x5, x0, 0
    sw x5, 28(x21)
    addi x5, x0, 0
    sw x5, 32(x21)
    addi x5, x0, 0
    sw x5, 36(x21)
    addi x5, x0, -1
    sw x5, 40(x21)
    addi x5, x0, 6
    sw x5, 44(x21)
    lui x5, 0x80002
    addi x5, x5, -128
    sw x5, 48(x21)
    lui x5, 0x80002
    addi x5, x5, -200
    sw x5, 52(x21)
    lui x5, 0xb97ba
    addi x5, x5, 1943
    sw x5, 56(x21)
    lui x5, 0xc1bca
    addi x5, x5, 846
    sw x5, 60(x21)
    fence iorw, iorw
    addi x5, x0, 1
    sw x5, 24(x21)
live_wait:
    lw x22, 8(x21)
    beq x22, x0, live_wait
    lw x5, 12(x21)
    beq x22, x5, live_wait
    fence iorw, iorw
    csrr x23, mcycle
    lui x6, 0x80001
    addi x6, x6, 1288
    sw x22, 0(x6)
    sw x23, 4(x6)
    addi x5, x0, 2
    sw x5, 24(x21)
    addi x5, x0, 0
    sw x5, 28(x21)
    addi x5, x0, -1
    sw x5, 40(x21)
    lw x5, 16(x21)
    addi x6, x0, 1
    beq x5, x6, live_command_ok
    jal x0, live_bad_command
live_command_ok:
    lw x5, 20(x21)
    addi x6, x0, 64
    beq x5, x6, live_length_ok
    jal x0, live_bad_length
live_length_ok:
    lw x24, 36(x21)
    addi x24, x24, 1
    sw x24, 36(x21)
    lui x4, 0x80001
    addi x4, x4, 1552
    lui x29, 0x80001
    addi x29, x29, 1576
    lui x1, 0x0
    addi x1, x1, 0
    jal x0, fc_runtime
fc_return_1:
    addi x30, x0, -128
    addi x31, x0, 127
    lui x17, 0x1
    addi x17, x17, -2034
    lui x18, 0x100
    lui x5, 0x80002
    addi x5, x5, -328
    lui x6, 0x80002
    addi x6, x6, -160
    addi x7, x0, 32
fc_quant_2:
    lw x10, 0(x5)
    mul x10,x10,x17
    add x10, x10, x18
    srai x10,x10,1045
    bge x10, x30, clip_low_3
    addi x10, x30, 0
clip_low_3:
    bge x31, x10, clip_high_4
    addi x10, x31, 0
clip_high_4:
    sb x10,0(x6)
    addi x5, x5, 4
    addi x6, x6, 1
    addi x7, x7, -1
    bne x7, x0, fc_quant_2
    lui x17, 0x85d
    addi x17, x17, 681
    lui x18, 0x400
    lui x5, 0x80002
    addi x5, x5, -160
    lui x6, 0x80002
    addi x6, x6, -192
    addi x7, x0, 32
cpu_relu_5:
    lb x10,0(x5)
    bge x10, x0, relu_6
    addi x10, x0, 0
relu_6:
    mul x10,x10,x17
    add x10, x10, x18
    srai x10,x10,1047
    bge x10, x30, clip_low_7
    addi x10, x30, 0
clip_low_7:
    bge x31, x10, clip_high_8
    addi x10, x31, 0
clip_high_8:
    sb x10,0(x6)
    addi x5, x5, 1
    addi x6, x6, 1
    addi x7, x7, -1
    bne x7, x0, cpu_relu_5
    lui x4, 0x80001
    addi x4, x4, 1296
    lui x29, 0x80001
    addi x29, x29, 1320
    lui x1, 0x0
    addi x1, x1, 0
    jal x0, fc_runtime
fc_return_9:
    addi x30, x0, -128
    addi x31, x0, 127
    lui x17, 0x1
    addi x17, x17, -582
    lui x18, 0x80
    lui x5, 0x80002
    addi x5, x5, -328
    lui x6, 0x80002
    addi x6, x6, -200
    addi x7, x0, 6
fc_quant_10:
    lw x10, 0(x5)
    mul x10,x10,x17
    add x10, x10, x18
    srai x10,x10,1044
    bge x10, x30, clip_low_11
    addi x10, x30, 0
clip_low_11:
    bge x31, x10, clip_high_12
    addi x10, x31, 0
clip_high_12:
    sb x10,0(x6)
    addi x5, x5, 4
    addi x6, x6, 1
    addi x7, x7, -1
    bne x7, x0, fc_quant_10
    lui x21, 0x80002
    addi x21, x21, -64
    lui x5, 0x80002
    addi x5, x5, -200
    lb x6,0(x5)
    addi x7, x0, 0
    lb x8,1(x5)
    bge x6, x8, keep_argmax_13
    addi x6, x8, 0
    addi x7, x0, 1
keep_argmax_13:
    lb x8,2(x5)
    bge x6, x8, keep_argmax_14
    addi x6, x8, 0
    addi x7, x0, 2
keep_argmax_14:
    lb x8,3(x5)
    bge x6, x8, keep_argmax_15
    addi x6, x8, 0
    addi x7, x0, 3
keep_argmax_15:
    lb x8,4(x5)
    bge x6, x8, keep_argmax_16
    addi x6, x8, 0
    addi x7, x0, 4
keep_argmax_16:
    lb x8,5(x5)
    bge x6, x8, keep_argmax_17
    addi x6, x8, 0
    addi x7, x0, 5
keep_argmax_17:
    sw x7, 40(x21)
    addi x5, x0, 3
    sw x5, 24(x21)
    jal x0, live_publish
live_bad_command:
    addi x5, x0, 1
    sw x5, 28(x21)
    jal x0, live_error
live_bad_length:
    addi x5, x0, 2
    sw x5, 28(x21)
    jal x0, live_error
fail:
    lui x21, 0x80002
    addi x21, x21, -64
    addi x5, x0, 3
    sw x5, 28(x21)
live_error:
    addi x5, x0, 4
    sw x5, 24(x21)
live_publish:
    lui x6, 0x80001
    addi x6, x6, 1288
    lw x22, 0(x6)
    lw x23, 4(x6)
    csrr x5, mcycle
    sub x5, x5, x23
    sw x5, 32(x21)
    fence iorw, iorw
    sw x22, 12(x21)
    jal x0, live_wait
fc_runtime:
    lw x5, 0(x4)
    lw x6, 4(x4)
    lw x7, 8(x4)
    lw x23, 12(x4)
    lw x9, 16(x4)
    lw x10, 20(x4)
    lui x8, 0x80002
    addi x8, x8, -328
    addi x15, x0, 0
fc_bias:
    slli x18,x15,2
    add x19, x7, x18
    lw x21, 0(x19)
    add x19, x8, x18
    sw x21, 0(x19)
    addi x15, x15, 1
    bltu x15, x9, fc_bias
    lw x13, 0(x29)
    lw x14, 4(x29)
    beq x13, x0, fc_cpu_all
    beq x14, x0, fc_cpu_all
    addi x3, x6, 0
    addi x11, x0, 0
opt_n_block:
    addi x12, x0, 0
opt_k_block:
bench_input_pack:
    add x18, x5, x12
    addi x19, x2, 64
    addi x15, x0, 16
opt_input_words:
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
    bne x15, x0, opt_input_words
bench_npu_wait:
    sw x3, 32(x2)
    addi x17, x0, 1
    sw x17, 0(x2)
    lui x15, 0x18
    addi x15, x15, 1696
opt_poll_done:
    lw x17, 4(x2)
    andi x18, x17, 2
    beq x18, x0, opt_tile_done
    addi x15, x15, -1
    bne x15, x0, skip_fail_18
    jal x0, fail
skip_fail_18:
    jal x0, opt_poll_done
opt_tile_done:
    addi x18, x0, 1
    beq x17, x18, skip_fail_19
    jal x0, fail
skip_fail_19:
bench_read_reduce:
    addi x15, x0, 0
opt_read_partial:
    sw x15, 128(x2)
    addi x16, x0, 1000
opt_poll_ready:
    lw x17, 136(x2)
    andi x17, x17, 1
    bne x17, x0, opt_ready
    addi x16, x16, -1
    bne x16, x0, skip_fail_20
    jal x0, fail
skip_fail_20:
    jal x0, opt_poll_ready
opt_ready:
    lw x21, 132(x2)
    add x18, x11, x15
    slli x20,x18,2
    add x20, x8, x20
    lw x19, 0(x20)
    add x21, x19, x21
    sw x21, 0(x20)
    addi x15, x15, 1
    addi x31, x0, 32
    bltu x15, x31, opt_read_partial
    addi x17, x0, 2
    sw x17, 0(x2)
    lui x31, 0x1
    addi x31, x31, -2048
    add x3, x3, x31
    addi x12, x12, 64
    bltu x12, x14, opt_k_block
    addi x11, x11, 32
    bltu x11, x13, opt_n_block
    sub x10, x10, x14
    beq x10, x0, fc_bottom
    lw x6, 8(x29)
    add x5, x5, x14
    addi x9, x13, 0
    addi x12, x0, 1
    jal x0, fc_cpu_segment
fc_bottom:
    lw x9, 16(x4)
    sub x9, x9, x13
    beq x9, x0, fc_return
    lw x10, 20(x4)
    lw x5, 0(x4)
    lw x6, 12(x29)
    lui x8, 0x80002
    addi x8, x8, -328
    slli x18,x13,2
    add x8, x8, x18
    addi x12, x0, 2
    jal x0, fc_cpu_segment
fc_cpu_all:
    addi x12, x0, 2
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
    addi x17, x0, 1
    beq x12, x17, fc_bottom
fc_return:
    jalr x0,0(x1)
