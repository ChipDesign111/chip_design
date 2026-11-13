"""CPU-memory workloads followed by the original full HAR numerical self-check.

These are explicitly additional workloads, not HAR-only latency benchmarks.
The generated image can be reused by run_soc_xcelium.py --firmware-dir.
"""
import argparse
from pathlib import Path
import firmware
from assembler import Assembler

def prologue(a,name):
 if name=='scratch_128':
  a.li(10,0x80001fd0);a.li(11,128);a.li(12,0);a.label('scratch_loop')
  a.sw(12,10);a.addi(12,12,1);a.addi(11,11,-1);a.branch('bne',11,0,'scratch_loop')
  a.lw(13,10);a.li(14,127);a.branch('bne',13,14,'fail')
 else:
  a.la(15,'patch_word');a.li(19,8192);a.add(19,15,19)
  a.la(16,'patch_return1');a.jump('patch_word')
  a.label('patch_return1');a.li(18,1);a.branch('bne',17,18,'fail')
  a.li(18,0x20)
  a.emit((18<<20)|(19<<15)|(2<<7)|0x23,'sb x18, 2(x19) # +8KiB SRAM alias')
  a.emit(0x0000100f,'fence.i')
  a.la(16,'patch_return2');a.jump('patch_word')
  a.label('patch_return2');a.li(18,2);a.branch('bne',17,18,'fail')
  a.li(18,0x00300893);a.sw(18,15);a.emit(0x0000100f,'fence.i')
  a.la(16,'patch_return3');a.jump('patch_word')
  a.label('patch_return3');a.li(18,3);a.branch('bne',17,18,'fail');a.jump('patch_done')
  a.label('patch_word');a.addi(17,0,1)
  a.emit((16<<15)|0x67,'jalr x0, x16, 0')
  a.label('patch_done')


def build(run, workload, seed=10000):
    original = firmware.Assembler
    class WorkloadAssembler(Assembler):
        def __init__(self):
            super().__init__()
            prologue(self, workload)
    try:
        firmware.Assembler = WorkloadAssembler
        firmware.build(run, seed)
    finally:
        firmware.Assembler = original


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workload', choices=('scratch_128', 'code_patch_alias_byte'), required=True)
    parser.add_argument('--out', type=Path, required=True, help='Fresh seed_N directory')
    parser.add_argument('--seed', type=int, default=10000)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    build(args.out, args.workload, args.seed)


if __name__ == '__main__':
    main()
