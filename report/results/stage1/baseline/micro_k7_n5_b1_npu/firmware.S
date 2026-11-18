    addi x30, x0, -128
    addi x31, x0, 127
    addi x5, x0, 2
    lui x6, 0x70000
    sw x5, 0(x6)
    addi x5, x0, 1
    lui x6, 0x70000
    addi x6, x6, 60
    sw x5, 0(x6)
    addi x5, x0, 7
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
    addi x5, x5, -164
    lui x6, 0x70000
    addi x6, x6, 32
    sw x5, 0(x6)
    lui x5, 0x80002
    addi x5, x5, -72
    lui x6, 0x70000
    addi x6, x6, 64
    addi x7, x0, 2
load_input_1:
    lw x8, 0(x5)
    sw x8, 0(x6)
    addi x5, x5, 4
    addi x6, x6, 4
    addi x7, x7, -1
    bne x7, x0, load_input_1
    lui x5, 0x80002
    addi x5, x5, -100
    lui x6, 0x70001
    addi x6, x6, -1600
    addi x7, x0, 5
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
    lui x17, 0x9
    addi x17, x17, -1229
    lui x18, 0x200
    lui x5, 0x70001
    addi x5, x5, 1024
    lui x6, 0x80002
    addi x6, x6, -80
    addi x7, x0, 5
read_npu_6:
    lw x10, 0(x5)
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
    addi x5, x5, 4
    addi x6, x6, 1
    addi x7, x7, -1
    bne x7, x0, read_npu_6
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
