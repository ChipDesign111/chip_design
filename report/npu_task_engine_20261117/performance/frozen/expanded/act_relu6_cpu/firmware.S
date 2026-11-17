    addi x30, x0, -128
    addi x31, x0, 127
    lui x17, 0x3
    addi x17, x17, -1501
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
    lui x17, 0xae0
    addi x17, x17, 845
    lui x18, 0x400
    addi x19, x0, 127
    lui x5, 0x80002
    addi x5, x5, -144
    lui x6, 0x80002
    addi x6, x6, -176
    addi x7, x0, 7
cpu_relu6_17:
    lb x10, 0(x5)
    bge x10, x0, relu_18
    addi x10, x0, 0
relu_18:
    mul x10, x10, x17
    add x10, x10, x18
    srai x10, x10, 23
    bge x10, x30, clip_low_19
    addi x10, x30, 0
clip_low_19:
    bge x31, x10, clip_high_20
    addi x10, x31, 0
clip_high_20:
    bge x19, x10, relu6_cap_21
    addi x10, x19, 0
relu6_cap_21:
    sb x10, 0(x6)
    addi x5, x5, 1
    addi x6, x6, 1
    addi x7, x7, -1
    bne x7, x0, cpu_relu6_17
    lui x5, 0x80002
    addi x5, x5, -136
    lui x6, 0x80002
    addi x6, x6, -168
    addi x7, x0, 7
cpu_relu6_22:
    lb x10, 0(x5)
    bge x10, x0, relu_23
    addi x10, x0, 0
relu_23:
    mul x10, x10, x17
    add x10, x10, x18
    srai x10, x10, 23
    bge x10, x30, clip_low_24
    addi x10, x30, 0
clip_low_24:
    bge x31, x10, clip_high_25
    addi x10, x31, 0
clip_high_25:
    bge x19, x10, relu6_cap_26
    addi x10, x19, 0
relu6_cap_26:
    sb x10, 0(x6)
    addi x5, x5, 1
    addi x6, x6, 1
    addi x7, x7, -1
    bne x7, x0, cpu_relu6_22
    lui x5, 0x80002
    addi x5, x5, -128
    lui x6, 0x80002
    addi x6, x6, -160
    addi x7, x0, 7
cpu_relu6_27:
    lb x10, 0(x5)
    bge x10, x0, relu_28
    addi x10, x0, 0
relu_28:
    mul x10, x10, x17
    add x10, x10, x18
    srai x10, x10, 23
    bge x10, x30, clip_low_29
    addi x10, x30, 0
clip_low_29:
    bge x31, x10, clip_high_30
    addi x10, x31, 0
clip_high_30:
    bge x19, x10, relu6_cap_31
    addi x10, x19, 0
relu6_cap_31:
    sb x10, 0(x6)
    addi x5, x5, 1
    addi x6, x6, 1
    addi x7, x7, -1
    bne x7, x0, cpu_relu6_27
    lui x5, 0x80002
    addi x5, x5, -120
    lui x6, 0x80002
    addi x6, x6, -152
    addi x7, x0, 7
cpu_relu6_32:
    lb x10, 0(x5)
    bge x10, x0, relu_33
    addi x10, x0, 0
relu_33:
    mul x10, x10, x17
    add x10, x10, x18
    srai x10, x10, 23
    bge x10, x30, clip_low_34
    addi x10, x30, 0
clip_low_34:
    bge x31, x10, clip_high_35
    addi x10, x31, 0
clip_high_35:
    bge x19, x10, relu6_cap_36
    addi x10, x19, 0
relu6_cap_36:
    sb x10, 0(x6)
    addi x5, x5, 1
    addi x6, x6, 1
    addi x7, x7, -1
    bne x7, x0, cpu_relu6_32
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
