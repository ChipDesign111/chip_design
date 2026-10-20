"""Small deterministic RV32I emitter for the real CPU self-check."""
BASE=0x80000000

class Assembler:

    def __init__(self):
        self.words, self.labels, self.fixups, self.listing = ([], {}, [], [])

    def label(self, name):
        self.labels[name] = BASE + 4 * len(self.words)
        self.listing.append(name + ':')

    def emit(self, word, text):
        self.words.append(word & 4294967295)
        self.listing.append('    ' + text)

    def lui(self, rd, value):
        self.emit(value & 4294963200 | rd << 7 | 55, f'lui x{rd}, 0x{value >> 12:x}')

    def addi(self, rd, rs, imm):
        assert -2048 <= imm <= 2047
        self.emit((imm & 4095) << 20 | rs << 15 | rd << 7 | 19, f'addi x{rd}, x{rs}, {imm}')

    def andi(self, rd, rs, imm):
        self.emit((imm & 4095) << 20 | rs << 15 | 7 << 12 | rd << 7 | 19, f'andi x{rd}, x{rs}, {imm}')

    def li(self, rd, value):
        value &= 4294967295
        low = value & 4095
        if low >= 2048:
            low -= 4096
        self.lui(rd, value - low & 4294967295)
        self.addi(rd, rd, low)

    def la(self, rd, name):
        self.fixups.append(('la', len(self.words), rd, name))
        self.li(rd, 0)

    def lw(self, rd, rs, offset=0):
        self.emit((offset & 4095) << 20 | rs << 15 | 2 << 12 | rd << 7 | 3, f'lw x{rd}, {offset}(x{rs})')

    def sw(self, rs2, rs1, offset=0):
        imm = offset & 4095
        self.emit(imm >> 5 << 25 | rs2 << 20 | rs1 << 15 | 2 << 12 | (imm & 31) << 7 | 35, f'sw x{rs2}, {offset}(x{rs1})')

    def add(self, rd, rs1, rs2):
        self.emit(rs2 << 20 | rs1 << 15 | rd << 7 | 51, f'add x{rd}, x{rs1}, x{rs2}')

    def sub(self, rd, rs1, rs2):
        self.emit(32 << 25 | rs2 << 20 | rs1 << 15 | rd << 7 | 51, f'sub x{rd}, x{rs1}, x{rs2}')

    def rdcycle(self, rd):
        self.emit(2816 << 20 | 2 << 12 | rd << 7 | 115, f'csrr x{rd}, mcycle')

    def branch(self, kind, rs1, rs2, label):
        self.fixups.append((kind, len(self.words), rs1, rs2, label))
        self.emit(0, f'{kind} x{rs1}, x{rs2}, {label}')

    def jump(self, label):
        self.fixups.append(('jal', len(self.words), label))
        self.emit(0, f'jal x0, {label}')

    def resolve(self):
        for item in self.fixups:
            kind, idx = item[:2]
            if kind == 'la':
                rd, name = item[2:]
                value = self.labels[name]
                low = value & 4095
                if low >= 2048:
                    low -= 4096
                self.words[idx] = value - low & 4294963200 | rd << 7 | 55
                self.words[idx + 1] = (low & 4095) << 20 | rd << 15 | rd << 7 | 19
                continue
            label = item[-1]
            delta = self.labels[label] - (BASE + idx * 4)
            assert delta % 2 == 0
            if kind == 'jal':
                assert -(1 << 20) <= delta < 1 << 20
                bits = delta & 2097151
                self.words[idx] = bits >> 20 << 31 | (bits >> 1 & 1023) << 21 | (bits >> 11 & 1) << 20 | (bits >> 12 & 255) << 12 | 111
            else:
                assert -4096 <= delta <= 4094
                rs1, rs2 = item[2:4]
                bits = delta & 8191
                self.words[idx] = bits >> 12 << 31 | (bits >> 5 & 63) << 25 | rs2 << 20 | rs1 << 15 | (kind == 'bne') << 12 | (bits >> 1 & 15) << 8 | (bits >> 11 & 1) << 7 | 99
