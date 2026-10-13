"""Looped RV32I CPU self-check for 24 real UCI inputs and trained parameters."""
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.build_har_firmware import Assembler,pack
import hashlib

def build_model():
    out=ROOT/"build/real_model"
    words=[int(v,16) for v in (out/"weights.hex").read_text().split()]
    raw=[int(v,16) for v in (out/"soc24.hex").read_text().split()]
    assert len(raw)==24*105 and len(words)==600
    records=[]
    for n in range(24):
        row=raw[n*105:(n+1)*105]
        records+= [row[104]]+pack(row[:64])+pack(row[64:96])+row[96:103]
    assert len(records)==24*32
    a=Assembler()
    a.label("_start");a.li(2,0x80001fe0);a.li(10,0x80001fe0);a.li(11,0x70000000)
    a.li(5,0x12345678);a.sw(5,10)
    def copy_loop(label,destination,count):
        a.li(7,destination);a.li(28,count);a.label(label)
        a.lw(29,6);a.sw(29,7);a.addi(6,6,4);a.addi(7,7,4);a.addi(28,28,-1)
        a.branch("bne",28,0,label)
    a.la(6,"model_weights");copy_loop("load_model",0x70000100,598)
    a.li(5,words[598]);a.sw(5,11,16);a.li(5,words[599]);a.sw(5,11,20)
    a.li(5,2);a.sw(5,11,24)
    a.la(8,"records");a.li(21,12)
    a.label("pair_loop")
    a.lw(5,8);a.sw(5,10,20)
    a.addi(6,8,4);copy_loop("load_input0",0x70000040,16);a.addi(22,6,0)
    a.addi(6,8,132);copy_loop("load_input1",0x70000c00,16);a.addi(23,6,0)
    a.li(5,1);a.sw(5,11);a.li(28,10000)
    a.label("poll");a.lw(29,11,4);a.andi(5,29,4);a.branch("bne",5,0,"fail")
    a.andi(5,29,1);a.branch("bne",5,0,"finished")
    a.addi(28,28,-1);a.branch("bne",28,0,"poll");a.jump("fail")
    a.label("finished")
    for slot in range(2):
        a.addi(6,22+slot,0)
        for stage,address,count in [(1,0x70000a80 if slot==0 else 0x70000c40,8),
                                    (2,0x70000b00 if slot==0 else 0x70000c80,6),
                                    (3,0x70000008 if slot==0 else 0x70000c98,1)]:
            a.li(5,stage+slot*10);a.sw(5,10,4)
            a.li(7,address);a.li(28,count);a.label(f"check_{slot}_{stage}")
            a.lw(29,7);a.lw(30,6);a.branch("bne",29,30,"fail")
            a.addi(7,7,4);a.addi(6,6,4);a.addi(28,28,-1);a.branch("bne",28,0,f"check_{slot}_{stage}")
    for offset,expected in [(12,59),(28,18),(32,38),(36,38)]:
        a.lw(29,11,offset);a.li(30,expected);a.branch("bne",29,30,"fail")
    a.li(5,2);a.sw(5,11)
    a.addi(8,8,256);a.addi(21,21,-1);a.branch("bne",21,0,"pair_loop")
    a.li(5,0xc0dec0de);a.sw(5,10)
    a.label("halt");a.jump("halt")
    a.label("fail");a.sw(28,10,8);a.sw(29,10,12);a.sw(30,10,16)
    a.li(5,0xdeadbeef);a.sw(5,10);a.jump("halt")
    code_bytes=len(a.words)*4
    a.label("model_weights")
    for v in words[:598]:a.emit(v,f".word 0x{v:08x}")
    a.label("records")
    for v in records:a.emit(v,f".word 0x{v:08x}")
    a.resolve()
    used=len(a.words)*4
    assert used<0x1fe0
    image=out/"model_selftest.hex"
    image.write_text("".join(f"{v:08x}\n" for v in a.words+[0]*(2048-len(a.words))),encoding="ascii")
    (out/"model_selftest.S").write_text("\n".join(a.listing)+"\n")
    meta={"samples":24,"batches":12,"code_bytes":code_bytes,"image_used_bytes":used,"sram_bytes":8192,
        "sha256":hashlib.sha256(image.read_bytes()).hexdigest(),"comparison":"Every hidden, score and predicted class against integer gold, not against the true activity label"}
    (out/"firmware.json").write_text(json.dumps(meta,indent=2)+"\n")
    print(json.dumps(meta),flush=True)
    return image
if __name__=="__main__":build_model()
