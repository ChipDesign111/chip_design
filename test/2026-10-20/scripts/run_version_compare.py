"""Compare real previous INT8 RTL with current W8A4 streaming, equal checks.

CPU collects and checks 24 classes in both versions. Passive TB additionally
checks every hidden and score in both. This is a system-version comparison,
including native precision, transport, batching and driver differences.
"""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import tarfile

import numpy as np

ROOT=Path(__file__).resolve().parents[3]
BASE='52be8c57b365b70536500526a52905352e505666'
STREAM='8afc2e9e21436236704871e806a16b858dfb205b'
sys.path.insert(0,str(ROOT))
from tools.workspace import WORK,begin_run,finish_run
from tools.memory_profile import vendor_model,functional_sim_flags
from model.reference.mlp_int import infer
sys.path.insert(0,str(ROOT/'test/2026-10-15/scripts'))
from build_har_firmware import Assembler,pack
from run_tests import execute,tool,RESULTS


def previous_sources(out):
    """Extract only committed public RTL, never working-tree changes or vendor IP."""
    archive=subprocess.check_output(['git','archive','--format=tar',BASE,'--','rtl'],cwd=ROOT)
    destination=out/'previous_sources';destination.mkdir(parents=True,exist_ok=True)
    with tarfile.open(fileobj=io.BytesIO(archive)) as source:
        for member in source.getmembers():
            name=PurePosixPath(member.name)
            if name.is_absolute() or '..' in name.parts or name.parts[0]!='rtl':
                raise ValueError('Invalid archive path')
            if member.isdir():continue
            if not member.isfile():raise ValueError('Unexpected archive member')
            target=destination/str(name);target.parent.mkdir(parents=True,exist_ok=True)
            target.write_bytes(source.extractfile(member).read())
    return destination


def model_inputs(out):
    fixture=json.loads((ROOT/'test/2026-10-15/fixtures/har_uci24.json').read_text())
    newer=json.loads((ROOT/'test/2026-10-20/fixtures/w8a4_soc24.json').read_text())
    assert fixture['row_ids']==[c['row_id'] for c in newer]
    params=json.loads((ROOT/'model/export/quant_params.json').read_text())
    with np.load(ROOT/'model/export/weights_int8.npz',allow_pickle=False) as z:
        w1=z['fc1_weight_int8'].tolist();w2=z['fc2_weight_int8'].tolist()
    weights=pack([v for row in w1+w2 for v in row])
    previous=[]
    for x in fixture['x_int8']:
        h,s,c=infer(x,w1,w2,params['fc1']['bias_int32'],params['fc2']['bias_int32'],
                    params['hidden_requant']['mul'],params['hidden_requant']['shift'])
        previous.append(dict(input_words_u32=pack(x),hidden_u4=h,scores_int32=s,class_id=c))
    q=json.loads((ROOT/'model/quantization/w8a4.json').read_text())
    models={
        'previous':(weights+params['fc1']['bias_int32']+params['fc2']['bias_int32']+
                    [params['hidden_requant']['mul'],params['hidden_requant']['shift']],previous),
        'current':(weights+q['bias1_int32']+q['bias2_int32']+[q['requant_multiplier'],q['requant_shift']],newer)}
    for name,(words,cases) in models.items():
        assert len(words)==600 and len(cases)==24
        golden=[v for c in cases for v in c['hidden_u4']+c['scores_int32']+[c['class_id']]]
        (out/(name+'_gold.hex')).write_bytes(''.join(f'{v&0xffffffff:08x}\n' for v in golden).encode('ascii'))
    return models,fixture['row_ids']


def build(out,words,cases,current):
    """Same class collection/check work, native version interfaces and drivers."""
    a=Assembler();a.label('_start');a.li(2,0x80001fe0);a.li(10,0x80001fe0)
    a.li(11,0x70000000);a.li(12,0x70000f00);a.li(13,0x80001e00)
    a.li(16,0x80001fc0);a.li(17,0);a.li(24,0)
    a.emit(0x32001073,'csrw mcountinhibit, x0');a.rdcycle(20)
    def dma(label,dest,count):
        a.li(7,0x70000d00);a.sw(6,7,8);a.li(5,dest);a.sw(5,7,12)
        a.li(5,count);a.sw(5,7,16);a.li(5,1);a.sw(5,7);a.li(31,100000)
        a.label(label);a.lw(29,7,4);a.andi(5,29,4);a.branch('bne',5,0,'fail')
        a.andi(5,29,1);a.branch('bne',5,0,label+'_done')
        a.addi(31,31,-1);a.branch('bne',31,0,label);a.jump('fail')
        a.label(label+'_done');a.lw(29,7,24);a.li(30,count);a.branch('bne',29,30,'fail')
        a.lw(29,7,20);a.add(17,17,29);a.li(5,count*4);a.add(6,6,5)
    def poll(label,base):
        a.li(31,10000);a.label(label);a.lw(29,base,4)
        a.andi(5,29,4);a.branch('bne',5,0,'fail');a.andi(5,29,1);a.branch('bne',5,0,label+'_done')
        a.addi(31,31,-1);a.branch('bne',31,0,label);a.jump('fail');a.label(label+'_done')
    a.la(6,'parameters');a.rdcycle(25);dma('load_params',0x70000100,598)
    a.rdcycle(26);a.sub(19,26,25)
    a.li(5,words[598]);a.sw(5,11,16);a.li(5,words[599]);a.sw(5,11,20)
    if current:
        a.li(5,24);a.sw(5,12,8);a.li(5,3);a.sw(5,12,12)
    else:a.li(5,2);a.sw(5,11,24)
    a.rdcycle(18);a.la(8,'inputs')
    if current:
        a.li(5,1);a.sw(5,12);a.addi(6,8,0);a.rdcycle(25)
        dma('load_inputs',0x70000e00,192);a.rdcycle(26);a.sub(24,26,25);poll('poll_npu',12)
        a.li(7,0x70001000);a.li(28,24);a.label('collect')
        a.lw(29,7);a.sw(29,13);a.addi(7,7,4);a.addi(13,13,4);a.addi(28,28,-1)
        a.branch('bne',28,0,'collect')
    else:
        a.li(21,12);a.label('pairs');a.addi(6,8,0);a.rdcycle(25)
        dma('load_x0',0x70000040,16);dma('load_x1',0x70000c00,16)
        a.rdcycle(26);a.sub(26,26,25);a.add(24,24,26)
        a.li(5,1);a.sw(5,11);poll('poll_npu',11)
        a.li(7,0x70000008);a.lw(29,7);a.sw(29,13)
        a.li(7,0x70000c98);a.lw(29,7);a.sw(29,13,4);a.addi(13,13,8)
        a.li(5,2);a.sw(5,11);a.addi(8,8,128);a.addi(21,21,-1);a.branch('bne',21,0,'pairs')
    # Identical CPU verification loop: read 24 collected + 24 expected classes.
    a.rdcycle(26);a.sub(23,26,18)
    a.la(6,'classes');a.li(7,0x80001e00);a.li(28,24);a.label('check_class')
    a.lw(29,7);a.lw(30,6);a.branch('bne',29,30,'fail')
    a.addi(7,7,4);a.addi(6,6,4);a.addi(28,28,-1);a.branch('bne',28,0,'check_class')
    a.rdcycle(26);a.sub(27,26,20);a.sub(26,26,18)
    a.sw(19,16);a.sw(24,16,4);a.sw(27,16,8);a.sw(17,16,12);a.sw(26,16,16)
    a.sw(23,16,20);a.li(5,0xc0dec0de);a.sw(5,10);a.label('halt');a.jump('halt')
    a.label('fail');a.sw(29,10,12);a.sw(30,10,16);a.li(5,0xdeadbeef);a.sw(5,10);a.jump('halt')
    code=len(a.words)*4;a.label('parameters')
    for v in words[:598]:a.emit(v,'.word')
    while len(a.words)*4%32:a.emit(0,'.align 32')
    a.label('inputs')
    for c in cases:
        for v in c['input_words_u32']:a.emit(v,'.word')
    a.label('classes')
    for c in cases:a.emit(c['class_id'],'.word')
    a.resolve();used=len(a.words)*4;assert used<0x1e00
    name='current' if current else 'previous';path=out/(name+'.hex')
    path.write_bytes(''.join(f'{v:08x}\n' for v in a.words+[0]*(2048-len(a.words))).encode('ascii'))
    (out/(name+'.S')).write_bytes(('\n'.join(a.listing)+'\n').encode())
    return path,dict(code_bytes=code,image_used_bytes=used,sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def sources(root,out,memory,current):
    lines=['+define+CHIP_STREAM_NPU'] if current else []
    if memory=='ra1shd':lines+=['+define+CHIP_USE_RA1SHD',vendor_model().as_posix()]
    for raw in (root/'rtl/filelist.f').read_text().splitlines():
        line=raw.strip()
        if not line or line.startswith('#'):continue
        if line.startswith('+incdir+'):lines.append('+incdir+'+(root/line[8:]).as_posix())
        else:lines.append((root/line).as_posix())
    lines.append((ROOT/'test/2026-10-20/rtl/tb_version_compare.sv').as_posix())
    path=out/'sources.f';path.write_bytes(('\n'.join('"'+v+'"' for v in lines)+'\n').encode())
    return path


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--memory',choices=['portable-sram','ra1shd'],default='portable-sram');p.add_argument('--vsim')
    args=p.parse_args();meta=begin_run(' '.join(sys.argv));code=1
    out=WORK/'version_compare';out.mkdir(parents=True,exist_ok=True)
    try:
        previous=previous_sources(out);models,rows=model_inputs(out)
        vsim=tool('vsim',args.vsim);env=os.environ.copy()
        if not env.get('LM_LICENSE_FILE'):
            lic=Path(vsim).parent.parent/'LICENSE.TXT'
            if lic.exists():env['LM_LICENSE_FILE']=str(lic)
        metrics={};images={};identities={}
        observed=['parameter_cycles','input_cycles','application_cycles','warm_cycles','dma_engine_cycles',
                  'dma_read_beats','dma_write_beats','dma_read_bursts','dma_write_bursts',
                  'result_count','compute_cycles','transfer_compute_cycles']
        for name,root,current in [('previous',previous,False),('current',ROOT,True)]:
            directory=out/name;directory.mkdir(exist_ok=True)
            fw,images[name]=build(out,*models[name],current)
            fl=sources(root,directory,args.memory,current)
            command=['onerror {quit -code 1}','onbreak {resume}','vlib work','vmap work work',f'vlog -sv -f {{{fl.as_posix()}}}',
                f'vsim {functional_sim_flags(args.memory)}-suppress 12110 -novopt -onfinish stop -wlf version.wlf {{-G/tb_version_compare/INIT_FILE={fw.as_posix()}}} {{-G/tb_version_compare/GOLD_FILE={(out/(name+"_gold.hex")).as_posix()}}} work.tb_version_compare',
                'run 0','vcd off','run -all','set status [examine -radix hex /tb_version_compare/magic_status]',
                'puts "SOC_MAGIC=$status"','if {![string equal -nocase $status c0dec0de]} {quit -code 2}']
            for field in observed:command += [f'set value [examine -radix hex /tb_version_compare/{field}]',f'puts "BENCH_{field}=$value"']
            command+=['quit -code 0'];script=directory/'run.do';script.write_bytes(('\n'.join(command)+'\n').encode())
            log=execute('version_'+args.memory+'_'+name,[vsim,'-c','-do',f'do {{{script.as_posix()}}}'],cwd=directory,env=env,marker='SOC_MAGIC=c0dec0de',timeout=300)
            stats={field:int(re.search('BENCH_'+field+r'=([0-9a-fA-F]+)',log)[1],16) for field in observed}
            stats['soc_cycles']=RESULTS[-1]['soc_cycles'];stats['transfer_cycles']=stats['parameter_cycles']+stats['input_cycles']
            assert stats['result_count']==24
            assert stats['dma_read_beats']==stats['dma_write_beats']==(790 if current else 982)
            assert (stats['transfer_compute_cycles']>0) if current else (stats['transfer_compute_cycles']==0)
            metrics[name]=stats
            identities[name]={p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted((root/'rtl').rglob('*')) if p.is_file()}
        summary=dict(previous_commit=BASE,stream_rtl_commit=STREAM,memory=args.memory,samples=24,row_ids=rows,
            precisions={'previous':'W8A8 native INT8 input/hidden','current':'W8A4 native INT4 input, UINT4 hidden'},
            weights_resident_in_both=True,weight_bytes=2240,cpu_class_gathers=24,cpu_class_checks=24,
            external_full_hidden_score_class_checks=24,firmware=images,metrics=metrics,source_sha256=identities,
            scope='Whole version comparison, including precision/driver/transport/batching; not pure bubble or weight-residency gain',
            accuracy={'previous':2504/2947,'current':2490/2947},
            speedup={field:metrics['previous'][field]/metrics['current'][field] for field in
                ['parameter_cycles','input_cycles','application_cycles','warm_cycles','soc_cycles']})
        (out/'results.json').write_bytes((json.dumps(summary,indent=2)+'\n').encode())
        (WORK/'results').mkdir(exist_ok=True);(WORK/'results/version_compare.json').write_bytes((json.dumps(summary,indent=2)+'\n').encode())
        print(json.dumps({k:v for k,v in summary.items() if k!='source_sha256'}),flush=True);code=0
    finally:finish_run(meta,code)


if __name__=='__main__':main()
