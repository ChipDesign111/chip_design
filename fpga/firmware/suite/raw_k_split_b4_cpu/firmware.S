    lui x31, 0x80002
    addi x31, x31, -64
    addi x30, x0, 1
    sw x30, 0(x31)
    addi x30, x0, -128
    addi x31, x0, 127
    lui x4, 0x80001
    addi x4, x4, -1000
    lui x29, 0x80001
    addi x29, x29, -976
    lui x1, 0x0
    addi x1, x1, 0
    jal x0, fc_runtime
fc_return_1:
    addi x30, x0, -128
    addi x31, x0, 127
    addi x17, x0, 1628
    lui x18, 0x100
    lui x5, 0x80002
    addi x5, x5, -832
    lui x6, 0x80002
    addi x6, x6, -704
    addi x7, x0, 32
fc_quant_2:
    lw x10, 0(x5)
    mul x10,x10,x17
    add x10, x10, x18
    srai x10,x10,1045
    bge x10, x30, clip_low_3
    addi x10, x30, 0
clip_low_3:
    bge x31, x10, clip_high_4
    addi x10, x31, 0
clip_high_4:
    sb x10,0(x6)
    addi x5, x5, 4
    addi x6, x6, 1
    addi x7, x7, -1
    bne x7, x0, fc_quant_2
    lui x4, 0x80001
    addi x4, x4, -1024
    lui x29, 0x80001
    addi x29, x29, -976
    lui x1, 0x0
    addi x1, x1, 0
    jal x0, fc_runtime
fc_return_5:
    addi x30, x0, -128
    addi x31, x0, 127
    addi x17, x0, 1628
    lui x18, 0x100
    lui x5, 0x80002
    addi x5, x5, -832
    lui x6, 0x80002
    addi x6, x6, -672
    addi x7, x0, 32
fc_quant_6:
    lw x10, 0(x5)
    mul x10,x10,x17
    add x10, x10, x18
    srai x10,x10,1045
    bge x10, x30, clip_low_7
    addi x10, x30, 0
clip_low_7:
    bge x31, x10, clip_high_8
    addi x10, x31, 0
clip_high_8:
    sb x10,0(x6)
    addi x5, x5, 4
    addi x6, x6, 1
    addi x7, x7, -1
    bne x7, x0, fc_quant_6
    lui x4, 0x80001
    addi x4, x4, -1048
    lui x29, 0x80001
    addi x29, x29, -976
    lui x1, 0x0
    addi x1, x1, 0
    jal x0, fc_runtime
fc_return_9:
    addi x30, x0, -128
    addi x31, x0, 127
    addi x17, x0, 1628
    lui x18, 0x100
    lui x5, 0x80002
    addi x5, x5, -832
    lui x6, 0x80002
    addi x6, x6, -640
    addi x7, x0, 32
fc_quant_10:
    lw x10, 0(x5)
    mul x10,x10,x17
    add x10, x10, x18
    srai x10,x10,1045
    bge x10, x30, clip_low_11
    addi x10, x30, 0
clip_low_11:
    bge x31, x10, clip_high_12
    addi x10, x31, 0
clip_high_12:
    sb x10,0(x6)
    addi x5, x5, 4
    addi x6, x6, 1
    addi x7, x7, -1
    bne x7, x0, fc_quant_10
    lui x4, 0x80001
    addi x4, x4, -1072
    lui x29, 0x80001
    addi x29, x29, -976
    lui x1, 0x0
    addi x1, x1, 0
    jal x0, fc_runtime
fc_return_13:
    addi x30, x0, -128
    addi x31, x0, 127
    addi x17, x0, 1628
    lui x18, 0x100
    lui x5, 0x80002
    addi x5, x5, -832
    lui x6, 0x80002
    addi x6, x6, -608
    addi x7, x0, 32
fc_quant_14:
    lw x10, 0(x5)
    mul x10,x10,x17
    add x10, x10, x18
    srai x10,x10,1045
    bge x10, x30, clip_low_15
    addi x10, x30, 0
clip_low_15:
    bge x31, x10, clip_high_16
    addi x10, x31, 0
clip_high_16:
    sb x10,0(x6)
    addi x5, x5, 4
    addi x6, x6, 1
    addi x7, x7, -1
    bne x7, x0, fc_quant_14
    lui x31, 0x80002
    addi x31, x31, -64
    addi x30, x0, 2
    sw x30, 0(x31)
    lui x17, 0xc0dec
    addi x17, x17, 222
    jal x0, exit
fail:
    lui x17, 0xdeadc
    addi x17, x17, -273
exit:
    lui x18, 0x80002
    addi x18, x18, -32
    sw x17, 0(x18)
halt:
    jal x0, halt
fc_runtime:
    lw x5, 0(x4)
    lw x6, 4(x4)
    lw x7, 8(x4)
    lw x23, 12(x4)
    lw x9, 16(x4)
    lw x10, 20(x4)
    lui x8, 0x80002
    addi x8, x8, -832
    addi x15, x0, 0
fc_bias:
    slli x18,x15,2
    add x19, x7, x18
    lw x21, 0(x19)
    add x19, x8, x18
    sw x21, 0(x19)
    addi x15, x15, 1
    bltu x15, x9, fc_bias
fc_cpu_segment:
    andi x11, x10, -4
    addi x15, x0, 0
cpu_row:
    mul x18,x15,x10
    add x18, x6, x18
    addi x19, x5, 0
    slli x20,x15,2
    add x20, x8, x20
    lw x21, 0(x20)
    addi x16, x0, 0
    beq x11, x0, cpu_tail
cpu_unroll4:
    lb x17,0(x18)
    lb x22,0(x19)
    mul x17,x17,x22
    add x21, x21, x17
    lb x17,1(x18)
    lb x22,1(x19)
    mul x17,x17,x22
    add x21, x21, x17
    lb x17,2(x18)
    lb x22,2(x19)
    mul x17,x17,x22
    add x21, x21, x17
    lb x17,3(x18)
    lb x22,3(x19)
    mul x17,x17,x22
    add x21, x21, x17
    addi x18, x18, 4
    addi x19, x19, 4
    addi x16, x16, 4
    bltu x16, x11, cpu_unroll4
cpu_tail:
    bgeu x16, x10, cpu_row_done
    lb x17,0(x18)
    lb x22,0(x19)
    mul x17,x17,x22
    add x21, x21, x17
    addi x18, x18, 1
    addi x19, x19, 1
    addi x16, x16, 1
    jal x0, cpu_tail
cpu_row_done:
    sw x21, 0(x20)
    addi x15, x15, 1
    bltu x15, x9, cpu_row
    jalr x0,0(x1)
