    addi x30, x0, -128
    addi x31, x0, 127
    addi x17, x0, 132
    lui x18, 0x800
    lui x12, 0x80002
    addi x12, x12, -100
    lui x13, 0x80002
    addi x13, x13, -88
    lui x6, 0x80002
    addi x6, x6, -72
    addi x14, x0, 3
cpu_fc_out_1:
    lw x10, 0(x13)
    lui x5, 0x80002
    addi x5, x5, -68
    addi x7, x0, 4
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
    srai x10, x10, 24
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
    lui x17, 0x800
    lui x18, 0x400
    lui x5, 0x80002
    addi x5, x5, -72
    lui x6, 0x80002
    addi x6, x6, -76
    addi x7, x0, 3
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
