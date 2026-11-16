BASE=0x80000000

class Assembler:
    def __init__(self):
        self.words, self.labels, self.fixups, self.listing = [], {}, [], []
        self.compact_li = False
    def label(self, name):
        self.labels[name] = BASE + 4 * len(self.words)
        self.listing.append(name + ":")
    def emit(self, word, text):
        self.words.append(word & 0xffffffff)
        self.listing.append("    " + text)
    def lui(self, rd, value):
        self.emit((value & 0xfffff000) | (rd << 7) | 0x37, f"lui x{rd}, 0x{value >> 12:x}")
    def addi(self, rd, rs, imm):
        assert -2048 <= imm <= 2047
        self.emit(((imm & 4095) << 20) | (rs << 15) | (rd << 7) | 0x13, f"addi x{rd}, x{rs}, {imm}")
    def andi(self, rd, rs, imm):
        self.emit(((imm & 4095) << 20) | (rs << 15) | (7 << 12) | (rd << 7) | 0x13, f"andi x{rd}, x{rs}, {imm}")
    def li(self, rd, value):
        value &= 0xffffffff
        signed = value if value < 0x80000000 else value - 0x100000000
        if self.compact_li and -2048 <= signed <= 2047:
            self.addi(rd, 0, signed)
            return
        low = value & 4095
        if low >= 2048:
            low -= 4096
        self.lui(rd, (value - low) & 0xffffffff)
        if not self.compact_li or low:
            self.addi(rd, rd, low)
    def la(self, rd, name):
        self.fixups.append(("la", len(self.words), rd, name))
        # Address fixups always own two slots, including with compact constants.
        self.lui(rd, 0)
        self.addi(rd, rd, 0)
    def lw(self, rd, rs, offset=0):
        self.emit(((offset & 4095) << 20) | (rs << 15) | (2 << 12) | (rd << 7) | 3, f"lw x{rd}, {offset}(x{rs})")
    def sw(self, rs2, rs1, offset=0):
        imm = offset & 4095
        self.emit(((imm >> 5) << 25) | (rs2 << 20) | (rs1 << 15) | (2 << 12) | ((imm & 31) << 7) | 0x23, f"sw x{rs2}, {offset}(x{rs1})")
    def add(self, rd, rs1, rs2):
        self.emit((rs2 << 20) | (rs1 << 15) | (rd << 7) | 0x33, f"add x{rd}, x{rs1}, x{rs2}")
    def sub(self, rd, rs1, rs2):
        self.emit((0x20 << 25) | (rs2 << 20) | (rs1 << 15) | (rd << 7) | 0x33, f"sub x{rd}, x{rs1}, x{rs2}")
    def rdcycle(self, rd):
        self.emit((0xb00 << 20) | (2 << 12) | (rd << 7) | 0x73, f"csrr x{rd}, mcycle")
    def branch(self, kind, rs1, rs2, label):
        self.fixups.append((kind, len(self.words), rs1, rs2, label))
        self.emit(0, f"{kind} x{rs1}, x{rs2}, {label}")
    def jump(self, label):
        self.fixups.append(("jal", len(self.words), label))
        self.emit(0, f"jal x0, {label}")
    def resolve(self):
        for item in self.fixups:
            kind, idx = item[:2]
            if kind == "la":
                rd, name = item[2:]
                value = self.labels[name]
                low = value & 4095
                if low >= 2048:
                    low -= 4096
                self.words[idx] = ((value-low) & 0xfffff000) | (rd << 7) | 0x37
                self.words[idx+1] = ((low & 4095) << 20) | (rd << 15) | (rd << 7) | 0x13
                continue
            label = item[-1]
            delta = self.labels[label] - (BASE + idx * 4)
            assert delta % 2 == 0
            if kind == "jal":
                assert -(1 << 20) <= delta < (1 << 20)
                bits = delta & 0x1fffff
                self.words[idx] = ((bits >> 20) << 31) | (((bits >> 1) & 1023) << 21) | (((bits >> 11) & 1) << 20) | (((bits >> 12) & 255) << 12) | 0x6f
            else:
                assert -4096 <= delta <= 4094
                rs1, rs2 = item[2:4]
                bits = delta & 8191
                self.words[idx] = ((bits >> 12) << 31) | (((bits >> 5) & 63) << 25) | (rs2 << 20) | (rs1 << 15) | ((kind == "bne") << 12) | (((bits >> 1) & 15) << 8) | (((bits >> 11) & 1) << 7) | 0x63



class Program(Assembler):
    """Additional RV32IM operations used by generated CPU fallback kernels."""
    def __init__(self):
        super().__init__();self.compact_li=True;self.serial=0
    def fresh(self,prefix):
        self.serial+=1;return f"{prefix}_{self.serial}"
    def lw(self,rd,rs,offset=0):
        assert -2048<=offset<=2047
        super().lw(rd,rs,offset)
    def sw(self,rs2,rs1,offset=0):
        assert -2048<=offset<=2047
        super().sw(rs2,rs1,offset)
    def branch(self,kind,rs1,rs2,label):
        # Error handlers may be beyond the signed 12-bit branch range.
        if label=='fail':
            skip=self.fresh('skip_fail')
            super().branch({'beq':'bne','bne':'beq','blt':'bge','bge':'blt'}[kind],rs1,rs2,skip)
            self.jump(label);self.label(skip)
        else:super().branch(kind,rs1,rs2,label)
    def lb(self,rd,rs,offset=0):
        assert -2048<=offset<=2047
        self.emit(((offset&4095)<<20)|(rs<<15)|(rd<<7)|3,f"lb x{rd}, {offset}(x{rs})")
    def sb(self,rs2,rs1,offset=0):
        assert -2048<=offset<=2047
        v=offset&4095
        self.emit(((v>>5)<<25)|(rs2<<20)|(rs1<<15)|((v&31)<<7)|0x23,f"sb x{rs2}, {offset}(x{rs1})")
    def mul(self,rd,rs1,rs2):
        self.emit((1<<25)|(rs2<<20)|(rs1<<15)|(rd<<7)|0x33,f"mul x{rd}, x{rs1}, x{rs2}")
    def lhu(self,rd,rs,offset=0):
        self.emit(((offset&4095)<<20)|(rs<<15)|(5<<12)|(rd<<7)|3,f"lhu x{rd}, {offset}(x{rs})")
    def slli(self,rd,rs,shift):
        self.emit((shift<<20)|(rs<<15)|(1<<12)|(rd<<7)|0x13,f"slli x{rd}, x{rs}, {shift}")
    def divu(self,rd,rs1,rs2):
        self.emit((1<<25)|(rs2<<20)|(rs1<<15)|(5<<12)|(rd<<7)|0x33,f"divu x{rd}, x{rs1}, x{rs2}")
    def srai(self,rd,rs,shift):
        assert 0<=shift<32
        self.emit((0x400|shift)<<20|(rs<<15)|(5<<12)|(rd<<7)|0x13,f"srai x{rd}, x{rs}, {shift}")
    def resolve(self):
        super().resolve()
        for kind,idx,*_ in self.fixups:
            if kind in ('blt','bge'):
                self.words[idx]=(self.words[idx]&~(7<<12))|({'blt':4,'bge':5}[kind]<<12)
