    addi x30, x0, -128
    addi x31, x0, 127
    lui x17, 0x2
    addi x17, x17, -1953
    lui x18, 0x100
    lui x12, 0x80002
    addi x12, x12, -428
    lui x13, 0x80002
    addi x13, x13, -224
    lui x6, 0x80002
    addi x6, x6, -96
    addi x14, x0, 12
cpu_fc_out_1:
    lw x10, 0(x13)
    lui x5, 0x80002
    addi x5, x5, -84
    addi x7, x0, 17
cpu_fc_dot_2:
    lb x8, 0(x5)
    lb x9, 0(x12)
    mul x8, x8, x9
    add x10, x10, x8
    addi x5, x5, 1
    addi x12, x12, 1
    addi x7, x7, -1
    bne x7, x0, cpu_fc_dot_2
    mul x10, x10, x17
    add x10, x10, x18
    srai x10, x10, 21
    bge x10, x30, clip_low_3
    addi x10, x30, 0
clip_low_3:
    bge x31, x10, clip_high_4
    addi x10, x31, 0
clip_high_4:
    sb x10, 0(x6)
    addi x6, x6, 1
    addi x13, x13, 4
    addi x14, x14, -1
    bne x14, x0, cpu_fc_out_1
    lui x17, 0xa41
    addi x17, x17, -1854
    lui x18, 0x400
    lui x5, 0x80002
    addi x5, x5, -96
    lui x6, 0x80002
    addi x6, x6, -108
    addi x7, x0, 12
cpu_relu_5:
    lb x10, 0(x5)
    bge x10, x0, relu_6
    addi x10, x0, 0
relu_6:
    mul x10, x10, x17
    add x10, x10, x18
    srai x10, x10, 23
    bge x10, x30, clip_low_7
    addi x10, x30, 0
clip_low_7:
    bge x31, x10, clip_high_8
    addi x10, x31, 0
clip_high_8:
    sb x10, 0(x6)
    addi x5, x5, 1
    addi x6, x6, 1
    addi x7, x7, -1
    bne x7, x0, cpu_relu_5
    lui x17, 0x80002
    addi x17, x17, -684
    lui x5, 0x80002
    addi x5, x5, -108
    lui x6, 0x80002
    addi x6, x6, -120
    addi x7, x0, 12
cpu_sigmoid_9:
    lb x10, 0(x5)
    addi x10, x10, 128
    add x10, x10, x17
    lb x10, 0(x10)
    sb x10, 0(x6)
    addi x5, x5, 1
    addi x6, x6, 1
    addi x7, x7, -1
    bne x7, x0, cpu_sigmoid_9
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
cpu_mul_10:
    lb x10, 0(x5)
    lb x11, 0(x12)
    addi x12, x12, 1
    mul x10, x10, x11
    mul x10, x10, x17
    add x10, x10, x18
    srai x10, x10, 23
    bge x10, x30, clip_low_11
    addi x10, x30, 0
clip_low_11:
    bge x31, x10, clip_high_12
    addi x10, x31, 0
clip_high_12:
    sb x10, 0(x6)
    addi x5, x5, 1
    addi x6, x6, 1
    addi x7, x7, -1
    bne x7, x0, cpu_mul_10
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
cpu_add_13:
    lb x10, 0(x5)
    lb x11, 0(x12)
    addi x12, x12, 1
    mul x10, x10, x17
    mul x11, x11, x19
    add x10, x10, x11
    add x10, x10, x18
    srai x10, x10, 23
    bge x10, x30, clip_low_14
    addi x10, x30, 0
clip_low_14:
    bge x31, x10, clip_high_15
    addi x10, x31, 0
clip_high_15:
    sb x10, 0(x6)
    addi x5, x5, 1
    addi x6, x6, 1
    addi x7, x7, -1
    bne x7, x0, cpu_add_13
    lui x17, 0x2
    addi x17, x17, 1358
    lui x18, 0x100
    lui x12, 0x80002
    addi x12, x12, -764
    lui x13, 0x80002
    addi x13, x13, -704
    lui x6, 0x80002
    addi x6, x6, -152
    addi x14, x0, 5
cpu_fc_out_16:
    lw x10, 0(x13)
    lui x5, 0x80002
    addi x5, x5, -144
    addi x7, x0, 12
cpu_fc_dot_17:
    lb x8, 0(x5)
    lb x9, 0(x12)
    mul x8, x8, x9
    add x10, x10, x8
    addi x5, x5, 1
    addi x12, x12, 1
    addi x7, x7, -1
    bne x7, x0, cpu_fc_dot_17
    mul x10, x10, x17
    add x10, x10, x18
    srai x10, x10, 21
    bge x10, x30, clip_low_18
    addi x10, x30, 0
clip_low_18:
    bge x31, x10, clip_high_19
    addi x10, x31, 0
clip_high_19:
    sb x10, 0(x6)
    addi x6, x6, 1
    addi x13, x13, 4
    addi x14, x14, -1
    bne x14, x0, cpu_fc_out_16
    lui x17, 0x800
    addi x17, x17, 1
    lui x18, 0x400
    lui x5, 0x80002
    addi x5, x5, -152
    lui x6, 0x80002
    addi x6, x6, -160
    addi x7, x0, 5
cpu_mul_20:
    lb x10, 0(x5)
    mul x10, x10, x17
    add x10, x10, x18
    srai x10, x10, 23
    bge x10, x30, clip_low_21
    addi x10, x30, 0
clip_low_21:
    bge x31, x10, clip_high_22
    addi x10, x31, 0
clip_high_22:
    sb x10, 0(x6)
    addi x5, x5, 1
    addi x6, x6, 1
    addi x7, x7, -1
    bne x7, x0, cpu_mul_20
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
cpu_add_23:
    lb x10, 0(x5)
    mul x10, x10, x17
    add x10, x10, x19
    add x10, x10, x18
    srai x10, x10, 23
    bge x10, x30, clip_low_24
    addi x10, x30, 0
clip_low_24:
    bge x31, x10, clip_high_25
    addi x10, x31, 0
clip_high_25:
    sb x10, 0(x6)
    addi x5, x5, 1
    addi x6, x6, 1
    addi x7, x7, -1
    bne x7, x0, cpu_add_23
    lui x17, 0x80002
    addi x17, x17, -1276
    addi x19, x0, 534
    lui x5, 0x80002
    addi x5, x5, -168
    addi x7, x0, 5
    addi x14, x0, -128
softmax_max_26:
    lb x10, 0(x5)
    bge x14, x10, keep_max_27
    addi x14, x10, 0
keep_max_27:
    addi x5, x5, 1
    addi x7, x7, -1
    bne x7, x0, softmax_max_26
    lui x5, 0x80002
    addi x5, x5, -168
    addi x7, x0, 5
    addi x15, x0, 0
softmax_sum_28:
    lb x10, 0(x5)
    sub x10, x10, x14
    addi x10, x10, 255
    slli x10, x10, 1
    add x10, x10, x17
    lhu x10, 0(x10)
    add x15, x15, x10
    addi x5, x5, 1
    addi x7, x7, -1
    bne x7, x0, softmax_sum_28
    lui x5, 0x80002
    addi x5, x5, -168
    lui x6, 0x80002
    addi x6, x6, -176
    addi x7, x0, 5
    srai x18, x15, 1
softmax_normalize_29:
    lb x10, 0(x5)
    sub x10, x10, x14
    addi x10, x10, 255
    slli x10, x10, 1
    add x10, x10, x17
    lhu x10, 0(x10)
    mul x10, x10, x19
    add x10, x10, x18
    divu x10, x10, x15
    bge x31, x10, softmax_clip_30
    addi x10, x31, 0
softmax_clip_30:
    sb x10, 0(x6)
    addi x5, x5, 1
    addi x6, x6, 1
    addi x7, x7, -1
    bne x7, x0, softmax_normalize_29
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
