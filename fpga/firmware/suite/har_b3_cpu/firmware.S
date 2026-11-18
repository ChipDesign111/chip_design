    lui x31, 0x80002
    addi x31, x31, -64
    addi x30, x0, 1
    sw x30, 0(x31)
    lui x4, 0x80001
    addi x4, x4, -2048
    lui x1, 0x0
    addi x1, x1, 0
    jal x0, cpu_layer
layer_return_1:
    lui x4, 0x80001
    addi x4, x4, -2012
    lui x1, 0x0
    addi x1, x1, 0
    jal x0, cpu_layer
layer_return_2:
    lui x5, 0x80002
    addi x5, x5, -736
    lw x19, 0(x5)
    addi x7, x0, 1
    addi x21, x0, 0
argmax_3:
    lw x20, 4(x5)
    bge x19, x20, keep_class_4
    addi x19, x20, 0
    addi x21, x7, 0
keep_class_4:
    addi x5, x5, 4
    addi x7, x7, 1
    addi x17, x0, 6
    bltu x7, x17, argmax_3
    lui x18, 0x80002
    addi x18, x18, -712
    sw x21, 0(x18)
    lui x4, 0x80001
    addi x4, x4, -1976
    lui x1, 0x0
    addi x1, x1, 0
    jal x0, cpu_layer
layer_return_5:
    lui x4, 0x80001
    addi x4, x4, -1940
    lui x1, 0x0
    addi x1, x1, 0
    jal x0, cpu_layer
layer_return_6:
    lui x5, 0x80002
    addi x5, x5, -672
    lw x19, 0(x5)
    addi x7, x0, 1
    addi x21, x0, 0
argmax_7:
    lw x20, 4(x5)
    bge x19, x20, keep_class_8
    addi x19, x20, 0
    addi x21, x7, 0
keep_class_8:
    addi x5, x5, 4
    addi x7, x7, 1
    addi x17, x0, 6
    bltu x7, x17, argmax_7
    lui x18, 0x80002
    addi x18, x18, -648
    sw x21, 0(x18)
    lui x4, 0x80001
    addi x4, x4, -1904
    lui x1, 0x0
    addi x1, x1, 0
    jal x0, cpu_layer
layer_return_9:
    lui x4, 0x80001
    addi x4, x4, -1868
    lui x1, 0x0
    addi x1, x1, 0
    jal x0, cpu_layer
layer_return_10:
    lui x5, 0x80002
    addi x5, x5, -608
    lw x19, 0(x5)
    addi x7, x0, 1
    addi x21, x0, 0
argmax_11:
    lw x20, 4(x5)
    bge x19, x20, keep_class_12
    addi x19, x20, 0
    addi x21, x7, 0
keep_class_12:
    addi x5, x5, 4
    addi x7, x7, 1
    addi x17, x0, 6
    bltu x7, x17, argmax_11
    lui x18, 0x80002
    addi x18, x18, -584
    sw x21, 0(x18)
    lui x31, 0x80002
    addi x31, x31, -64
    addi x30, x0, 2
    sw x30, 0(x31)
    lui x5, 0x80002
    addi x5, x5, -768
    lui x6, 0x80002
    addi x6, x6, -1024
    addi x7, x0, 15
verify_13:
    lw x8, 0(x5)
    lw x9, 0(x6)
    beq x8, x9, skip_fail_14
    jal x0, fail
skip_fail_14:
    addi x5, x5, 4
    addi x6, x6, 4
    addi x7, x7, -1
    bne x7, x0, verify_13
    lui x5, 0x80002
    addi x5, x5, -704
    lui x6, 0x80002
    addi x6, x6, -960
    addi x7, x0, 15
verify_15:
    lw x8, 0(x5)
    lw x9, 0(x6)
    beq x8, x9, skip_fail_16
    jal x0, fail
skip_fail_16:
    addi x5, x5, 4
    addi x6, x6, 4
    addi x7, x7, -1
    bne x7, x0, verify_15
    lui x5, 0x80002
    addi x5, x5, -640
    lui x6, 0x80002
    addi x6, x6, -896
    addi x7, x0, 15
verify_17:
    lw x8, 0(x5)
    lw x9, 0(x6)
    beq x8, x9, skip_fail_18
    jal x0, fail
skip_fail_18:
    addi x5, x5, 4
    addi x6, x6, 4
    addi x7, x7, -1
    bne x7, x0, verify_17
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
cpu_layer:
    lw x5, 0(x4)
    lw x6, 4(x4)
    lw x7, 8(x4)
    lw x23, 12(x4)
    lw x9, 16(x4)
    lw x10, 20(x4)
    lw x24, 24(x4)
    lw x25, 28(x4)
    lw x26, 32(x4)
    lui x8, 0x80001
    addi x8, x8, -1536
    addi x15, x0, 0
bias:
    slli x18,x15,2
    add x19, x7, x18
    lw x21, 0(x19)
    add x19, x8, x18
    sw x21, 0(x19)
    addi x15, x15, 1
    bltu x15, x9, bias
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
    addi x15, x0, 0
wrap22:
    slli x20,x15,2
    add x20, x8, x20
    lw x21, 0(x20)
    slli x21,x21,10
    srai x21,x21,1034
    sw x21, 0(x20)
    addi x15, x15, 1
    bltu x15, x9, wrap22
bench_postprocess:
    addi x15, x0, 0
finish_output:
    slli x20,x15,2
    add x20, x20, x8
    lw x21, 0(x20)
    beq x26, x0, store_score
    blt x21, x0, quant_zero
    mul x17,x21,x24
    mulhu x18,x21,x24
    beq x25, x0, quant_shifted
    addi x19, x25, -1
    addi x20, x0, 1
    sll x20,x20,x19
    add x19, x17, x20
    sltu x20,x19,x17
    add x18, x18, x20
    addi x17, x19, 0
    srl x17,x17,x25
    addi x19, x0, 32
    sub x19, x19, x25
    sll x20,x18,x19
    or x17,x17,x20
    srl x18,x18,x25
quant_shifted:
    bne x18, x0, quant_saturate
    addi x19, x0, 128
    bgeu x17, x19, quant_saturate
    addi x21, x17, 0
    jal x0, store_hidden
quant_saturate:
    addi x21, x0, 127
    jal x0, store_hidden
quant_zero:
    addi x21, x0, 0
store_hidden:
    add x20, x23, x15
    sb x21,0(x20)
    jal x0, output_next
store_score:
    slli x20,x15,2
    add x18, x23, x20
    sw x21, 0(x18)
output_next:
    addi x15, x15, 1
    bltu x15, x9, finish_output
    jalr x0,0(x1)
