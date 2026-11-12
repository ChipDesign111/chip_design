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
    addi x7, x0, 32
bias1:
    lw x8, 0(x5)
    sw x8, 0(x6)
    addi x5, x5, 4
    addi x6, x6, 4
    addi x7, x7, -1
    bne x7, x0, bias1
    lui x5, 0x80002
    addi x5, x5, -1664
    lui x6, 0x70001
    addi x6, x6, -1472
    addi x7, x0, 6
bias2:
    lw x8, 0(x5)
    sw x8, 0(x6)
    addi x5, x5, 4
    addi x6, x6, 4
    addi x7, x7, -1
    bne x7, x0, bias2
    lui x5, 0x80002
    addi x5, x5, -1536
    lui x6, 0x70000
    addi x6, x6, 64
    addi x7, x0, 16
x0:
    lw x8, 0(x5)
    sw x8, 0(x6)
    addi x5, x5, 4
    addi x6, x6, 4
    addi x7, x7, -1
    bne x7, x0, x0
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
    addi x7, x0, 8
hidden0:
    lw x8, 0(x5)
    lw x9, 0(x6)
    bne x8, x9, fail
    addi x5, x5, 4
    addi x6, x6, 4
    addi x7, x7, -1
    bne x7, x0, hidden0
    lui x5, 0x70001
    addi x5, x5, -1280
    lui x6, 0x80002
    addi x6, x6, -992
    addi x7, x0, 6
scores0:
    lw x8, 0(x5)
    lw x9, 0(x6)
    bne x8, x9, fail
    addi x5, x5, 4
    addi x6, x6, 4
    addi x7, x7, -1
    bne x7, x0, scores0
    lui x5, 0x70000
    addi x5, x5, 8
    lui x6, 0x80002
    addi x6, x6, -968
    addi x7, x0, 1
class0:
    lw x8, 0(x5)
    lw x9, 0(x6)
    bne x8, x9, fail
    addi x5, x5, 4
    addi x6, x6, 4
    addi x7, x7, -1
    bne x7, x0, class0
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
