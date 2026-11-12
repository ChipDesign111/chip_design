    lui x20, 0x70000
    lui x5, 0x80001
    sw x5, 32(x20)
    lui x5, 0x80002
    addi x5, x5, -2048
    sw x5, 36(x20)
    addi x5, x0, 123
    sw x5, 16(x20)
    addi x5, x0, 14
    sw x5, 20(x20)
    addi x5, x0, 1
    sw x5, 24(x20)
    lui x5, 0x80002
    addi x5, x5, -1792
    lui x6, 0x70001
    addi x6, x6, -1600
    addi x7, x0, 8
bias1:
    lw x8, 0(x5)
    lw x9, 4(x5)
    lw x10, 8(x5)
    lw x11, 12(x5)
    sw x8, 0(x6)
    sw x9, 4(x6)
    sw x10, 8(x6)
    sw x11, 12(x6)
    addi x5, x5, 16
    addi x6, x6, 16
    addi x7, x7, -1
    bne x7, x0, bias1
    lui x5, 0x80002
    addi x5, x5, -1664
    lui x6, 0x70001
    addi x6, x6, -1472
bias2:
    lw x8, 0(x5)
    lw x9, 4(x5)
    lw x10, 8(x5)
    lw x11, 12(x5)
    sw x8, 0(x6)
    sw x9, 4(x6)
    sw x10, 8(x6)
    sw x11, 12(x6)
    lw x8, 16(x5)
    lw x9, 20(x5)
    sw x8, 16(x6)
    sw x9, 20(x6)
    lui x5, 0x80002
    addi x5, x5, -1536
    lui x6, 0x70000
    addi x6, x6, 64
    addi x7, x0, 4
x0:
    lw x8, 0(x5)
    lw x9, 4(x5)
    lw x10, 8(x5)
    lw x11, 12(x5)
    sw x8, 0(x6)
    sw x9, 4(x6)
    sw x10, 8(x6)
    sw x11, 12(x6)
    addi x5, x5, 16
    addi x6, x6, 16
    addi x7, x7, -1
    bne x7, x0, x0
    addi x5, x0, 1
    sw x5, 0(x20)
poll:
    lw x5, 4(x20)
    addi x0, x0, 0
    addi x0, x0, 0
    addi x0, x0, 0
    addi x0, x0, 0
    andi x6, x5, 2
    bne x6, x0, poll
    addi x6, x0, 1
    bne x5, x6, fail
    lui x5, 0x70001
    addi x5, x5, -1408
    lui x6, 0x80002
    addi x6, x6, -1024
    addi x7, x0, 2
hidden0:
    lw x8, 0(x5)
    lw x9, 4(x5)
    lw x10, 8(x5)
    lw x11, 12(x5)
    lw x12, 0(x6)
    lw x13, 4(x6)
    lw x14, 8(x6)
    lw x15, 12(x6)
    bne x8, x12, fail
    bne x9, x13, fail
    bne x10, x14, fail
    bne x11, x15, fail
    addi x5, x5, 16
    addi x6, x6, 16
    addi x7, x7, -1
    bne x7, x0, hidden0
    lui x5, 0x70001
    addi x5, x5, -1280
    lui x6, 0x80002
    addi x6, x6, -992
scores0:
    lw x8, 0(x5)
    lw x9, 4(x5)
    lw x10, 8(x5)
    lw x11, 12(x5)
    lw x12, 0(x6)
    lw x13, 4(x6)
    lw x14, 8(x6)
    lw x15, 12(x6)
    bne x8, x12, fail
    bne x9, x13, fail
    bne x10, x14, fail
    bne x11, x15, fail
    lw x8, 16(x5)
    lw x9, 20(x5)
    lw x12, 16(x6)
    lw x13, 20(x6)
    bne x8, x12, fail
    bne x9, x13, fail
    lui x5, 0x70000
    addi x5, x5, 8
    lui x6, 0x80002
    addi x6, x6, -968
class0:
    lw x8, 0(x5)
    lw x12, 0(x6)
    bne x8, x12, fail
    lw x5, 48(x20)
    addi x6, x0, 64
    bne x5, x6, fail
    lw x5, 40(x20)
    addi x6, x0, 64
    bne x5, x6, fail
    lw x5, 44(x20)
    addi x6, x0, 16
    bne x5, x6, fail
    lui x6, 0x80002
    addi x6, x6, -64
    lw x5, 12(x20)
    sw x5, 0(x6)
    lw x5, 28(x20)
    sw x5, 4(x6)
    lw x5, 52(x20)
    sw x5, 8(x6)
    lw x5, 56(x20)
    sw x5, 12(x6)
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
