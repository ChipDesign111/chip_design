    addi x30, x0, -128
    addi x31, x0, 127
    lui x17, 0x4
    addi x17, x17, -1040
    lui x18, 0x200
    lui x12, 0x80002
    addi x12, x12, -268
    lui x13, 0x80002
    addi x13, x13, -204
    lui x6, 0x80002
    addi x6, x6, -144
    addi x14, x0, 7
cpu_fc_out_1:
    lw x10, 0(x13)
    lui x5, 0x80002
    addi x5, x5, -112
    addi x7, x0, 9
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
    srai x10, x10, 22
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
    lui x12, 0x80002
    addi x12, x12, -268
    lui x13, 0x80002
    addi x13, x13, -204
    lui x6, 0x80002
    addi x6, x6, -136
    addi x14, x0, 7
cpu_fc_out_5:
    lw x10, 0(x13)
    lui x5, 0x80002
    addi x5, x5, -100
    addi x7, x0, 9
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
    srai x10, x10, 22
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
    lui x12, 0x80002
    addi x12, x12, -268
    lui x13, 0x80002
    addi x13, x13, -204
    lui x6, 0x80002
    addi x6, x6, -128
    addi x14, x0, 7
cpu_fc_out_9:
    lw x10, 0(x13)
    lui x5, 0x80002
    addi x5, x5, -88
    addi x7, x0, 9
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
    srai x10, x10, 22
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
    lui x12, 0x80002
    addi x12, x12, -268
    lui x13, 0x80002
    addi x13, x13, -204
    lui x6, 0x80002
    addi x6, x6, -120
    addi x14, x0, 7
cpu_fc_out_13:
    lw x10, 0(x13)
    lui x5, 0x80002
    addi x5, x5, -76
    addi x7, x0, 9
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
    srai x10, x10, 22
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
    lui x17, 0x800
    lui x18, 0x400
    lui x19, 0x214
    addi x19, x19, 1966
    lui x20, 0x800
    lui x5, 0x80002
    addi x5, x5, -144
    lui x6, 0x80002
    addi x6, x6, -176
    addi x7, x0, 7
cpu_leaky_relu_17:
    lb x10, 0(x5)
    bge x10, x0, leaky_positive_18
    mul x10, x10, x19
    add x10, x10, x20
    srai x10, x10, 24
    bge x10, x30, clip_low_20
    addi x10, x30, 0
clip_low_20:
    bge x31, x10, clip_high_21
    addi x10, x31, 0
clip_high_21:
    jal x0, leaky_finished_19
leaky_positive_18:
    mul x10, x10, x17
    add x10, x10, x18
    srai x10, x10, 23
    bge x10, x30, clip_low_22
    addi x10, x30, 0
clip_low_22:
    bge x31, x10, clip_high_23
    addi x10, x31, 0
clip_high_23:
leaky_finished_19:
    sb x10, 0(x6)
    addi x5, x5, 1
    addi x6, x6, 1
    addi x7, x7, -1
    bne x7, x0, cpu_leaky_relu_17
    lui x5, 0x80002
    addi x5, x5, -136
    lui x6, 0x80002
    addi x6, x6, -168
    addi x7, x0, 7
cpu_leaky_relu_24:
    lb x10, 0(x5)
    bge x10, x0, leaky_positive_25
    mul x10, x10, x19
    add x10, x10, x20
    srai x10, x10, 24
    bge x10, x30, clip_low_27
    addi x10, x30, 0
clip_low_27:
    bge x31, x10, clip_high_28
    addi x10, x31, 0
clip_high_28:
    jal x0, leaky_finished_26
leaky_positive_25:
    mul x10, x10, x17
    add x10, x10, x18
    srai x10, x10, 23
    bge x10, x30, clip_low_29
    addi x10, x30, 0
clip_low_29:
    bge x31, x10, clip_high_30
    addi x10, x31, 0
clip_high_30:
leaky_finished_26:
    sb x10, 0(x6)
    addi x5, x5, 1
    addi x6, x6, 1
    addi x7, x7, -1
    bne x7, x0, cpu_leaky_relu_24
    lui x5, 0x80002
    addi x5, x5, -128
    lui x6, 0x80002
    addi x6, x6, -160
    addi x7, x0, 7
cpu_leaky_relu_31:
    lb x10, 0(x5)
    bge x10, x0, leaky_positive_32
    mul x10, x10, x19
    add x10, x10, x20
    srai x10, x10, 24
    bge x10, x30, clip_low_34
    addi x10, x30, 0
clip_low_34:
    bge x31, x10, clip_high_35
    addi x10, x31, 0
clip_high_35:
    jal x0, leaky_finished_33
leaky_positive_32:
    mul x10, x10, x17
    add x10, x10, x18
    srai x10, x10, 23
    bge x10, x30, clip_low_36
    addi x10, x30, 0
clip_low_36:
    bge x31, x10, clip_high_37
    addi x10, x31, 0
clip_high_37:
leaky_finished_33:
    sb x10, 0(x6)
    addi x5, x5, 1
    addi x6, x6, 1
    addi x7, x7, -1
    bne x7, x0, cpu_leaky_relu_31
    lui x5, 0x80002
    addi x5, x5, -120
    lui x6, 0x80002
    addi x6, x6, -152
    addi x7, x0, 7
cpu_leaky_relu_38:
    lb x10, 0(x5)
    bge x10, x0, leaky_positive_39
    mul x10, x10, x19
    add x10, x10, x20
    srai x10, x10, 24
    bge x10, x30, clip_low_41
    addi x10, x30, 0
clip_low_41:
    bge x31, x10, clip_high_42
    addi x10, x31, 0
clip_high_42:
    jal x0, leaky_finished_40
leaky_positive_39:
    mul x10, x10, x17
    add x10, x10, x18
    srai x10, x10, 23
    bge x10, x30, clip_low_43
    addi x10, x30, 0
clip_low_43:
    bge x31, x10, clip_high_44
    addi x10, x31, 0
clip_high_44:
leaky_finished_40:
    sb x10, 0(x6)
    addi x5, x5, 1
    addi x6, x6, 1
    addi x7, x7, -1
    bne x7, x0, cpu_leaky_relu_38
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
