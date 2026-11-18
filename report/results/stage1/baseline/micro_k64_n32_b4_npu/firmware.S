    addi x30, x0, -128
    addi x31, x0, 127
    addi x5, x0, 2
    lui x6, 0x70000
    sw x5, 0(x6)
    addi x5, x0, 1
    lui x6, 0x70000
    addi x6, x6, 60
    sw x5, 0(x6)
    addi x5, x0, 64
    lui x6, 0x70000
    addi x6, x6, 128
    sw x5, 0(x6)
    addi x5, x0, 32
    lui x6, 0x70000
    addi x6, x6, 132
    sw x5, 0(x6)
    addi x5, x0, 4
    lui x6, 0x70000
    addi x6, x6, 24
    sw x5, 0(x6)
    lui x5, 0x80001
    addi x5, x5, 1472
    lui x6, 0x70000
    addi x6, x6, 32
    sw x5, 0(x6)
    lui x5, 0x80002
    addi x5, x5, -320
    lui x6, 0x70000
    addi x6, x6, 64
    addi x7, x0, 16
load_input_1:
    lw x8, 0(x5)
    sw x8, 0(x6)
    addi x5, x5, 4
    addi x6, x6, 4
    addi x7, x7, -1
    bne x7, x0, load_input_1
    lui x5, 0x80002
    addi x5, x5, -256
    lui x6, 0x70001
    addi x6, x6, -1024
    addi x7, x0, 16
load_input_2:
    lw x8, 0(x5)
    sw x8, 0(x6)
    addi x5, x5, 4
    addi x6, x6, 4
    addi x7, x7, -1
    bne x7, x0, load_input_2
    lui x5, 0x80002
    addi x5, x5, -192
    lui x6, 0x70001
    addi x7, x0, 16
load_input_3:
    lw x8, 0(x5)
    sw x8, 0(x6)
    addi x5, x5, 4
    addi x6, x6, 4
    addi x7, x7, -1
    bne x7, x0, load_input_3
    lui x5, 0x80002
    addi x5, x5, -128
    lui x6, 0x70001
    addi x6, x6, 64
    addi x7, x0, 16
load_input_4:
    lw x8, 0(x5)
    sw x8, 0(x6)
    addi x5, x5, 4
    addi x6, x6, 4
    addi x7, x7, -1
    bne x7, x0, load_input_4
    lui x5, 0x80002
    addi x5, x5, -576
    lui x6, 0x70001
    addi x6, x6, -1600
    addi x7, x0, 32
load_bias_5:
    lw x8, 0(x5)
    sw x8, 0(x6)
    addi x5, x5, 4
    addi x6, x6, 4
    addi x7, x7, -1
    bne x7, x0, load_bias_5
    addi x5, x0, 1
    lui x6, 0x70000
    sw x5, 0(x6)
    lui x6, 0x70000
    addi x6, x6, 4
    lui x7, 0x5
    addi x7, x7, -480
wait_npu_6:
    lw x8, 0(x6)
    addi x9, x0, 1
    beq x8, x9, npu_finished_7
    andi x9, x8, 4
    beq x9, x0, skip_fail_8
    jal x0, fail
skip_fail_8:
    addi x7, x7, -1
    bne x7, x0, wait_npu_6
    jal x0, fail
npu_finished_7:
    lui x17, 0x1
    addi x17, x17, 1745
    lui x18, 0x100
    lui x5, 0x70001
    addi x5, x5, 1024
    lui x6, 0x80002
    addi x6, x6, -448
    addi x7, x0, 32
read_npu_9:
    lw x10, 0(x5)
    mul x10, x10, x17
    add x10, x10, x18
    srai x10, x10, 21
    bge x10, x30, clip_low_10
    addi x10, x30, 0
clip_low_10:
    bge x31, x10, clip_high_11
    addi x10, x31, 0
clip_high_11:
    sb x10, 0(x6)
    addi x5, x5, 4
    addi x6, x6, 1
    addi x7, x7, -1
    bne x7, x0, read_npu_9
    lui x5, 0x70001
    addi x5, x5, 1152
    lui x6, 0x80002
    addi x6, x6, -416
    addi x7, x0, 32
read_npu_12:
    lw x10, 0(x5)
    mul x10, x10, x17
    add x10, x10, x18
    srai x10, x10, 21
    bge x10, x30, clip_low_13
    addi x10, x30, 0
clip_low_13:
    bge x31, x10, clip_high_14
    addi x10, x31, 0
clip_high_14:
    sb x10, 0(x6)
    addi x5, x5, 4
    addi x6, x6, 1
    addi x7, x7, -1
    bne x7, x0, read_npu_12
    lui x5, 0x70001
    addi x5, x5, 1280
    lui x6, 0x80002
    addi x6, x6, -384
    addi x7, x0, 32
read_npu_15:
    lw x10, 0(x5)
    mul x10, x10, x17
    add x10, x10, x18
    srai x10, x10, 21
    bge x10, x30, clip_low_16
    addi x10, x30, 0
clip_low_16:
    bge x31, x10, clip_high_17
    addi x10, x31, 0
clip_high_17:
    sb x10, 0(x6)
    addi x5, x5, 4
    addi x6, x6, 1
    addi x7, x7, -1
    bne x7, x0, read_npu_15
    lui x5, 0x70001
    addi x5, x5, 1408
    lui x6, 0x80002
    addi x6, x6, -352
    addi x7, x0, 32
read_npu_18:
    lw x10, 0(x5)
    mul x10, x10, x17
    add x10, x10, x18
    srai x10, x10, 21
    bge x10, x30, clip_low_19
    addi x10, x30, 0
clip_low_19:
    bge x31, x10, clip_high_20
    addi x10, x31, 0
clip_high_20:
    sb x10, 0(x6)
    addi x5, x5, 4
    addi x6, x6, 1
    addi x7, x7, -1
    bne x7, x0, read_npu_18
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
