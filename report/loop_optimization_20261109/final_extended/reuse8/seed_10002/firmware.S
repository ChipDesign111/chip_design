    lui x20, 0x70000
    lui x5, 0x80001
    sw x5, 32(x20)
    lui x5, 0x80002
    addi x5, x5, -2048
    sw x5, 36(x20)
    addi x5, x0, 1064
    sw x5, 16(x20)
    addi x5, x0, 20
    sw x5, 20(x20)
    addi x5, x0, 4
    sw x5, 24(x20)
    lui x5, 0x80002
    addi x5, x5, -1792
    lui x6, 0x70001
    addi x6, x6, -1600
    addi x7, x0, 4
bias1:
    lw x8, 0(x5)
    lw x9, 4(x5)
    lw x10, 8(x5)
    lw x11, 12(x5)
    lw x12, 16(x5)
    lw x13, 20(x5)
    lw x14, 24(x5)
    lw x15, 28(x5)
    sw x8, 0(x6)
    sw x9, 4(x6)
    sw x10, 8(x6)
    sw x11, 12(x6)
    sw x12, 16(x6)
    sw x13, 20(x6)
    sw x14, 24(x6)
    sw x15, 28(x6)
    addi x5, x5, 32
    addi x6, x6, 32
    addi x7, x7, -1
    bne x7, x0, bias1
bias2:
    lw x8, 0(x5)
    lw x9, 4(x5)
    lw x10, 8(x5)
    lw x11, 12(x5)
    lw x12, 16(x5)
    lw x13, 20(x5)
    sw x8, 0(x6)
    sw x9, 4(x6)
    sw x10, 8(x6)
    sw x11, 12(x6)
    sw x12, 16(x6)
    sw x13, 20(x6)
    addi x5, x5, 128
    addi x6, x20, 64
    addi x7, x0, 2
x0:
    lw x8, 0(x5)
    lw x9, 4(x5)
    lw x10, 8(x5)
    lw x11, 12(x5)
    lw x12, 16(x5)
    lw x13, 20(x5)
    lw x14, 24(x5)
    lw x15, 28(x5)
    sw x8, 0(x6)
    sw x9, 4(x6)
    sw x10, 8(x6)
    sw x11, 12(x6)
    sw x12, 16(x6)
    sw x13, 20(x6)
    sw x14, 24(x6)
    sw x15, 28(x6)
    addi x5, x5, 32
    addi x6, x6, 32
    addi x7, x7, -1
    bne x7, x0, x0
    lui x6, 0x70001
    addi x6, x6, -1024
    addi x7, x0, 2
x1:
    lw x8, 0(x5)
    lw x9, 4(x5)
    lw x10, 8(x5)
    lw x11, 12(x5)
    lw x12, 16(x5)
    lw x13, 20(x5)
    lw x14, 24(x5)
    lw x15, 28(x5)
    sw x8, 0(x6)
    sw x9, 4(x6)
    sw x10, 8(x6)
    sw x11, 12(x6)
    sw x12, 16(x6)
    sw x13, 20(x6)
    sw x14, 24(x6)
    sw x15, 28(x6)
    addi x5, x5, 32
    addi x6, x6, 32
    addi x7, x7, -1
    bne x7, x0, x1
    addi x6, x6, 960
    addi x7, x0, 2
x2:
    lw x8, 0(x5)
    lw x9, 4(x5)
    lw x10, 8(x5)
    lw x11, 12(x5)
    lw x12, 16(x5)
    lw x13, 20(x5)
    lw x14, 24(x5)
    lw x15, 28(x5)
    sw x8, 0(x6)
    sw x9, 4(x6)
    sw x10, 8(x6)
    sw x11, 12(x6)
    sw x12, 16(x6)
    sw x13, 20(x6)
    sw x14, 24(x6)
    sw x15, 28(x6)
    addi x5, x5, 32
    addi x6, x6, 32
    addi x7, x7, -1
    bne x7, x0, x2
    addi x7, x0, 2
x3:
    lw x8, 0(x5)
    lw x9, 4(x5)
    lw x10, 8(x5)
    lw x11, 12(x5)
    lw x12, 16(x5)
    lw x13, 20(x5)
    lw x14, 24(x5)
    lw x15, 28(x5)
    sw x8, 0(x6)
    sw x9, 4(x6)
    sw x10, 8(x6)
    sw x11, 12(x6)
    sw x12, 16(x6)
    sw x13, 20(x6)
    sw x14, 24(x6)
    sw x15, 28(x6)
    addi x5, x5, 32
    addi x6, x6, 32
    addi x7, x7, -1
    bne x7, x0, x3
    addi x5, x0, 1
    sw x5, 0(x20)
poll:
    lw x5, 4(x20)
    andi x6, x5, 2
    bne x6, x0, poll
    addi x6, x0, 1
    bne x5, x6, fail
    lui x5, 0x70001
    addi x5, x5, -1408
    lui x6, 0x80002
    addi x6, x6, -1024
hidden0:
    lw x8, 0(x5)
    lw x9, 4(x5)
    lw x10, 8(x5)
    lw x11, 12(x5)
    lw x12, 16(x5)
    lw x13, 20(x5)
    lw x14, 24(x5)
    lw x15, 28(x5)
    lw x24, 0(x6)
    lw x25, 4(x6)
    lw x26, 8(x6)
    lw x27, 12(x6)
    lw x28, 16(x6)
    lw x29, 20(x6)
    lw x30, 24(x6)
    lw x31, 28(x6)
    bne x8, x24, fail
    bne x9, x25, fail
    bne x10, x26, fail
    bne x11, x27, fail
    bne x12, x28, fail
    bne x13, x29, fail
    bne x14, x30, fail
    bne x15, x31, fail
    addi x5, x5, 128
    addi x6, x6, 32
scores0:
    lw x8, 0(x5)
    lw x9, 4(x5)
    lw x10, 8(x5)
    lw x11, 12(x5)
    lw x12, 16(x5)
    lw x13, 20(x5)
    lw x24, 0(x6)
    lw x25, 4(x6)
    lw x26, 8(x6)
    lw x27, 12(x6)
    lw x28, 16(x6)
    lw x29, 20(x6)
    bne x8, x24, fail
    bne x9, x25, fail
    bne x10, x26, fail
    bne x11, x27, fail
    bne x12, x28, fail
    bne x13, x29, fail
    addi x5, x20, 8
    addi x6, x6, 24
class0:
    lw x8, 0(x5)
    lw x24, 0(x6)
    bne x8, x24, fail
    lui x5, 0x70001
    addi x5, x5, -960
    addi x6, x6, 8
hidden1:
    lw x8, 0(x5)
    lw x9, 4(x5)
    lw x10, 8(x5)
    lw x11, 12(x5)
    lw x12, 16(x5)
    lw x13, 20(x5)
    lw x14, 24(x5)
    lw x15, 28(x5)
    lw x24, 0(x6)
    lw x25, 4(x6)
    lw x26, 8(x6)
    lw x27, 12(x6)
    lw x28, 16(x6)
    lw x29, 20(x6)
    lw x30, 24(x6)
    lw x31, 28(x6)
    bne x8, x24, fail
    bne x9, x25, fail
    bne x10, x26, fail
    bne x11, x27, fail
    bne x12, x28, fail
    bne x13, x29, fail
    bne x14, x30, fail
    bne x15, x31, fail
    addi x5, x5, 64
    addi x6, x6, 32
scores1:
    lw x8, 0(x5)
    lw x9, 4(x5)
    lw x10, 8(x5)
    lw x11, 12(x5)
    lw x12, 16(x5)
    lw x13, 20(x5)
    lw x24, 0(x6)
    lw x25, 4(x6)
    lw x26, 8(x6)
    lw x27, 12(x6)
    lw x28, 16(x6)
    lw x29, 20(x6)
    bne x8, x24, fail
    bne x9, x25, fail
    bne x10, x26, fail
    bne x11, x27, fail
    bne x12, x28, fail
    bne x13, x29, fail
    addi x5, x5, 24
    addi x6, x6, 24
class1:
    lw x8, 0(x5)
    lw x24, 0(x6)
    bne x8, x24, fail
    addi x5, x5, 1384
    addi x6, x6, 8
hidden2:
    lw x8, 0(x5)
    lw x9, 4(x5)
    lw x10, 8(x5)
    lw x11, 12(x5)
    lw x12, 16(x5)
    lw x13, 20(x5)
    lw x14, 24(x5)
    lw x15, 28(x5)
    lw x24, 0(x6)
    lw x25, 4(x6)
    lw x26, 8(x6)
    lw x27, 12(x6)
    lw x28, 16(x6)
    lw x29, 20(x6)
    lw x30, 24(x6)
    lw x31, 28(x6)
    bne x8, x24, fail
    bne x9, x25, fail
    bne x10, x26, fail
    bne x11, x27, fail
    bne x12, x28, fail
    bne x13, x29, fail
    bne x14, x30, fail
    bne x15, x31, fail
    addi x5, x5, 32
    addi x6, x6, 32
scores2:
    lw x8, 0(x5)
    lw x9, 4(x5)
    lw x10, 8(x5)
    lw x11, 12(x5)
    lw x12, 16(x5)
    lw x13, 20(x5)
    lw x24, 0(x6)
    lw x25, 4(x6)
    lw x26, 8(x6)
    lw x27, 12(x6)
    lw x28, 16(x6)
    lw x29, 20(x6)
    bne x8, x24, fail
    bne x9, x25, fail
    bne x10, x26, fail
    bne x11, x27, fail
    bne x12, x28, fail
    bne x13, x29, fail
    addi x5, x5, 24
    addi x6, x6, 24
class2:
    lw x8, 0(x5)
    lw x24, 0(x6)
    bne x8, x24, fail
    addi x5, x5, 8
    addi x6, x6, 8
hidden3:
    lw x8, 0(x5)
    lw x9, 4(x5)
    lw x10, 8(x5)
    lw x11, 12(x5)
    lw x12, 16(x5)
    lw x13, 20(x5)
    lw x14, 24(x5)
    lw x15, 28(x5)
    lw x24, 0(x6)
    lw x25, 4(x6)
    lw x26, 8(x6)
    lw x27, 12(x6)
    lw x28, 16(x6)
    lw x29, 20(x6)
    lw x30, 24(x6)
    lw x31, 28(x6)
    bne x8, x24, fail
    bne x9, x25, fail
    bne x10, x26, fail
    bne x11, x27, fail
    bne x12, x28, fail
    bne x13, x29, fail
    bne x14, x30, fail
    bne x15, x31, fail
    addi x5, x5, 32
    addi x6, x6, 32
scores3:
    lw x8, 0(x5)
    lw x9, 4(x5)
    lw x10, 8(x5)
    lw x11, 12(x5)
    lw x12, 16(x5)
    lw x13, 20(x5)
    lw x24, 0(x6)
    lw x25, 4(x6)
    lw x26, 8(x6)
    lw x27, 12(x6)
    lw x28, 16(x6)
    lw x29, 20(x6)
    bne x8, x24, fail
    bne x9, x25, fail
    bne x10, x26, fail
    bne x11, x27, fail
    bne x12, x28, fail
    bne x13, x29, fail
    addi x5, x5, 24
    addi x6, x6, 24
class3:
    lw x8, 0(x5)
    lw x24, 0(x6)
    bne x8, x24, fail
    lw x5, 48(x20)
    addi x6, x0, 64
    bne x5, x6, fail
    lw x5, 40(x20)
    addi x6, x0, 256
    bne x5, x6, fail
    lw x5, 44(x20)
    addi x6, x0, 64
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
