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
    addi x7, x0, 16
bias1:
    lw x8, 0(x5)
    sw x8, 0(x6)
    lw x8, 4(x5)
    sw x8, 4(x6)
    addi x5, x5, 8
    addi x6, x6, 8
    addi x7, x7, -1
    bne x7, x0, bias1
    lui x5, 0x80002
    addi x5, x5, -1664
    lui x6, 0x70001
    addi x6, x6, -1472
    addi x7, x0, 3
bias2:
    lw x8, 0(x5)
    sw x8, 0(x6)
    lw x8, 4(x5)
    sw x8, 4(x6)
    addi x5, x5, 8
    addi x6, x6, 8
    addi x7, x7, -1
    bne x7, x0, bias2
    lui x5, 0x80002
    addi x5, x5, -1536
    lui x6, 0x70000
    addi x6, x6, 64
    addi x7, x0, 8
x0:
    lw x8, 0(x5)
    sw x8, 0(x6)
    lw x8, 4(x5)
    sw x8, 4(x6)
    addi x5, x5, 8
    addi x6, x6, 8
    addi x7, x7, -1
    bne x7, x0, x0
    lui x5, 0x80002
    addi x5, x5, -1472
    lui x6, 0x70001
    addi x6, x6, -1024
    addi x7, x0, 8
x1:
    lw x8, 0(x5)
    sw x8, 0(x6)
    lw x8, 4(x5)
    sw x8, 4(x6)
    addi x5, x5, 8
    addi x6, x6, 8
    addi x7, x7, -1
    bne x7, x0, x1
    lui x5, 0x80002
    addi x5, x5, -1408
    lui x6, 0x70001
    addi x7, x0, 8
x2:
    lw x8, 0(x5)
    sw x8, 0(x6)
    lw x8, 4(x5)
    sw x8, 4(x6)
    addi x5, x5, 8
    addi x6, x6, 8
    addi x7, x7, -1
    bne x7, x0, x2
    lui x5, 0x80002
    addi x5, x5, -1344
    lui x6, 0x70001
    addi x6, x6, 64
    addi x7, x0, 8
x3:
    lw x8, 0(x5)
    sw x8, 0(x6)
    lw x8, 4(x5)
    sw x8, 4(x6)
    addi x5, x5, 8
    addi x6, x6, 8
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
    addi x7, x0, 4
hidden0:
    lw x8, 0(x5)
    lw x9, 0(x6)
    bne x8, x9, fail
    lw x8, 4(x5)
    lw x9, 4(x6)
    bne x8, x9, fail
    addi x5, x5, 8
    addi x6, x6, 8
    addi x7, x7, -1
    bne x7, x0, hidden0
    lui x5, 0x70001
    addi x5, x5, -1280
    lui x6, 0x80002
    addi x6, x6, -992
    addi x7, x0, 3
scores0:
    lw x8, 0(x5)
    lw x9, 0(x6)
    bne x8, x9, fail
    lw x8, 4(x5)
    lw x9, 4(x6)
    bne x8, x9, fail
    addi x5, x5, 8
    addi x6, x6, 8
    addi x7, x7, -1
    bne x7, x0, scores0
    lui x5, 0x70000
    addi x5, x5, 8
    lui x6, 0x80002
    addi x6, x6, -968
class0:
    lw x8, 0(x5)
    lw x9, 0(x6)
    bne x8, x9, fail
    lui x5, 0x70001
    addi x5, x5, -960
    lui x6, 0x80002
    addi x6, x6, -960
    addi x7, x0, 4
hidden1:
    lw x8, 0(x5)
    lw x9, 0(x6)
    bne x8, x9, fail
    lw x8, 4(x5)
    lw x9, 4(x6)
    bne x8, x9, fail
    addi x5, x5, 8
    addi x6, x6, 8
    addi x7, x7, -1
    bne x7, x0, hidden1
    lui x5, 0x70001
    addi x5, x5, -896
    lui x6, 0x80002
    addi x6, x6, -928
    addi x7, x0, 3
scores1:
    lw x8, 0(x5)
    lw x9, 0(x6)
    bne x8, x9, fail
    lw x8, 4(x5)
    lw x9, 4(x6)
    bne x8, x9, fail
    addi x5, x5, 8
    addi x6, x6, 8
    addi x7, x7, -1
    bne x7, x0, scores1
    lui x5, 0x70001
    addi x5, x5, -872
    lui x6, 0x80002
    addi x6, x6, -904
class1:
    lw x8, 0(x5)
    lw x9, 0(x6)
    bne x8, x9, fail
    lui x5, 0x70001
    addi x5, x5, 512
    lui x6, 0x80002
    addi x6, x6, -896
    addi x7, x0, 4
hidden2:
    lw x8, 0(x5)
    lw x9, 0(x6)
    bne x8, x9, fail
    lw x8, 4(x5)
    lw x9, 4(x6)
    bne x8, x9, fail
    addi x5, x5, 8
    addi x6, x6, 8
    addi x7, x7, -1
    bne x7, x0, hidden2
    lui x5, 0x70001
    addi x5, x5, 544
    lui x6, 0x80002
    addi x6, x6, -864
    addi x7, x0, 3
scores2:
    lw x8, 0(x5)
    lw x9, 0(x6)
    bne x8, x9, fail
    lw x8, 4(x5)
    lw x9, 4(x6)
    bne x8, x9, fail
    addi x5, x5, 8
    addi x6, x6, 8
    addi x7, x7, -1
    bne x7, x0, scores2
    lui x5, 0x70001
    addi x5, x5, 568
    lui x6, 0x80002
    addi x6, x6, -840
class2:
    lw x8, 0(x5)
    lw x9, 0(x6)
    bne x8, x9, fail
    lui x5, 0x70001
    addi x5, x5, 576
    lui x6, 0x80002
    addi x6, x6, -832
    addi x7, x0, 4
hidden3:
    lw x8, 0(x5)
    lw x9, 0(x6)
    bne x8, x9, fail
    lw x8, 4(x5)
    lw x9, 4(x6)
    bne x8, x9, fail
    addi x5, x5, 8
    addi x6, x6, 8
    addi x7, x7, -1
    bne x7, x0, hidden3
    lui x5, 0x70001
    addi x5, x5, 608
    lui x6, 0x80002
    addi x6, x6, -800
    addi x7, x0, 3
scores3:
    lw x8, 0(x5)
    lw x9, 0(x6)
    bne x8, x9, fail
    lw x8, 4(x5)
    lw x9, 4(x6)
    bne x8, x9, fail
    addi x5, x5, 8
    addi x6, x6, 8
    addi x7, x7, -1
    bne x7, x0, scores3
    lui x5, 0x70001
    addi x5, x5, 632
    lui x6, 0x80002
    addi x6, x6, -776
class3:
    lw x8, 0(x5)
    lw x9, 0(x6)
    bne x8, x9, fail
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
