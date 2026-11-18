    addi x30, x0, -128
    addi x31, x0, 127
    lui x6, 0x70001
    addi x6, x6, 1552
    lw x8, 0(x6)
    srai x8, x8, 24
    addi x9, x0, 1
    beq x8, x9, skip_fail_1
    jal x0, fail
skip_fail_1:
    addi x5, x0, 2
    lui x6, 0x70001
    addi x6, x6, 1536
    sw x5, 0(x6)
    lui x5, 0x80002
    addi x5, x5, -1536
    lui x6, 0x70001
    addi x6, x6, 1544
    sw x5, 0(x6)
    addi x5, x0, 2
    lui x6, 0x70001
    addi x6, x6, 1548
    sw x5, 0(x6)
    fence iorw, iorw
    addi x5, x0, 1
    lui x6, 0x70001
    addi x6, x6, 1536
    sw x5, 0(x6)
    lui x6, 0x70001
    addi x6, x6, 1540
    lui x7, 0x31
    addi x7, x7, -704
wait_segment_2:
    lw x8, 0(x6)
    addi x9, x0, 9
    beq x8, x9, segment_done_3
    andi x9, x8, 20
    beq x9, x0, skip_fail_4
    jal x0, fail
skip_fail_4:
    addi x7, x7, -1
    bne x7, x0, wait_segment_2
    jal x0, fail
segment_done_3:
    fence iorw, iorw
    lui x17, 0x10
    addi x17, x17, 516
    lui x18, 0x400
    lui x5, 0x80002
    addi x5, x5, -120
    lui x6, 0x80002
    addi x6, x6, -132
    addi x7, x0, 12
    lui x12, 0x80002
    addi x12, x12, -108
cpu_mul_5:
    lb x10, 0(x5)
    lb x11, 0(x12)
    addi x12, x12, 1
    mul x10, x10, x11
    mul x10, x10, x17
    add x10, x10, x18
    srai x10, x10, 23
    bge x10, x30, clip_low_6
    addi x10, x30, 0
clip_low_6:
    bge x31, x10, clip_high_7
    addi x10, x31, 0
clip_high_7:
    sb x10, 0(x6)
    addi x5, x5, 1
    addi x6, x6, 1
    addi x7, x7, -1
    bne x7, x0, cpu_mul_5
    lui x17, 0x312
    addi x17, x17, -615
    lui x18, 0x400
    lui x19, 0x4ee
    addi x19, x19, 615
    lui x5, 0x80002
    addi x5, x5, -132
    lui x6, 0x80002
    addi x6, x6, -144
    addi x7, x0, 12
    lui x12, 0x80002
    addi x12, x12, -108
cpu_add_8:
    lb x10, 0(x5)
    lb x11, 0(x12)
    addi x12, x12, 1
    mul x10, x10, x17
    mul x11, x11, x19
    add x10, x10, x11
    add x10, x10, x18
    srai x10, x10, 23
    bge x10, x30, clip_low_9
    addi x10, x30, 0
clip_low_9:
    bge x31, x10, clip_high_10
    addi x10, x31, 0
clip_high_10:
    sb x10, 0(x6)
    addi x5, x5, 1
    addi x6, x6, 1
    addi x7, x7, -1
    bne x7, x0, cpu_add_8
    lui x6, 0x70001
    addi x6, x6, 1552
    lw x8, 0(x6)
    srai x8, x8, 24
    addi x9, x0, 1
    beq x8, x9, skip_fail_11
    jal x0, fail
skip_fail_11:
    addi x5, x0, 2
    lui x6, 0x70001
    addi x6, x6, 1536
    sw x5, 0(x6)
    lui x5, 0x80002
    addi x5, x5, -1600
    lui x6, 0x70001
    addi x6, x6, 1544
    sw x5, 0(x6)
    addi x5, x0, 1
    lui x6, 0x70001
    addi x6, x6, 1548
    sw x5, 0(x6)
    fence iorw, iorw
    addi x5, x0, 1
    lui x6, 0x70001
    addi x6, x6, 1536
    sw x5, 0(x6)
    lui x6, 0x70001
    addi x6, x6, 1540
    lui x7, 0x31
    addi x7, x7, -704
wait_segment_12:
    lw x8, 0(x6)
    addi x9, x0, 9
    beq x8, x9, segment_done_13
    andi x9, x8, 20
    beq x9, x0, skip_fail_14
    jal x0, fail
skip_fail_14:
    addi x7, x7, -1
    bne x7, x0, wait_segment_12
    jal x0, fail
segment_done_13:
    fence iorw, iorw
    lui x17, 0x800
    addi x17, x17, 1
    lui x18, 0x400
    lui x5, 0x80002
    addi x5, x5, -152
    lui x6, 0x80002
    addi x6, x6, -160
    addi x7, x0, 5
cpu_mul_15:
    lb x10, 0(x5)
    mul x10, x10, x17
    add x10, x10, x18
    srai x10, x10, 23
    bge x10, x30, clip_low_16
    addi x10, x30, 0
clip_low_16:
    bge x31, x10, clip_high_17
    addi x10, x31, 0
clip_high_17:
    sb x10, 0(x6)
    addi x5, x5, 1
    addi x6, x6, 1
    addi x7, x7, -1
    bne x7, x0, cpu_mul_15
    lui x17, 0xb0a
    addi x17, x17, 1713
    lui x18, 0x400
    lui x19, 0x1822b
    addi x19, x19, 467
    lui x5, 0x80002
    addi x5, x5, -160
    lui x6, 0x80002
    addi x6, x6, -168
    addi x7, x0, 5
cpu_add_18:
    lb x10, 0(x5)
    mul x10, x10, x17
    add x10, x10, x19
    add x10, x10, x18
    srai x10, x10, 23
    bge x10, x30, clip_low_19
    addi x10, x30, 0
clip_low_19:
    bge x31, x10, clip_high_20
    addi x10, x31, 0
clip_high_20:
    sb x10, 0(x6)
    addi x5, x5, 1
    addi x6, x6, 1
    addi x7, x7, -1
    bne x7, x0, cpu_add_18
    lui x17, 0x80002
    addi x17, x17, -1396
    addi x19, x0, 534
    lui x5, 0x80002
    addi x5, x5, -168
    addi x7, x0, 5
    addi x14, x0, -128
softmax_max_21:
    lb x10, 0(x5)
    bge x14, x10, keep_max_22
    addi x14, x10, 0
keep_max_22:
    addi x5, x5, 1
    addi x7, x7, -1
    bne x7, x0, softmax_max_21
    lui x5, 0x80002
    addi x5, x5, -168
    addi x7, x0, 5
    addi x15, x0, 0
softmax_sum_23:
    lb x10, 0(x5)
    sub x10, x10, x14
    addi x10, x10, 255
    slli x10, x10, 1
    add x10, x10, x17
    lhu x10, 0(x10)
    add x15, x15, x10
    addi x5, x5, 1
    addi x7, x7, -1
    bne x7, x0, softmax_sum_23
    lui x5, 0x80002
    addi x5, x5, -168
    lui x6, 0x80002
    addi x6, x6, -176
    addi x7, x0, 5
    srai x18, x15, 1
softmax_normalize_24:
    lb x10, 0(x5)
    sub x10, x10, x14
    addi x10, x10, 255
    slli x10, x10, 1
    add x10, x10, x17
    lhu x10, 0(x10)
    mul x10, x10, x19
    add x10, x10, x18
    divu x10, x10, x15
    bge x31, x10, softmax_clip_25
    addi x10, x31, 0
softmax_clip_25:
    sb x10, 0(x6)
    addi x5, x5, 1
    addi x6, x6, 1
    addi x7, x7, -1
    bne x7, x0, softmax_normalize_24
    lui x5, 0xc0dec
    addi x5, x5, 222
    jal x0, finish
fail:
    lui x5, 0xdeadc
    addi x5, x5, -273
finish:
    lui x6, 0x80002
    addi x6, x6, -32
    sw x5, 0(x6)
halt:
    jal x0, halt
