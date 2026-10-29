"""RV32I self-check using the public MMIO protocol and tile-major SRAM data."""
from assembler import Assembler
from run import make_case
def build(run,seed=10000):
    mem=make_case(seed)
    batch=mem[0x1f08//4]
    if not 1<=batch<=4:raise ValueError('Invalid batch size')
    a=Assembler()
    a.li(20,0x70000000)
    def put(offset,value):a.li(5,value);a.sw(5,20,offset)
    put(0x20,0x80001000);put(0x24,0x80001800)
    put(0x10,mem[0x1f00//4]);put(0x14,mem[0x1f04//4]);put(0x18,batch)
    def copy(name,src,dst,count):
        a.li(5,src);a.li(6,dst);a.li(7,count);a.label(name)
        a.lw(8,5);a.sw(8,6);a.addi(5,5,4);a.addi(6,6,4);a.addi(7,7,-1);a.branch('bne',7,0,name)
    copy('bias1',0x80001900,0x700009c0,32)
    copy('bias2',0x80001980,0x70000a40,6)
    for n in range(batch):
        destination=0x70000040 if n==0 else 0x70000c00 if n==1 else 0x70001000+(n-2)*64
        copy('x'+str(n),0x80001a00+n*64,destination,16)
    put(0,1);a.label('poll');a.lw(5,20,4);a.andi(6,5,2);a.branch('bne',6,0,'poll')
    a.li(6,1);a.branch('bne',5,6,'fail')
    def compare(name,src,golden,count):
        a.li(5,src);a.li(6,golden);a.li(7,count);a.label(name)
        a.lw(8,5);a.lw(9,6);a.branch('bne',8,9,'fail')
        a.addi(5,5,4);a.addi(6,6,4);a.addi(7,7,-1);a.branch('bne',7,0,name)
    for n in range(batch):
        output_base=0x70000a80 if n==0 else 0x70000c40 if n==1 else 0x70001200+(n-2)*64
        score_address=0x70000b00 if n==0 else 0x70000c80 if n==1 else output_base+0x20
        class_address=0x70000008 if n==0 else 0x70000c98 if n==1 else output_base+0x38
        compare('hidden'+str(n),output_base,0x80001c00+n*64,8)
        compare('scores'+str(n),score_address,0x80001c20+n*64,6)
        compare('class'+str(n),class_address,0x80001c38+n*64,1)
    a.lw(5,20,0x30);a.li(6,64);a.branch('bne',5,6,'fail')
    a.lw(5,20,0x28);a.li(6,batch*32);a.branch('bne',5,6,'fail')
    a.lw(5,20,0x2c);a.li(6,batch*4);a.branch('bne',5,6,'fail')
    a.li(6,0x80001fc0)
    for offset,reg in [(0,0x0c),(4,0x1c),(8,0x34),(12,0x38)]:a.lw(5,20,reg);a.sw(5,6,offset)
    a.li(5,0xc0dec0de);a.jump('finish')
    a.label('fail');a.li(5,0xdeadbeef)
    a.label('finish');a.li(6,0x80001fe0);a.sw(5,6);a.label('halt');a.jump('halt');a.resolve()
    if len(a.words)*4>0x1000:raise ValueError('Firmware overlaps weights')
    mem[:len(a.words)]=a.words
    (run/'firmware.hex').write_text(''.join('%08x\n'%v for v in mem))
    (run/'firmware.S').write_text('\n'.join(a.listing)+'\n')
