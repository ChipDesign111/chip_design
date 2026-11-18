    addi x30, x0, -128
    addi x31, x0, 127
    addi x5, x0, 2
    lui x6, 0x70000
    sw x5, 0(x6)
    addi x5, x0, 0
    lui x6, 0x70000
    addi x6, x6, 60
    sw x5, 0(x6)
    addi x5, x0, 4
    lui x6, 0x70000
    addi x6, x6, 24
    sw x5, 0(x6)
    lui x5, 0x80001
    addi x5, x5, 1312
    lui x6, 0x70000
    addi x6, x6, 32
    sw x5, 0(x6)
    lui x5, 0x80001
    addi x5, x5, 1032
    lui x6, 0x70000
    addi x6, x6, 36
    sw x5, 0(x6)
    addi x5, x0, 275
    lui x6, 0x70000
    addi x6, x6, 16
    sw x5, 0(x6)
    addi x5, x0, 21
    lui x6, 0x70000
    addi x6, x6, 20
    sw x5, 0(x6)
    lui x5, 0x80002
    addi x5, x5, -320
    lui x6, 0x70000
    addi x6, x6, 64
    addi x7, x0, 16
special_input_1:
    lw x8, 0(x5)
    sw x8, 0(x6)
    addi x5, x5, 4
    addi x6, x6, 4
    addi x7, x7, -1
    bne x7, x0, special_input_1
    lui x5, 0x80002
    addi x5, x5, -256
    lui x6, 0x70001
    addi x6, x6, -1024
    addi x7, x0, 16
special_input_2:
    lw x8, 0(x5)
    sw x8, 0(x6)
    addi x5, x5, 4
    addi x6, x6, 4
    addi x7, x7, -1
    bne x7, x0, special_input_2
    lui x5, 0x80002
    addi x5, x5, -192
    lui x6, 0x70001
    addi x7, x0, 16
special_input_3:
    lw x8, 0(x5)
    sw x8, 0(x6)
    addi x5, x5, 4
    addi x6, x6, 4
    addi x7, x7, -1
    bne x7, x0, special_input_3
    lui x5, 0x80002
    addi x5, x5, -128
    lui x6, 0x70001
    addi x6, x6, 64
    addi x7, x0, 16
special_input_4:
    lw x8, 0(x5)
    sw x8, 0(x6)
    addi x5, x5, 4
    addi x6, x6, 4
    addi x7, x7, -1
    bne x7, x0, special_input_4
    lui x5, 0x80002
    addi x5, x5, -736
    lui x6, 0x70001
    addi x6, x6, -1600
    addi x7, x0, 32
special_bias_5:
    lw x8, 0(x5)
    sw x8, 0(x6)
    addi x5, x5, 4
    addi x6, x6, 4
    addi x7, x7, -1
    bne x7, x0, special_bias_5
    lui x5, 0x80001
    addi x5, x5, 1288
    lui x6, 0x70001
    addi x6, x6, -1472
    addi x7, x0, 6
special_bias_6:
    lw x8, 0(x5)
    sw x8, 0(x6)
    addi x5, x5, 4
    addi x6, x6, 4
    addi x7, x7, -1
    bne x7, x0, special_bias_6
    addi x5, x0, 1
    lui x6, 0x70000
    sw x5, 0(x6)
    lui x6, 0x70000
    addi x6, x6, 4
    lui x7, 0x5
    addi x7, x7, -480
special_wait_7:
    lw x8, 0(x6)
    addi x9, x0, 1
    beq x8, x9, special_done_8
    andi x9, x8, 4
    beq x9, x0, skip_fail_9
    jal x0, fail
skip_fail_9:
    addi x7, x7, -1
    bne x7, x0, special_wait_7
    jal x0, fail
special_done_8:
    lui x17, 0x1
    addi x17, x17, -1746
    lui x18, 0x400
    lui x5, 0x70001
    addi x5, x5, -1280
    lui x6, 0x80002
    addi x6, x6, -608
    addi x7, x0, 6
special_scores_10:
    lw x10, 0(x5)
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
    addi x5, x5, 4
    addi x6, x6, 1
    addi x7, x7, -1
    bne x7, x0, special_scores_10
    lui x5, 0x70001
    addi x5, x5, -896
    lui x6, 0x80002
    addi x6, x6, -600
    addi x7, x0, 6
special_scores_13:
    lw x10, 0(x5)
    mul x10, x10, x17
    add x10, x10, x18
    srai x10, x10, 23
    bge x10, x30, clip_low_14
    addi x10, x30, 0
clip_low_14:
    bge x31, x10, clip_high_15
    addi x10, x31, 0
clip_high_15:
    sb x10, 0(x6)
    addi x5, x5, 4
    addi x6, x6, 1
    addi x7, x7, -1
    bne x7, x0, special_scores_13
    lui x5, 0x70001
    addi x5, x5, 544
    lui x6, 0x80002
    addi x6, x6, -592
    addi x7, x0, 6
special_scores_16:
    lw x10, 0(x5)
    mul x10, x10, x17
    add x10, x10, x18
    srai x10, x10, 23
    bge x10, x30, clip_low_17
    addi x10, x30, 0
clip_low_17:
    bge x31, x10, clip_high_18
    addi x10, x31, 0
clip_high_18:
    sb x10, 0(x6)
    addi x5, x5, 4
    addi x6, x6, 1
    addi x7, x7, -1
    bne x7, x0, special_scores_16
    lui x5, 0x70001
    addi x5, x5, 608
    lui x6, 0x80002
    addi x6, x6, -584
    addi x7, x0, 6
special_scores_19:
    lw x10, 0(x5)
    mul x10, x10, x17
    add x10, x10, x18
    srai x10, x10, 23
    bge x10, x30, clip_low_20
    addi x10, x30, 0
clip_low_20:
    bge x31, x10, clip_high_21
    addi x10, x31, 0
clip_high_21:
    sb x10, 0(x6)
    addi x5, x5, 4
    addi x6, x6, 1
    addi x7, x7, -1
    bne x7, x0, special_scores_19
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
