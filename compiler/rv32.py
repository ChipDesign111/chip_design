"""Ordinary RV32IM operations around the existing four-way CPU/RAW emitters."""
from .runtime import RuntimeAssembler


class Program(RuntimeAssembler):
    def __init__(self):
        super().__init__()
        self.serial = 0

    def fresh(self, prefix):
        self.serial += 1
        return '%s_%d' % (prefix, self.serial)

    def branch(self, kind, left, right, label):
        if label == 'fail':
            skip = self.fresh('skip_fail')
            opposite = {'beq': 'bne', 'bne': 'beq', 'blt': 'bge', 'bge': 'blt',
                        'bltu': 'bgeu', 'bgeu': 'bltu'}
            super().branch(opposite[kind], left, right, skip)
            self.jump(label)
            self.label(skip)
        else:
            super().branch(kind, left, right, label)

    def jalr(self, rd, rs):
        self.emit((rs << 15) | (rd << 7) | 0x67, 'jalr x%d,0(x%d)' % (rd, rs))

    def srai(self, rd, rs, shift):
        self.immediate('srai', rd, rs, 0x400 | shift, 5)

    def lhu(self, rd, rs):
        self.emit((rs << 15) | (5 << 12) | (rd << 7) | 3, 'lhu x%d,0(x%d)' % (rd, rs))

    def divu(self, rd, left, right):
        self.register('divu', rd, left, right, 5, 1)
