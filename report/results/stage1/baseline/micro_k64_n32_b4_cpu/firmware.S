    addi x30, x0, -128
    addi x31, x0, 127
    lui x17, 0x1
    addi x17, x17, 1745
    lui x18, 0x100
    lui x12, 0x80001
    addi x12, x12, 1472
    lui x13, 0x80002
    addi x13, x13, -576
    lui x6, 0x80002
    addi x6, x6, -448
    addi x14, x0, 32
cpu_fc_out_1:
    lw x10, 0(x13)
    lui x5, 0x80002
    addi x5, x5, -320
    addi x7, x0, 64
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
    lui x12, 0x80001
    addi x12, x12, 1472
    lui x13, 0x80002
    addi x13, x13, -576
    lui x6, 0x80002
    addi x6, x6, -416
    addi x14, x0, 32
cpu_fc_out_5:
    lw x10, 0(x13)
    lui x5, 0x80002
    addi x5, x5, -256
    addi x7, x0, 64
cpu_fc_dot_6:
    lb x8, 0(x5)
    lb x9, 0(x12)
    mul x8, x8, x9
    add x10, x10, x8
    addi x5, x5, 1
    addi x12, x12, 1
    addi x7, x7, -1
    bne x7, x0, cpu_fc_dot_6
    mul x10, x10, x17
    add x10, x10, x18
    srai x10, x10, 21
    bge x10, x30, clip_low_7
    addi x10, x30, 0
clip_low_7:
    bge x31, x10, clip_high_8
    addi x10, x31, 0
clip_high_8:
    sb x10, 0(x6)
    addi x6, x6, 1
    addi x13, x13, 4
    addi x14, x14, -1
    bne x14, x0, cpu_fc_out_5
    lui x12, 0x80001
    addi x12, x12, 1472
    lui x13, 0x80002
    addi x13, x13, -576
    lui x6, 0x80002
    addi x6, x6, -384
    addi x14, x0, 32
cpu_fc_out_9:
    lw x10, 0(x13)
    lui x5, 0x80002
    addi x5, x5, -192
    addi x7, x0, 64
cpu_fc_dot_10:
    lb x8, 0(x5)
    lb x9, 0(x12)
    mul x8, x8, x9
    add x10, x10, x8
    addi x5, x5, 1
    addi x12, x12, 1
    addi x7, x7, -1
    bne x7, x0, cpu_fc_dot_10
    mul x10, x10, x17
    add x10, x10, x18
    srai x10, x10, 21
    bge x10, x30, clip_low_11
    addi x10, x30, 0
clip_low_11:
    bge x31, x10, clip_high_12
    addi x10, x31, 0
clip_high_12:
    sb x10, 0(x6)
    addi x6, x6, 1
    addi x13, x13, 4
    addi x14, x14, -1
    bne x14, x0, cpu_fc_out_9
    lui x12, 0x80001
    addi x12, x12, 1472
    lui x13, 0x80002
    addi x13, x13, -576
    lui x6, 0x80002
    addi x6, x6, -352
    addi x14, x0, 32
cpu_fc_out_13:
    lw x10, 0(x13)
    lui x5, 0x80002
    addi x5, x5, -128
    addi x7, x0, 64
cpu_fc_dot_14:
    lb x8, 0(x5)
    lb x9, 0(x12)
    mul x8, x8, x9
    add x10, x10, x8
    addi x5, x5, 1
    addi x12, x12, 1
    addi x7, x7, -1
    bne x7, x0, cpu_fc_dot_14
    mul x10, x10, x17
    add x10, x10, x18
    srai x10, x10, 21
    bge x10, x30, clip_low_15
    addi x10, x30, 0
clip_low_15:
    bge x31, x10, clip_high_16
    addi x10, x31, 0
clip_high_16:
    sb x10, 0(x6)
    addi x6, x6, 1
    addi x13, x13, 4
    addi x14, x14, -1
    bne x14, x0, cpu_fc_out_13
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
