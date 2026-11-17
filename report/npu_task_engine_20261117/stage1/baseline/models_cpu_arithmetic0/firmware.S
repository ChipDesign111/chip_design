    addi x30, x0, -128
    addi x31, x0, 127
    lui x17, 0xffc00
    lui x18, 0x400
    lui x19, 0x1fc00
    lui x5, 0x80002
    addi x5, x5, -80
    lui x6, 0x80002
    addi x6, x6, -96
    addi x7, x0, 7
cpu_sub_1:
    lb x10, 0(x5)
    mul x10, x10, x17
    add x10, x10, x19
    add x10, x10, x18
    srai x10, x10, 23
    bge x10, x30, clip_low_2
    addi x10, x30, 0
clip_low_2:
    bge x31, x10, clip_high_3
    addi x10, x31, 0
clip_high_3:
    sb x10, 0(x6)
    addi x5, x5, 1
    addi x6, x6, 1
    addi x7, x7, -1
    bne x7, x0, cpu_sub_1
    lui x5, 0x80002
    addi x5, x5, -72
    lui x6, 0x80002
    addi x6, x6, -88
    addi x7, x0, 7
cpu_sub_4:
    lb x10, 0(x5)
    mul x10, x10, x17
    add x10, x10, x19
    add x10, x10, x18
    srai x10, x10, 23
    bge x10, x30, clip_low_5
    addi x10, x30, 0
clip_low_5:
    bge x31, x10, clip_high_6
    addi x10, x31, 0
clip_high_6:
    sb x10, 0(x6)
    addi x5, x5, 1
    addi x6, x6, 1
    addi x7, x7, -1
    bne x7, x0, cpu_sub_4
    lui x17, 0x800
    lui x18, 0x400
    lui x5, 0x80002
    addi x5, x5, -80
    lui x6, 0x80002
    addi x6, x6, -112
    addi x7, x0, 7
cpu_mul_7:
    lb x10, 0(x5)
    mul x10, x10, x17
    add x10, x10, x18
    srai x10, x10, 23
    bge x10, x30, clip_low_8
    addi x10, x30, 0
clip_low_8:
    bge x31, x10, clip_high_9
    addi x10, x31, 0
clip_high_9:
    sb x10, 0(x6)
    addi x5, x5, 1
    addi x6, x6, 1
    addi x7, x7, -1
    bne x7, x0, cpu_mul_7
    lui x5, 0x80002
    addi x5, x5, -72
    lui x6, 0x80002
    addi x6, x6, -104
    addi x7, x0, 7
cpu_mul_10:
    lb x10, 0(x5)
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
    lui x17, 0x666
    addi x17, x17, 1638
    lui x18, 0x400
    lui x19, 0xffe66
    addi x19, x19, 1638
    lui x5, 0x80002
    addi x5, x5, -96
    lui x6, 0x80002
    addi x6, x6, -128
    addi x7, x0, 7
    lui x12, 0x80002
    addi x12, x12, -112
cpu_sub_13:
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
    bne x7, x0, cpu_sub_13
    lui x5, 0x80002
    addi x5, x5, -88
    lui x6, 0x80002
    addi x6, x6, -120
    addi x7, x0, 7
    lui x12, 0x80002
    addi x12, x12, -104
cpu_sub_16:
    lb x10, 0(x5)
    lb x11, 0(x12)
    addi x12, x12, 1
    mul x10, x10, x17
    mul x11, x11, x19
    add x10, x10, x11
    add x10, x10, x18
    srai x10, x10, 23
    bge x10, x30, clip_low_17
    addi x10, x30, 0
clip_low_17:
    bge x31, x10, clip_high_18
    addi x10, x31, 0
clip_high_18:
    sb x10, 0(x6)
    addi x5, x5, 1
    addi x6, x6, 1
    addi x7, x7, -1
    bne x7, x0, cpu_sub_16
    lui x17, 0x80002
    addi x17, x17, -656
    addi x19, x0, 494
    lui x5, 0x80002
    addi x5, x5, -128
    addi x7, x0, 7
    addi x14, x0, -128
softmax_max_19:
    lb x10, 0(x5)
    bge x14, x10, keep_max_20
    addi x14, x10, 0
keep_max_20:
    addi x5, x5, 1
    addi x7, x7, -1
    bne x7, x0, softmax_max_19
    lui x5, 0x80002
    addi x5, x5, -128
    addi x7, x0, 7
    addi x15, x0, 0
softmax_sum_21:
    lb x10, 0(x5)
    sub x10, x10, x14
    addi x10, x10, 255
    slli x10, x10, 1
    add x10, x10, x17
    lhu x10, 0(x10)
    add x15, x15, x10
    addi x5, x5, 1
    addi x7, x7, -1
    bne x7, x0, softmax_sum_21
    lui x5, 0x80002
    addi x5, x5, -128
    lui x6, 0x80002
    addi x6, x6, -144
    addi x7, x0, 7
    srai x18, x15, 1
softmax_normalize_22:
    lb x10, 0(x5)
    sub x10, x10, x14
    addi x10, x10, 255
    slli x10, x10, 1
    add x10, x10, x17
    lhu x10, 0(x10)
    mul x10, x10, x19
    add x10, x10, x18
    divu x10, x10, x15
    bge x31, x10, softmax_clip_23
    addi x10, x31, 0
softmax_clip_23:
    sb x10, 0(x6)
    addi x5, x5, 1
    addi x6, x6, 1
    addi x7, x7, -1
    bne x7, x0, softmax_normalize_22
    lui x5, 0x80002
    addi x5, x5, -120
    addi x7, x0, 7
    addi x14, x0, -128
softmax_max_24:
    lb x10, 0(x5)
    bge x14, x10, keep_max_25
    addi x14, x10, 0
keep_max_25:
    addi x5, x5, 1
    addi x7, x7, -1
    bne x7, x0, softmax_max_24
    lui x5, 0x80002
    addi x5, x5, -120
    addi x7, x0, 7
    addi x15, x0, 0
softmax_sum_26:
    lb x10, 0(x5)
    sub x10, x10, x14
    addi x10, x10, 255
    slli x10, x10, 1
    add x10, x10, x17
    lhu x10, 0(x10)
    add x15, x15, x10
    addi x5, x5, 1
    addi x7, x7, -1
    bne x7, x0, softmax_sum_26
    lui x5, 0x80002
    addi x5, x5, -120
    lui x6, 0x80002
    addi x6, x6, -136
    addi x7, x0, 7
    srai x18, x15, 1
softmax_normalize_27:
    lb x10, 0(x5)
    sub x10, x10, x14
    addi x10, x10, 255
    slli x10, x10, 1
    add x10, x10, x17
    lhu x10, 0(x10)
    mul x10, x10, x19
    add x10, x10, x18
    divu x10, x10, x15
    bge x31, x10, softmax_clip_28
    addi x10, x31, 0
softmax_clip_28:
    sb x10, 0(x6)
    addi x5, x5, 1
    addi x6, x6, 1
    addi x7, x7, -1
    bne x7, x0, softmax_normalize_27
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
