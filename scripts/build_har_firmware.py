"""Build deterministic RV32I self-check firmware without a cross compiler.
The emitted instructions execute on the imported CV32E40P. Test weights are
synthetic verification fixtures, not a trained activity recognition model.
"""
import argparse
import hashlib
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from model.reference.mlp_int import infer

BASE = 0x80000000

class Assembler:
    def __init__(self):
        self.words, self.labels, self.fixups, self.listing = [], {}, [], []
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
        low = value & 4095
        if low >= 2048:
            low -= 4096
        self.lui(rd, (value - low) & 0xffffffff)
        self.addi(rd, rd, low)
    def la(self, rd, name):
        self.fixups.append(("la", len(self.words), rd, name))
        self.li(rd, 0)
    def lw(self, rd, rs, offset=0):
        self.emit(((offset & 4095) << 20) | (rs << 15) | (2 << 12) | (rd << 7) | 3, f"lw x{rd}, {offset}(x{rs})")
    def sw(self, rs2, rs1, offset=0):
        imm = offset & 4095
        self.emit(((imm >> 5) << 25) | (rs2 << 20) | (rs1 << 15) | (2 << 12) | ((imm & 31) << 7) | 0x23, f"sw x{rs2}, {offset}(x{rs1})")
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

def pack(values):
    assert len(values) % 4 == 0
    return [sum((v & 255) << (8*j) for j,v in enumerate(values[i:i+4])) for i in range(0,len(values),4)]

def build(out):
    rng = random.Random(20261008)
    w1 = [[rng.randint(-3,3) for _ in range(64)] for _ in range(32)]
    w2 = [[rng.randint(-3,3) for _ in range(32)] for _ in range(6)]
    cases = []
    for idx in range(6):
        x = [rng.randint(-128,127) for _ in range(64)]
        x[0:2] = [-128,127]
        b1 = [rng.randint(-200,200) for _ in range(32)]
        b2 = [-1000]*6
        b2[idx] = 20000
        mult, shift = [1,3,255,65535,1,0][idx], [0,7,15,31,1,0][idx]
        hidden, scores, category = infer(x,w1,w2,b1,b2,mult,shift)
        assert category == idx
        cases.append(dict(x=x,b1=b1,b2=b2,mult=mult,shift=shift,hidden=hidden,scores=scores,category=category))
    a = Assembler()
    a.label("_start")
    a.li(2,0x80001fe0)
    a.li(10,0x80001fe0) # magic region
    a.li(11,0x70000000) # NPU
    a.li(5,0x12345678)
    a.sw(5,10)
    def copy(label, source, destination, count):
        a.la(6,source); a.li(7,destination); a.li(28,count)
        a.label(label)
        a.lw(29,6); a.sw(29,7)
        a.addi(6,6,4); a.addi(7,7,4); a.addi(28,28,-1)
        a.branch("bne",28,0,label)
    copy("load_weights","weights",0x70000100,560)
    for idx,c in enumerate(cases):
        a.li(5,idx); a.sw(5,10,20)
        copy(f"load_x_{idx}",f"x_{idx}",0x70000040,16)
        copy(f"load_bias_{idx}",f"bias_{idx}",0x700009c0,38)
        a.li(5,c["mult"]); a.sw(5,11,16)
        a.li(5,c["shift"]); a.sw(5,11,20)
        a.li(5,1); a.sw(5,11)
        a.li(28,10000)
        a.label(f"poll_{idx}")
        a.lw(29,11,4)
        a.andi(5,29,4); a.branch("bne",5,0,"fail")
        a.andi(5,29,1); a.branch("bne",5,0,f"done_{idx}")
        a.addi(28,28,-1); a.branch("bne",28,0,f"poll_{idx}")
        a.jump("fail")
        a.label(f"done_{idx}")
        # x30 = expected, x29 = observed; diagnostic stores preserve both.
        a.li(5,1); a.sw(5,10,4)
        a.la(6,f"expected_{idx}"); a.li(7,0x70000a80); a.li(28,8)
        a.label(f"hidden_{idx}")
        a.lw(29,7); a.lw(30,6); a.branch("bne",29,30,"fail")
        a.addi(7,7,4); a.addi(6,6,4); a.addi(28,28,-1)
        a.branch("bne",28,0,f"hidden_{idx}")
        a.li(5,2); a.sw(5,10,4)
        a.li(7,0x70000b00); a.li(28,6)
        a.label(f"scores_{idx}")
        a.lw(29,7); a.lw(30,6); a.branch("bne",29,30,"fail")
        a.addi(7,7,4); a.addi(6,6,4); a.addi(28,28,-1)
        a.branch("bne",28,0,f"scores_{idx}")
        a.li(5,3); a.sw(5,10,4)
        a.lw(29,11,8); a.lw(30,6); a.branch("bne",29,30,"fail")
        a.li(5,4); a.sw(5,10,4)
        a.lw(29,11,12); a.li(30,2279); a.branch("bne",29,30,"fail")
        a.li(5,2); a.sw(5,11)
    a.li(5,0xc0dec0de); a.sw(5,10)
    a.label("halt"); a.jump("halt")
    a.label("fail")
    a.sw(28,10,8); a.sw(29,10,12); a.sw(30,10,16)
    a.li(5,0xdeadbeef); a.sw(5,10); a.jump("halt")
    code_bytes = len(a.words)*4
    a.label("weights")
    for word in pack(sum(w1,[])+sum(w2,[])):
        a.emit(word,f".word 0x{word:08x}")
    for idx,c in enumerate(cases):
        for name,words in [
            (f"x_{idx}",pack(c["x"])),
            (f"bias_{idx}",c["b1"]+c["b2"]),
            (f"expected_{idx}",pack(c["hidden"])+c["scores"]+[c["category"]]),
        ]:
            a.label(name)
            for word in words:
                a.emit(word,f".word 0x{word & 0xffffffff:08x}")
    a.resolve()
    used = len(a.words)*4
    assert used < 0x1fe0, f"Firmware exceeds SRAM reserved boundary: {used}"
    out.mkdir(parents=True,exist_ok=True)
    hex_path = out/"har_selftest.hex"
    hex_path.write_text("".join(f"{word:08x}\n" for word in a.words+[0]*(2048-len(a.words))),encoding="ascii")
    # This listing is explanatory: resolved address loads are represented by symbols.
    (out/"har_selftest.S").write_text("# Generated RV32I listing; executable is har_selftest.hex.\n"+"\n".join(a.listing)+"\n",encoding="utf-8")
    meta = dict(cases=6,expected_classes=list(range(6)),code_bytes=code_bytes,image_used_bytes=used,sram_bytes=8192,sha256=hashlib.sha256(hex_path.read_bytes()).hexdigest(),labels={k:hex(v) for k,v in a.labels.items()},weights="synthetic, deterministic seed 20261008")
    (out/"har_selftest.json").write_text(json.dumps(meta,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:v for k,v in meta.items() if k!="labels"}))
    return hex_path

if __name__ == "__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--out",type=Path,default=ROOT/"build/sw")
    build(p.parse_args().out)
