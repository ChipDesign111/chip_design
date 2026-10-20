"""Run final W8A4 on the complete CPU/AXI/SRAM/DMA/NPU SoC."""
import argparse,hashlib,json,os,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from tools.workspace import WORK,begin_run,finish_run
from tools.simulation import execute,tool,RESULTS
from tools.memory_profile import vendor_model,functional_sim_flags
from tools.riscv_assembler import Assembler
from run_stream_tests import vectors

def build(out, words, cases):
    """Build final W8A4 CPU self-check with class collection and exact checks."""
    a = Assembler()
    a.label('_start')
    a.li(2, 2147491808)
    a.li(10, 2147491808)
    a.li(11, 1879048192)
    a.li(12, 1879052032)
    a.li(13, 2147491328)
    a.li(16, 2147491776)
    a.li(17, 0)
    a.li(24, 0)
    a.emit(838865011, 'csrw mcountinhibit, x0')
    a.rdcycle(20)

    def dma(label, dest, count):
        a.li(7, 1879051520)
        a.sw(6, 7, 8)
        a.li(5, dest)
        a.sw(5, 7, 12)
        a.li(5, count)
        a.sw(5, 7, 16)
        a.li(5, 1)
        a.sw(5, 7)
        a.li(31, 100000)
        a.label(label)
        a.lw(29, 7, 4)
        a.andi(5, 29, 4)
        a.branch('bne', 5, 0, 'fail')
        a.andi(5, 29, 1)
        a.branch('bne', 5, 0, label + '_done')
        a.addi(31, 31, -1)
        a.branch('bne', 31, 0, label)
        a.jump('fail')
        a.label(label + '_done')
        a.lw(29, 7, 24)
        a.li(30, count)
        a.branch('bne', 29, 30, 'fail')
        a.lw(29, 7, 20)
        a.add(17, 17, 29)
        a.li(5, count * 4)
        a.add(6, 6, 5)

    def poll(label, base):
        a.li(31, 10000)
        a.label(label)
        a.lw(29, base, 4)
        a.andi(5, 29, 4)
        a.branch('bne', 5, 0, 'fail')
        a.andi(5, 29, 1)
        a.branch('bne', 5, 0, label + '_done')
        a.addi(31, 31, -1)
        a.branch('bne', 31, 0, label)
        a.jump('fail')
        a.label(label + '_done')
    a.la(6, 'parameters')
    a.rdcycle(25)
    dma('load_params', 1879048448, 598)
    a.rdcycle(26)
    a.sub(19, 26, 25)
    a.li(5, words[598])
    a.sw(5, 11, 16)
    a.li(5, words[599])
    a.sw(5, 11, 20)
    a.li(5, 24)
    a.sw(5, 12, 8)
    a.li(5, 3)
    a.sw(5, 12, 12)
    a.rdcycle(18)
    a.la(8, 'inputs')
    a.li(5, 1)
    a.sw(5, 12)
    a.addi(6, 8, 0)
    a.rdcycle(25)
    dma('load_inputs', 1879051776, 192)
    a.rdcycle(26)
    a.sub(24, 26, 25)
    poll('poll_npu', 12)
    a.li(7, 1879052288)
    a.li(28, 24)
    a.label('collect')
    a.lw(29, 7)
    a.sw(29, 13)
    a.addi(7, 7, 4)
    a.addi(13, 13, 4)
    a.addi(28, 28, -1)
    a.branch('bne', 28, 0, 'collect')
    a.rdcycle(26)
    a.sub(23, 26, 18)
    a.la(6, 'classes')
    a.li(7, 2147491328)
    a.li(28, 24)
    a.label('check_class')
    a.lw(29, 7)
    a.lw(30, 6)
    a.branch('bne', 29, 30, 'fail')
    a.addi(7, 7, 4)
    a.addi(6, 6, 4)
    a.addi(28, 28, -1)
    a.branch('bne', 28, 0, 'check_class')
    a.rdcycle(26)
    a.sub(27, 26, 20)
    a.sub(26, 26, 18)
    a.sw(19, 16)
    a.sw(24, 16, 4)
    a.sw(27, 16, 8)
    a.sw(17, 16, 12)
    a.sw(26, 16, 16)
    a.sw(23, 16, 20)
    a.li(5, 3235823838)
    a.sw(5, 10)
    a.label('halt')
    a.jump('halt')
    a.label('fail')
    a.sw(29, 10, 12)
    a.sw(30, 10, 16)
    a.li(5, 3735928559)
    a.sw(5, 10)
    a.jump('halt')
    code = len(a.words) * 4
    a.label('parameters')
    for v in words[:598]:
        a.emit(v, '.word')
    while len(a.words) * 4 % 32:
        a.emit(0, '.align 32')
    a.label('inputs')
    for c in cases:
        for v in c['input_words_u32']:
            a.emit(v, '.word')
    a.label('classes')
    for c in cases:
        a.emit(c['class_id'], '.word')
    a.resolve()
    used = len(a.words) * 4
    assert used < 7680
    name = 'firmware'
    path = out / (name + '.hex')
    path.write_bytes(''.join((f'{v:08x}\n' for v in a.words + [0] * (2048 - len(a.words)))).encode('ascii'))
    (out / (name + '.S')).write_bytes(('\n'.join(a.listing) + '\n').encode())
    return (path, dict(code_bytes=code, image_used_bytes=used, sha256=hashlib.sha256(path.read_bytes()).hexdigest()))

def sources(out,memory):
    lines=[]
    if memory=='ra1shd':lines+=['+define+CHIP_USE_RA1SHD',vendor_model().as_posix()]
    for raw in (ROOT/'rtl/filelist.f').read_text().splitlines():
        line=raw.strip()
        if not line or line.startswith('#'):continue
        if line.startswith('+incdir+'):lines.append('+incdir+'+(ROOT/line[8:]).as_posix())
        else:lines.append((ROOT/line).as_posix())
    lines.append((ROOT/'test/2026-10-20/rtl/tb_soc.sv').as_posix())
    path=out/'sources.f';path.write_bytes(('\n'.join('"'+v+'"' for v in lines)+'\n').encode())
    return path
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--memory',choices=['portable-sram','ra1shd'],default='portable-sram');p.add_argument('--vsim')
    args=p.parse_args();meta=begin_run(' '.join(sys.argv));code=1
    out=WORK/'soc';out.mkdir(parents=True,exist_ok=True)
    try:
        words,cases,_,_,_=vectors(out)
        gold=[v for c in cases for v in c['hidden_u4']+c['scores_int32']+[c['class_id']]]
        (out/'gold.hex').write_bytes(''.join(f'{v&0xffffffff:08x}\n' for v in gold).encode())
        fw,image=build(out,words,cases);fl=sources(out,args.memory)
        vsim=tool('vsim',args.vsim);env=os.environ.copy()
        if not env.get('LM_LICENSE_FILE'):
            lic=Path(vsim).parent.parent/'LICENSE.TXT'
            if lic.exists():env['LM_LICENSE_FILE']=str(lic)
        observed=['parameter_cycles','input_cycles','application_cycles','warm_cycles','dma_engine_cycles',
                  'dma_read_beats','dma_write_beats','dma_read_bursts','dma_write_bursts','result_count','compute_cycles','transfer_compute_cycles']
        commands=['onerror {quit -code 1}','onbreak {resume}','vlib work','vmap work work',f'vlog -sv -f {{{fl.as_posix()}}}',
                  f'vsim {functional_sim_flags(args.memory)}-suppress 12110 -novopt -onfinish stop -wlf soc.wlf {{-G/tb_soc/INIT_FILE={fw.as_posix()}}} {{-G/tb_soc/GOLD_FILE={(out/"gold.hex").as_posix()}}} work.tb_soc',
                  'run 0','vcd off','run -all','set status [examine -radix hex /tb_soc/magic_status]',
                  'puts "SOC_MAGIC=$status"','if {![string equal -nocase $status c0dec0de]} {quit -code 2}']
        for field in observed:commands += [f'set value [examine -radix hex /tb_soc/{field}]',f'puts "BENCH_{field}=$value"']
        commands+=['quit -code 0'];script=out/'run.do';script.write_bytes(('\n'.join(commands)+'\n').encode())
        log=execute('soc_'+args.memory,[vsim,'-c','-do',f'do {{{script.as_posix()}}}'],cwd=out,env=env,marker='SOC_MAGIC=c0dec0de',timeout=300)
        stats={field:int(re.search('BENCH_'+field+r'=([0-9a-fA-F]+)',log)[1],16) for field in observed}
        stats['soc_cycles']=RESULTS[-1]['soc_cycles']
        assert stats['result_count']==24 and stats['dma_read_beats']==stats['dma_write_beats']==790
        assert stats['transfer_compute_cycles']>0
        result={'memory':args.memory,'samples':24,'firmware':image,'metrics':stats,'precision':'W8A4','scope':'Final design only; CPU checks 24 classes, passive TB checks all hidden/score/class values'}
        (WORK/'results').mkdir(exist_ok=True);(WORK/'results/soc.json').write_bytes((json.dumps(result,indent=2)+'\n').encode())
        print(json.dumps(result),flush=True);code=0
    finally:finish_run(meta,code)
if __name__=='__main__':main()
