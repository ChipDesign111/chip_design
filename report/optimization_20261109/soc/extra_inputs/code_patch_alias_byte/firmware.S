    lui x15, 0x0
    addi x15, x15, 0
    lui x19, 0x2
    addi x19, x19, 0
    add x19, x15, x19
    lui x16, 0x0
    addi x16, x16, 0
    jal x0, patch_word
patch_return1:
    lui x18, 0x0
    addi x18, x18, 1
    bne x17, x18, fail
    lui x18, 0x0
    addi x18, x18, 32
    sb x18, 2(x19) # +8KiB SRAM alias
    fence.i
    lui x16, 0x0
    addi x16, x16, 0
    jal x0, patch_word
patch_return2:
    lui x18, 0x0
    addi x18, x18, 2
    bne x17, x18, fail
    lui x18, 0x301
    addi x18, x18, -1901
    sw x18, 0(x15)
    fence.i
    lui x16, 0x0
    addi x16, x16, 0
    jal x0, patch_word
patch_return3:
    lui x18, 0x0
    addi x18, x18, 3
    bne x17, x18, fail
    jal x0, patch_done
patch_word:
    addi x17, x0, 1
    jalr x0, x16, 0
patch_done:
    lui x20, 0x70000
    addi x20, x20, 0
    lui x5, 0x80001
    addi x5, x5, 0
    sw x5, 32(x20)
    lui x5, 0x80002
    addi x5, x5, -2048
    sw x5, 36(x20)
    lui x5, 0x0
    addi x5, x5, 1064
    sw x5, 16(x20)
    lui x5, 0x0
    addi x5, x5, 20
    sw x5, 20(x20)
    lui x5, 0x0
    addi x5, x5, 4
    sw x5, 24(x20)
    lui x5, 0x80002
    addi x5, x5, -1792
    lui x6, 0x70001
    addi x6, x6, -1600
    lui x7, 0x0
    addi x7, x7, 32
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
    lui x7, 0x0
    addi x7, x7, 6
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
    lui x7, 0x0
    addi x7, x7, 16
x0:
    lw x8, 0(x5)
    sw x8, 0(x6)
    addi x5, x5, 4
    addi x6, x6, 4
    addi x7, x7, -1
    bne x7, x0, x0
    lui x5, 0x80002
    addi x5, x5, -1472
    lui x6, 0x70001
    addi x6, x6, -1024
    lui x7, 0x0
    addi x7, x7, 16
x1:
    lw x8, 0(x5)
    sw x8, 0(x6)
    addi x5, x5, 4
    addi x6, x6, 4
    addi x7, x7, -1
    bne x7, x0, x1
    lui x5, 0x80002
    addi x5, x5, -1408
    lui x6, 0x70001
    addi x6, x6, 0
    lui x7, 0x0
    addi x7, x7, 16
x2:
    lw x8, 0(x5)
    sw x8, 0(x6)
    addi x5, x5, 4
    addi x6, x6, 4
    addi x7, x7, -1
    bne x7, x0, x2
    lui x5, 0x80002
    addi x5, x5, -1344
    lui x6, 0x70001
    addi x6, x6, 64
    lui x7, 0x0
    addi x7, x7, 16
x3:
    lw x8, 0(x5)
    sw x8, 0(x6)
    addi x5, x5, 4
    addi x6, x6, 4
    addi x7, x7, -1
    bne x7, x0, x3
    lui x5, 0x0
    addi x5, x5, 1
    sw x5, 0(x20)
poll:
    lw x5, 4(x20)
    andi x6, x5, 2
    bne x6, x0, poll
    lui x6, 0x0
    addi x6, x6, 1
    bne x5, x6, fail
    lui x5, 0x70001
    addi x5, x5, -1408
    lui x6, 0x80002
    addi x6, x6, -1024
    lui x7, 0x0
    addi x7, x7, 8
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
    lui x7, 0x0
    addi x7, x7, 6
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
    lui x7, 0x0
    addi x7, x7, 1
class0:
    lw x8, 0(x5)
    lw x9, 0(x6)
    bne x8, x9, fail
    addi x5, x5, 4
    addi x6, x6, 4
    addi x7, x7, -1
    bne x7, x0, class0
    lui x5, 0x70001
    addi x5, x5, -960
    lui x6, 0x80002
    addi x6, x6, -960
    lui x7, 0x0
    addi x7, x7, 8
hidden1:
    lw x8, 0(x5)
    lw x9, 0(x6)
    bne x8, x9, fail
    addi x5, x5, 4
    addi x6, x6, 4
    addi x7, x7, -1
    bne x7, x0, hidden1
    lui x5, 0x70001
    addi x5, x5, -896
    lui x6, 0x80002
    addi x6, x6, -928
    lui x7, 0x0
    addi x7, x7, 6
scores1:
    lw x8, 0(x5)
    lw x9, 0(x6)
    bne x8, x9, fail
    addi x5, x5, 4
    addi x6, x6, 4
    addi x7, x7, -1
    bne x7, x0, scores1
    lui x5, 0x70001
    addi x5, x5, -872
    lui x6, 0x80002
    addi x6, x6, -904
    lui x7, 0x0
    addi x7, x7, 1
class1:
    lw x8, 0(x5)
    lw x9, 0(x6)
    bne x8, x9, fail
    addi x5, x5, 4
    addi x6, x6, 4
    addi x7, x7, -1
    bne x7, x0, class1
    lui x5, 0x70001
    addi x5, x5, 512
    lui x6, 0x80002
    addi x6, x6, -896
    lui x7, 0x0
    addi x7, x7, 8
hidden2:
    lw x8, 0(x5)
    lw x9, 0(x6)
    bne x8, x9, fail
    addi x5, x5, 4
    addi x6, x6, 4
    addi x7, x7, -1
    bne x7, x0, hidden2
    lui x5, 0x70001
    addi x5, x5, 544
    lui x6, 0x80002
    addi x6, x6, -864
    lui x7, 0x0
    addi x7, x7, 6
scores2:
    lw x8, 0(x5)
    lw x9, 0(x6)
    bne x8, x9, fail
    addi x5, x5, 4
    addi x6, x6, 4
    addi x7, x7, -1
    bne x7, x0, scores2
    lui x5, 0x70001
    addi x5, x5, 568
    lui x6, 0x80002
    addi x6, x6, -840
    lui x7, 0x0
    addi x7, x7, 1
class2:
    lw x8, 0(x5)
    lw x9, 0(x6)
    bne x8, x9, fail
    addi x5, x5, 4
    addi x6, x6, 4
    addi x7, x7, -1
    bne x7, x0, class2
    lui x5, 0x70001
    addi x5, x5, 576
    lui x6, 0x80002
    addi x6, x6, -832
    lui x7, 0x0
    addi x7, x7, 8
hidden3:
    lw x8, 0(x5)
    lw x9, 0(x6)
    bne x8, x9, fail
    addi x5, x5, 4
    addi x6, x6, 4
    addi x7, x7, -1
    bne x7, x0, hidden3
    lui x5, 0x70001
    addi x5, x5, 608
    lui x6, 0x80002
    addi x6, x6, -800
    lui x7, 0x0
    addi x7, x7, 6
scores3:
    lw x8, 0(x5)
    lw x9, 0(x6)
    bne x8, x9, fail
    addi x5, x5, 4
    addi x6, x6, 4
    addi x7, x7, -1
    bne x7, x0, scores3
    lui x5, 0x70001
    addi x5, x5, 632
    lui x6, 0x80002
    addi x6, x6, -776
    lui x7, 0x0
    addi x7, x7, 1
class3:
    lw x8, 0(x5)
    lw x9, 0(x6)
    bne x8, x9, fail
    addi x5, x5, 4
    addi x6, x6, 4
    addi x7, x7, -1
    bne x7, x0, class3
    lw x5, 48(x20)
    lui x6, 0x0
    addi x6, x6, 64
    bne x5, x6, fail
    lw x5, 40(x20)
    lui x6, 0x0
    addi x6, x6, 256
    bne x5, x6, fail
    lw x5, 44(x20)
    lui x6, 0x0
    addi x6, x6, 64
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
