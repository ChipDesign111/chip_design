    addi x30, x0, -128
    addi x31, x0, 127
    lui x6, 0x70001
    addi x6, x6, 1552
    lw x8, 0(x6)
    srai x8, x8, 24
    addi x9, x0, 1
    beq x8, x9, skip_fail_1
    jal x0, fail
skip_fail_1:
    addi x5, x0, 2
    lui x6, 0x70001
    addi x6, x6, 1536
    sw x5, 0(x6)
    lui x5, 0x80002
    addi x5, x5, -1920
    lui x6, 0x70001
    addi x6, x6, 1544
    sw x5, 0(x6)
    addi x5, x0, 2
    lui x6, 0x70001
    addi x6, x6, 1548
    sw x5, 0(x6)
    fence iorw, iorw
    addi x5, x0, 1
    lui x6, 0x70001
    addi x6, x6, 1536
    sw x5, 0(x6)
    lui x6, 0x70001
    addi x6, x6, 1540
    lui x7, 0x31
    addi x7, x7, -704
wait_segment_2:
    lw x8, 0(x6)
    addi x9, x0, 9
    beq x8, x9, segment_done_3
    andi x9, x8, 20
    beq x9, x0, skip_fail_4
    jal x0, fail
skip_fail_4:
    addi x7, x7, -1
    bne x7, x0, wait_segment_2
    jal x0, fail
segment_done_3:
    fence iorw, iorw
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
