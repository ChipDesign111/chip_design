    addi x30, x0, -128
    addi x31, x0, 127
    addi x17, x0, 275
    lui x18, 0x400
    lui x12, 0x80000
    addi x12, x12, 1824
    lui x13, 0x80002
    addi x13, x13, -1248
    lui x6, 0x80002
    addi x6, x6, -1168
    addi x14, x0, 20
cpu_fc_out_1:
    lw x10, 0(x13)
    lui x5, 0x80002
    addi x5, x5, -1088
    addi x7, x0, 256
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
    srai x10, x10, 23
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
    lui x12, 0x80000
    addi x12, x12, 1824
    lui x13, 0x80002
    addi x13, x13, -1248
    lui x6, 0x80002
    addi x6, x6, -1148
    addi x14, x0, 20
cpu_fc_out_5:
    lw x10, 0(x13)
    lui x5, 0x80002
    addi x5, x5, -832
    addi x7, x0, 256
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
    srai x10, x10, 23
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
    lui x12, 0x80000
    addi x12, x12, 1824
    lui x13, 0x80002
    addi x13, x13, -1248
    lui x6, 0x80002
    addi x6, x6, -1128
    addi x14, x0, 20
cpu_fc_out_9:
    lw x10, 0(x13)
    lui x5, 0x80002
    addi x5, x5, -576
    addi x7, x0, 256
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
    srai x10, x10, 23
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
    lui x12, 0x80000
    addi x12, x12, 1824
    lui x13, 0x80002
    addi x13, x13, -1248
    lui x6, 0x80002
    addi x6, x6, -1108
    addi x14, x0, 20
cpu_fc_out_13:
    lw x10, 0(x13)
    lui x5, 0x80002
    addi x5, x5, -320
    addi x7, x0, 256
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
    srai x10, x10, 23
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
