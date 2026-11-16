    addi x30, x0, -128
    addi x31, x0, 127
    addi x5, x0, 2
    lui x6, 0x70000
    sw x5, 0(x6)
    addi x5, x0, 1
    lui x6, 0x70000
    addi x6, x6, 60
    sw x5, 0(x6)
    addi x5, x0, 17
    lui x6, 0x70000
    addi x6, x6, 128
    sw x5, 0(x6)
    addi x5, x0, 12
    lui x6, 0x70000
    addi x6, x6, 132
    sw x5, 0(x6)
    addi x5, x0, 1
    lui x6, 0x70000
    addi x6, x6, 24
    sw x5, 0(x6)
    lui x5, 0x80002
    addi x5, x5, -512
    lui x6, 0x70000
    addi x6, x6, 32
    sw x5, 0(x6)
    lui x5, 0x80002
    addi x5, x5, -84
    lui x6, 0x70000
    addi x6, x6, 64
    addi x7, x0, 5
load_input_1:
    lw x8, 0(x5)
    sw x8, 0(x6)
    addi x5, x5, 4
    addi x6, x6, 4
    addi x7, x7, -1
    bne x7, x0, load_input_1
    lui x5, 0x80002
    addi x5, x5, -224
    lui x6, 0x70001
    addi x6, x6, -1600
    addi x7, x0, 12
load_bias_2:
    lw x8, 0(x5)
    sw x8, 0(x6)
    addi x5, x5, 4
    addi x6, x6, 4
    addi x7, x7, -1
    bne x7, x0, load_bias_2
    addi x5, x0, 1
    lui x6, 0x70000
    sw x5, 0(x6)
    lui x6, 0x70000
    addi x6, x6, 4
    lui x7, 0x5
    addi x7, x7, -480
wait_npu_3:
    lw x8, 0(x6)
    addi x9, x0, 1
    beq x8, x9, npu_finished_4
    andi x9, x8, 4
    beq x9, x0, skip_fail_5
    jal x0, fail
skip_fail_5:
    addi x7, x7, -1
    bne x7, x0, wait_npu_3
    jal x0, fail
npu_finished_4:
    lui x17, 0x2
    addi x17, x17, -1953
    lui x18, 0x100
    lui x5, 0x70001
    addi x5, x5, 1024
    lui x6, 0x80002
    addi x6, x6, -96
    addi x7, x0, 12
read_npu_6:
    lw x10, 0(x5)
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
    addi x5, x5, 4
    addi x6, x6, 1
    addi x7, x7, -1
    bne x7, x0, read_npu_6
    lui x17, 0xa41
    addi x17, x17, -1854
    lui x18, 0x400
    lui x5, 0x80002
    addi x5, x5, -96
    lui x6, 0x80002
    addi x6, x6, -108
    addi x7, x0, 12
cpu_relu_9:
    lb x10, 0(x5)
    bge x10, x0, relu_10
    addi x10, x0, 0
relu_10:
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
    bne x7, x0, cpu_relu_9
    lui x17, 0x80002
    addi x17, x17, -768
    lui x5, 0x80002
    addi x5, x5, -108
    lui x6, 0x80002
    addi x6, x6, -120
    addi x7, x0, 12
cpu_sigmoid_13:
    lb x10, 0(x5)
    addi x10, x10, 128
    add x10, x10, x17
    lb x10, 0(x10)
    sb x10, 0(x6)
    addi x5, x5, 1
    addi x6, x6, 1
    addi x7, x7, -1
    bne x7, x0, cpu_sigmoid_13
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
cpu_mul_14:
    lb x10, 0(x5)
    lb x11, 0(x12)
    addi x12, x12, 1
    mul x10, x10, x11
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
    addi x5, x5, 1
    addi x6, x6, 1
    addi x7, x7, -1
    bne x7, x0, cpu_mul_14
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
cpu_add_17:
    lb x10, 0(x5)
    lb x11, 0(x12)
    addi x12, x12, 1
    mul x10, x10, x17
    mul x11, x11, x19
    add x10, x10, x11
    add x10, x10, x18
    srai x10, x10, 23
    bge x10, x30, clip_low_18
    addi x10, x30, 0
clip_low_18:
    bge x31, x10, clip_high_19
    addi x10, x31, 0
clip_high_19:
    sb x10, 0(x6)
    addi x5, x5, 1
    addi x6, x6, 1
    addi x7, x7, -1
    bne x7, x0, cpu_add_17
    addi x5, x0, 2
    lui x6, 0x70000
    sw x5, 0(x6)
    addi x5, x0, 1
    lui x6, 0x70000
    addi x6, x6, 60
    sw x5, 0(x6)
    addi x5, x0, 12
    lui x6, 0x70000
    addi x6, x6, 128
    sw x5, 0(x6)
    addi x5, x0, 5
    lui x6, 0x70000
    addi x6, x6, 132
    sw x5, 0(x6)
    addi x5, x0, 1
    lui x6, 0x70000
    addi x6, x6, 24
    sw x5, 0(x6)
    lui x5, 0x80002
    addi x5, x5, -884
    lui x6, 0x70000
    addi x6, x6, 32
    sw x5, 0(x6)
    lui x5, 0x80002
    addi x5, x5, -144
    lui x6, 0x70000
    addi x6, x6, 64
    addi x7, x0, 3
load_input_20:
    lw x8, 0(x5)
    sw x8, 0(x6)
    addi x5, x5, 4
    addi x6, x6, 4
    addi x7, x7, -1
    bne x7, x0, load_input_20
    lui x5, 0x80002
    addi x5, x5, -788
    lui x6, 0x70001
    addi x6, x6, -1600
    addi x7, x0, 5
load_bias_21:
    lw x8, 0(x5)
    sw x8, 0(x6)
    addi x5, x5, 4
    addi x6, x6, 4
    addi x7, x7, -1
    bne x7, x0, load_bias_21
    addi x5, x0, 1
    lui x6, 0x70000
    sw x5, 0(x6)
    lui x6, 0x70000
    addi x6, x6, 4
    lui x7, 0x5
    addi x7, x7, -480
wait_npu_22:
    lw x8, 0(x6)
    addi x9, x0, 1
    beq x8, x9, npu_finished_23
    andi x9, x8, 4
    beq x9, x0, skip_fail_24
    jal x0, fail
skip_fail_24:
    addi x7, x7, -1
    bne x7, x0, wait_npu_22
    jal x0, fail
npu_finished_23:
    lui x17, 0x2
    addi x17, x17, 1358
    lui x18, 0x100
    lui x5, 0x70001
    addi x5, x5, 1024
    lui x6, 0x80002
    addi x6, x6, -152
    addi x7, x0, 5
read_npu_25:
    lw x10, 0(x5)
    mul x10, x10, x17
    add x10, x10, x18
    srai x10, x10, 21
    bge x10, x30, clip_low_26
    addi x10, x30, 0
clip_low_26:
    bge x31, x10, clip_high_27
    addi x10, x31, 0
clip_high_27:
    sb x10, 0(x6)
    addi x5, x5, 4
    addi x6, x6, 1
    addi x7, x7, -1
    bne x7, x0, read_npu_25
    lui x17, 0x800
    addi x17, x17, 1
    lui x18, 0x400
    lui x5, 0x80002
    addi x5, x5, -152
    lui x6, 0x80002
    addi x6, x6, -160
    addi x7, x0, 5
cpu_mul_28:
    lb x10, 0(x5)
    mul x10, x10, x17
    add x10, x10, x18
    srai x10, x10, 23
    bge x10, x30, clip_low_29
    addi x10, x30, 0
clip_low_29:
    bge x31, x10, clip_high_30
    addi x10, x31, 0
clip_high_30:
    sb x10, 0(x6)
    addi x5, x5, 1
    addi x6, x6, 1
    addi x7, x7, -1
    bne x7, x0, cpu_mul_28
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
cpu_add_31:
    lb x10, 0(x5)
    mul x10, x10, x17
    add x10, x10, x19
    add x10, x10, x18
    srai x10, x10, 23
    bge x10, x30, clip_low_32
    addi x10, x30, 0
clip_low_32:
    bge x31, x10, clip_high_33
    addi x10, x31, 0
clip_high_33:
    sb x10, 0(x6)
    addi x5, x5, 1
    addi x6, x6, 1
    addi x7, x7, -1
    bne x7, x0, cpu_add_31
    lui x17, 0x80002
    addi x17, x17, -1396
    addi x19, x0, 534
    lui x5, 0x80002
    addi x5, x5, -168
    addi x7, x0, 5
    addi x14, x0, -128
softmax_max_34:
    lb x10, 0(x5)
    bge x14, x10, keep_max_35
    addi x14, x10, 0
keep_max_35:
    addi x5, x5, 1
    addi x7, x7, -1
    bne x7, x0, softmax_max_34
    lui x5, 0x80002
    addi x5, x5, -168
    addi x7, x0, 5
    addi x15, x0, 0
softmax_sum_36:
    lb x10, 0(x5)
    sub x10, x10, x14
    addi x10, x10, 255
    slli x10, x10, 1
    add x10, x10, x17
    lhu x10, 0(x10)
    add x15, x15, x10
    addi x5, x5, 1
    addi x7, x7, -1
    bne x7, x0, softmax_sum_36
    lui x5, 0x80002
    addi x5, x5, -168
    lui x6, 0x80002
    addi x6, x6, -176
    addi x7, x0, 5
    srai x18, x15, 1
softmax_normalize_37:
    lb x10, 0(x5)
    sub x10, x10, x14
    addi x10, x10, 255
    slli x10, x10, 1
    add x10, x10, x17
    lhu x10, 0(x10)
    mul x10, x10, x19
    add x10, x10, x18
    divu x10, x10, x15
    bge x31, x10, softmax_clip_38
    addi x10, x31, 0
softmax_clip_38:
    sb x10, 0(x6)
    addi x5, x5, 1
    addi x6, x6, 1
    addi x7, x7, -1
    bne x7, x0, softmax_normalize_37
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
