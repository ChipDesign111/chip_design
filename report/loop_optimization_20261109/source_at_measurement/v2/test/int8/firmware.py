"""RV32I self-check using the public MMIO protocol and tile-major SRAM data."""
import json

from assembler import Assembler, BASE
from run import make_case
MODES = ('baseline', 'compact', 'unroll2', 'unroll4', 'unroll8', 'scheduled4',
         'aligned4', 'poll4', 'poll8', 'poll_eq', 'reuse4', 'reuse_eq', 'scheduled8',
         'reuse8', 'reuse8_eq')
DEFAULT_MODE = 'scheduled4'


def build(run,seed=10000,mode=DEFAULT_MODE):
    """Emit identical data/checks with a selectable RV32I instruction schedule.

    Baseline retains the original instruction stream. Compact changes only LI;
    unroll modes reduce loop maintenance, and scheduled4 also separates loads
    from their consumers. No mode changes the NPU commands or expected values.
    """
    if mode not in MODES:
        raise ValueError('Unknown firmware mode: %s' % mode)
    mem=make_case(seed)
    batch=mem[0x1f08//4]
    if not 1<=batch<=4:raise ValueError('Invalid batch size')
    a=Assembler()
    a.compact_li = mode != 'baseline'
    loop_modes = ('scheduled4', 'aligned4', 'poll4', 'poll8',
                  'poll_eq', 'reuse4', 'reuse_eq', 'scheduled8', 'reuse8', 'reuse8_eq')
    eight_wide = mode in ('scheduled8', 'reuse8', 'reuse8_eq')
    unroll = 8 if eight_wide else 4 if mode in loop_modes else {'unroll2': 2, 'unroll4': 4, 'unroll8': 8}.get(mode, 1)
    scheduled = mode in loop_modes
    schedule_width = 8 if eight_wide else 4
    golden_register = 24 if eight_wide else 12
    align_loops = mode == 'aligned4'
    poll_gap = {'poll4': 4, 'poll8': 8}.get(mode, 0)
    exact_busy = mode in ('poll_eq', 'reuse_eq', 'reuse8_eq')
    reuse_pointers = mode in ('reuse4', 'reuse_eq', 'reuse8', 'reuse8_eq')
    padding_words = 0
    pointers = {5: None, 6: None}
    phases = {}
    def mark(name):
        phases[name] = BASE + len(a.words)*4
    def align_loop():
        nonlocal padding_words
        if align_loops:
            # All instructions remain RV32I words. Padding executes only on
            # loop entry; the back edge targets the first useful instruction.
            padding = (-len(a.words)) % 8
            for _ in range(padding):a.addi(0,0,0)
            padding_words += padding
    def pointer(reg, value):
        previous = pointers[reg]
        delta = value-previous if previous is not None else None
        if reuse_pointers and delta is not None and -2048 <= delta <= 2047:
            if delta:a.addi(reg,reg,delta)
        elif reuse_pointers and -2048 <= value-0x70000000 <= 2047:
            # x20 remains the fixed NPU MMIO base throughout the program.
            a.addi(reg,20,value-0x70000000)
        else:
            a.li(reg,value)
        pointers[reg] = value
    def advanced(count):
        # Only loops with multiple groups advance their bases. A single group
        # or a straight-line tail uses offsets and leaves both bases unchanged.
        groups = count//unroll
        if groups > 1:
            for reg in (5,6):pointers[reg] += groups*unroll*4
    def grouped(name, count, body):
        """Pointers x5/x6, optional group count x7; tails never overread."""
        groups, tail = divmod(count, unroll)
        if groups > 1:
            a.li(7,groups);align_loop();a.label(name)
            body(unroll)
            a.addi(5,5,4*unroll);a.addi(6,6,4*unroll)
            a.addi(7,7,-1);a.branch('bne',7,0,name)
            body(tail)
        else:
            # A single group needs no loop counter or pointer updates.
            a.label(name)
            body(count)
    mark('configure')
    a.li(20,0x70000000)
    def put(offset,value):a.li(5,value);a.sw(5,20,offset)
    w1_base=mem[0x1f0c//4]
    put(0x20,w1_base);put(0x24,0x80001800)
    put(0x10,mem[0x1f00//4]);put(0x14,mem[0x1f04//4]);put(0x18,batch)
    def copy(name,src,dst,count):
        pointer(5,src);pointer(6,dst)
        if unroll == 1:
            a.li(7,count);a.label(name)
            a.lw(8,5);a.sw(8,6);a.addi(5,5,4);a.addi(6,6,4);a.addi(7,7,-1);a.branch('bne',7,0,name)
            return
        def body(words):
            if scheduled:
                for start in range(0, words, schedule_width):
                    chunk = min(schedule_width, words-start)
                    for i in range(chunk):a.lw(8+i,5,4*(start+i))
                    for i in range(chunk):a.sw(8+i,6,4*(start+i))
            else:
                for i in range(words):a.lw(8,5,4*i);a.sw(8,6,4*i)
        grouped(name,count,body)
        advanced(count)
    mark('copy')
    copy('bias1',0x80001900,0x700009c0,32)
    copy('bias2',0x80001980,0x70000a40,6)
    for n in range(batch):
        destination=0x70000040 if n==0 else 0x70000c00 if n==1 else 0x70001000+(n-2)*64
        copy('x'+str(n),0x80001a00+n*64,destination,16)
    mark('launch')
    if exact_busy:a.li(19,2)
    put(0,1);align_loop();a.label('poll');a.lw(5,20,4)
    if exact_busy:
        # STATUS = {error,busy,done}. Normal running is exactly 2. Any
        # other value exits polling and must still pass the strict DONE==1
        # check below, so an error while busy fails rather than being ignored.
        a.branch('beq',5,19,'poll')
    else:
        # Reduce MMIO polling pressure and separate a load from its consumer.
        # This never predicts completion: the next branch uses the real status.
        for _ in range(poll_gap):a.addi(0,0,0)
        a.andi(6,5,2);a.branch('bne',6,0,'poll')
    mark('verify')
    a.li(6,1);a.branch('bne',5,6,'fail')
    # START and status polling use x5/x6 as values, ending the copy-phase
    # pointer lifetimes. Golden comparisons begin a new known-base region.
    pointers = {5: None, 6: None}
    def compare(name,src,golden,count):
        pointer(5,src);pointer(6,golden)
        if unroll == 1:
            a.li(7,count);a.label(name)
            a.lw(8,5);a.lw(9,6);a.branch('bne',8,9,'fail')
            a.addi(5,5,4);a.addi(6,6,4);a.addi(7,7,-1);a.branch('bne',7,0,name)
            return
        def body(words):
            if scheduled:
                for start in range(0, words, schedule_width):
                    chunk = min(schedule_width, words-start)
                    for i in range(chunk):a.lw(8+i,5,4*(start+i))
                    for i in range(chunk):a.lw(golden_register+i,6,4*(start+i))
                    for i in range(chunk):a.branch('bne',8+i,golden_register+i,'fail')
            else:
                for i in range(words):
                    a.lw(8,5,4*i);a.lw(9,6,4*i);a.branch('bne',8,9,'fail')
        grouped(name,count,body)
        advanced(count)
    for n in range(batch):
        output_base=0x70000a80 if n==0 else 0x70000c40 if n==1 else 0x70001200+(n-2)*64
        score_address=0x70000b00 if n==0 else 0x70000c80 if n==1 else output_base+0x20
        class_address=0x70000008 if n==0 else 0x70000c98 if n==1 else output_base+0x38
        compare('hidden'+str(n),output_base,0x80001c00+n*64,8)
        compare('scores'+str(n),score_address,0x80001c20+n*64,6)
        compare('class'+str(n),class_address,0x80001c38+n*64,1)
    mark('counters')
    a.lw(5,20,0x30);a.li(6,64);a.branch('bne',5,6,'fail')
    a.lw(5,20,0x28);a.li(6,batch*64);a.branch('bne',5,6,'fail')
    a.lw(5,20,0x2c);a.li(6,batch*16);a.branch('bne',5,6,'fail')
    mark('statistics')
    a.li(6,0x80001fc0)
    for offset,reg in [(0,0x0c),(4,0x1c),(8,0x34),(12,0x38)]:a.lw(5,20,reg);a.sw(5,6,offset)
    a.li(5,0xc0dec0de);a.jump('finish')
    a.label('fail');a.li(5,0xdeadbeef)
    a.label('finish');a.li(6,0x80001fe0);a.sw(5,6);a.label('halt');a.jump('halt');a.resolve()
    mark('end')
    code_limit = min(0x1000, w1_base-BASE)
    if len(a.words)*4>code_limit:raise ValueError('Firmware overlaps weights')
    mem[:len(a.words)]=a.words
    (run/'firmware.hex').write_text(''.join('%08x\n'%v for v in mem))
    (run/'firmware.S').write_text('\n'.join(a.listing)+'\n')
    (run/'firmware_meta.json').write_text(json.dumps({
        'mode':mode, 'seed':seed, 'batch':batch, 'code_bytes':len(a.words)*4,
        'instruction_words':len(a.words), 'compact_li':a.compact_li,
        'unroll':unroll, 'labels':a.labels, 'phases':phases,
        'code_limit_bytes':code_limit,
        'align_loops_to_bytes':32 if align_loops else 0,
        'alignment_padding_words':padding_words,
        'poll_gap_words':poll_gap, 'poll_exact_busy':exact_busy,
        'reuse_known_pointers':reuse_pointers,
        'schedule_width_words':schedule_width if scheduled else 0,
    }, indent=2)+'\n')
