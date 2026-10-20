"""Matched W8A4 streaming RTL and real CPU/AXI/SRAM benchmark."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys

import numpy as np

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from tools.workspace import WORK, begin_run, finish_run
sys.path.insert(0,str(ROOT/'test/2026-10-15/scripts'))
from run_tests import execute,tool,filelist,RESULTS
from build_har_firmware import Assembler
from tools.memory_profile import functional_sim_flags

NEW_RTL=['rtl/npu/har_dot_tile.sv','rtl/npu/har_weight_store.sv',
         'rtl/npu/har_stream_core.sv','rtl/npu/har_stream_top.sv']


def vectors(directory,data_root=None):
    directory.mkdir(parents=True,exist_ok=True)
    study=json.loads((ROOT/'test/2026-10-20/precision/results.json').read_text())
    config=next(c for c in study['candidates'] if c['name']==study['recommended'])
    with np.load(ROOT/'model/export/weights_int8.npz',allow_pickle=False) as z:
        w1=z['fc1_weight_int8'].astype(np.int64);w2=z['fc2_weight_int8'].astype(np.int64)
        indices=z['feat_idx'].astype(int)
    values=w1.ravel().tolist()+w2.ravel().tolist()
    words=[sum((int(v)&255)<<(8*k) for k,v in enumerate(values[i:i+4])) for i in range(0,len(values),4)]
    words+=config['bias1_int32']+config['bias2_int32']+[config['requant_multiplier'],config['requant_shift']]
    cases=json.loads((ROOT/'test/2026-10-20/precision/w8a4_soc24_gold.json').read_text())
    def save(name,values):
        path=directory/(name+'.hex');path.write_text(''.join(f'{int(v)&0xffffffff:08x}\n' for v in values),encoding='ascii');return path
    params=save('params',words)
    def record(c):return c['input_words_u32']+c['hidden_u4']+c['scores_int32']+[c['class_id']]
    fixture=save('vectors',[v for c in cases for v in record(c)])
    full=None
    if data_root:
        raw=np.loadtxt(data_root/'test/X_test.txt',usecols=indices,dtype=np.float64)
        x=np.clip(np.rint(raw/config['input_scale']),-7,7).astype(np.int64)
        a=x@w1.T+np.array(config['bias1_int32'])
        h=np.minimum(15,(np.maximum(a,0)*config['requant_multiplier']+(1<<(config['requant_shift']-1)))>>config['requant_shift'])
        score=h@w2.T+np.array(config['bias2_int32']);pred=np.argmax(score,axis=1)
        full_words=[]
        for i in range(len(x)):
            packed=[sum((int(v)&15)<<(4*k) for k,v in enumerate(x[i,j:j+8])) for j in range(0,64,8)]
            full_words+=packed+h[i].tolist()+score[i].tolist()+[int(pred[i])]
        full=save('full_vectors',full_words)
    return words,cases,params,fixture,full


def firmware(directory,words,cases,mode):
    a=Assembler();a.label('_start');a.li(2,0x80001fe0);a.li(10,0x80001fe0)
    a.li(11,0x70000000);a.li(12,0x70000f00);a.li(16,0x80001fc0);a.li(17,0)
    a.emit(0x32001073,'csrw mcountinhibit, x0');a.rdcycle(20)
    def dma(label,dest,count):
        a.li(7,0x70000d00);a.sw(6,7,8);a.li(5,dest);a.sw(5,7,12)
        a.li(5,count);a.sw(5,7,16);a.li(5,1);a.sw(5,7);a.li(31,100000)
        a.label(label);a.lw(29,7,4);a.andi(5,29,4);a.branch('bne',5,0,'fail')
        a.andi(5,29,1);a.branch('bne',5,0,label+'_done')
        a.addi(31,31,-1);a.branch('bne',31,0,label);a.jump('fail')
        a.label(label+'_done');a.lw(29,7,24);a.li(30,count);a.branch('bne',29,30,'fail')
        a.lw(29,7,20);a.add(17,17,29)
    a.la(6,'parameters');a.rdcycle(25);dma('params',0x70000100,598)
    a.rdcycle(26);a.sub(19,26,25)
    a.li(5,words[598]);a.sw(5,11,16);a.li(5,words[599]);a.sw(5,11,20)
    a.li(5,24);a.sw(5,12,8);a.li(5,mode);a.sw(5,12,12)
    a.rdcycle(18);a.li(5,1);a.sw(5,12)
    a.la(6,'inputs');a.rdcycle(25);dma('inputs_dma',0x70000e00,192)
    a.rdcycle(26);a.sub(24,26,25)
    a.li(31,10000);a.label('poll_npu');a.lw(29,12,4)
    a.andi(5,29,4);a.branch('bne',5,0,'fail');a.andi(5,29,1);a.branch('bne',5,0,'check')
    a.addi(31,31,-1);a.branch('bne',31,0,'poll_npu');a.jump('fail')
    a.label('check');a.rdcycle(23);a.sub(23,23,18)
    for offset,value in [(20,384),(24,384),(32,24),(36,24)]:
        a.lw(29,12,offset);a.li(30,value);a.branch('bne',29,30,'fail')
    a.la(6,'classes');a.li(7,0x70001000);a.li(28,24);a.label('check_class')
    a.lw(29,7);a.lw(30,6);a.branch('bne',29,30,'fail')
    a.addi(7,7,4);a.addi(6,6,4);a.addi(28,28,-1);a.branch('bne',28,0,'check_class')
    a.rdcycle(26);a.sub(27,26,20);a.sub(26,26,18)
    a.sw(19,16);a.sw(24,16,4);a.sw(27,16,8);a.sw(17,16,12);a.sw(26,16,16)
    a.sw(23,16,20)
    a.li(5,0xc0dec0de);a.sw(5,10);a.label('halt');a.jump('halt')
    a.label('fail');a.sw(29,10,12);a.sw(30,10,16);a.li(5,0xdeadbeef);a.sw(5,10);a.jump('halt')
    code=len(a.words)*4
    a.label('parameters')
    for v in words[:598]:a.emit(v,'.word')
    while len(a.words)*4 % 32: a.emit(0,'.align 32')
    a.label('inputs')
    for c in cases:
        for v in c['input_words_u32']:a.emit(v,'.word')
    a.label('classes')
    for c in cases:a.emit(c['class_id'],'.word')
    a.resolve();used=len(a.words)*4;assert used<0x1fc0
    path=directory/f'stream_mode{mode}.hex'
    path.write_text(''.join(f'{v:08x}\n' for v in a.words+[0]*(2048-len(a.words))),encoding='ascii')
    return path,{'code_bytes':code,'image_used_bytes':used,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--unit',action='store_true')
    p.add_argument('--memory',choices=['portable-sram','ra1shd'],default='portable-sram')
    p.add_argument('--data-root',type=Path);p.add_argument('--iverilog');p.add_argument('--vvp');p.add_argument('--vsim')
    args=p.parse_args();metadata=begin_run(' '.join(sys.argv));exit_code=1
    out=WORK/'stream';out.mkdir(parents=True,exist_ok=True)
    try:
        words,cases,params,fixture,full=vectors(out,args.data_root)
        iv=tool('iverilog',args.iverilog);vv=tool('vvp',args.vvp)
        dma_image=out/'dma.vvp'
        execute('stream_dma_compile',[iv,'-g2012','-s','tb_stream_dma','-o',dma_image,ROOT/'rtl/dma/har_stream_dma.sv',ROOT/'test/2026-10-20/rtl/tb_stream_dma.sv'])
        execute('stream_dma_protocol',[vv,dma_image],marker='DMA_UNIT PASS transfers=248')
        image=out/'stream.vvp'
        execute('stream_compile',[iv,'-g2012','-s','tb_stream_npu','-o',image,*[ROOT/x for x in NEW_RTL],ROOT/'test/2026-10-20/rtl/tb_stream_npu.sv'])
        log=execute('stream_unit',[vv,image,f'+PARAMS={params.as_posix()}',f'+VECTORS={fixture.as_posix()}'],marker='STREAM_NPU PASS')
        unit=[dict(mode=int(a),samples=int(b),cycles=int(c),result_span=int(d)) for a,b,c,d in
              re.findall(r'STREAM_UNIT mode=(\d+) samples=(\d+) cycles=(\d+) result_span=(\d+)',log)]
        if full:
            execute('stream_full_model',[vv,image,f'+PARAMS={params.as_posix()}',f'+VECTORS={full.as_posix()}','+COUNT=2947','+ONLY_FAST=1'],marker='STREAM_NPU PASS')
        metrics={};images={}
        if not args.unit:
            vsim=tool('vsim',args.vsim);env=os.environ.copy()
            if not env.get('LM_LICENSE_FILE'):
                candidate=Path(vsim).parent.parent/'LICENSE.TXT'
                if candidate.exists():env['LM_LICENSE_FILE']=str(candidate)
            directory=out/args.memory;directory.mkdir(parents=True,exist_ok=True)
            original=filelist('har',args.memory)
            fl=out/'stream_soc.f'
            fl.write_text('+define+CHIP_STREAM_NPU\n'+original.read_text()+f'"{(ROOT/"test/2026-10-20/rtl/tb_stream_soc.sv").as_posix()}"\n')
            observed=['parameter_cycles','input_cycles','application_cycles','warm_cycles','dma_engine_cycles',
                      'dma_read_beats','dma_write_beats','dma_overlap_beats','dma_compute_overlap','dma_transfer_compute_cycles',
                      'result_count','first_result_cycle','last_result_cycle','min_result_interval','max_result_interval',
                      'npu_cycles','npu_fc1_issues','npu_fc2_issues','stream_window_cycles',
                      'first_fc1_issue','last_fc1_issue','first_fc2_issue','last_fc2_issue',
                      'observed_fc1_issues','observed_fc2_issues']
            for mode in (0,1,3):
                fw,images[mode]=firmware(out,words,cases,mode)
                commands=['onerror {quit -code 1}','onbreak {resume}']
                if mode==0:commands+=['if {[file exists work]} {vdel -lib work -all}','vlib work','vmap work work',f'vlog -sv -f {{{fl.as_posix()}}}']
                commands += [f'vsim {functional_sim_flags(args.memory)}-suppress 12110 -novopt -onfinish stop -wlf mode{mode}.wlf {{-G/tb_stream_soc/INIT_FILE={fw.as_posix()}}} {{-G/tb_stream_soc/GOLD_FILE={fixture.as_posix()}}} work.tb_stream_soc',
                    'run 0','vcd off','run -all','set status [examine -radix hex /tb_stream_soc/magic_status]',
                    'puts "SOC_MAGIC=$status"','if {![string equal -nocase $status c0dec0de]} {quit -code 2}']
                for name in observed:commands += [f'set observed [examine -radix hex /tb_stream_soc/{name}]',f'puts "BENCH_{name}=$observed"']
                commands+=['quit -code 0'];script=directory/f'mode{mode}.do';script.write_text('\n'.join(commands)+'\n')
                log=execute(f'stream_soc_{args.memory}_{mode}',[vsim,'-c','-do',f'do {{{script.as_posix()}}}'],cwd=directory,env=env,marker='SOC_MAGIC=c0dec0de',timeout=300)
                stats={name:int(re.search('BENCH_'+name+r'=([0-9a-fA-F]+)',log)[1],16) for name in observed}
                stats['soc_cycles']=RESULTS[-1]['soc_cycles']
                assert stats['result_count']==24 and stats['dma_read_beats']==stats['dma_write_beats']==790,stats
                assert stats['npu_fc1_issues']==stats['npu_fc2_issues']==384,stats
                assert stats['dma_overlap_beats']>0,stats
                if mode:assert stats['dma_transfer_compute_cycles']>0,stats
                assert stats['observed_fc1_issues']==stats['observed_fc2_issues']==384
                stats['fc1_issue_utilization']=384/(stats['last_fc1_issue']-stats['first_fc1_issue']+1)
                stats['fc2_issue_utilization']=384/(stats['last_fc2_issue']-stats['first_fc2_issue']+1)
                metrics[mode]=stats
        summary={'samples':24,'memory':args.memory,'unit':unit,'soc':metrics,'firmware':images,
                 'precision':'W8A4, INT32 accumulation','parameter_words':598,'input_words':192,
                 'scope':'Exact hidden/score/class checks on 24 real rows; matched hardware/precision/software, runtime scheduling mode changes only',
                 'full_model_rtl_samples':2947 if full else 0,
                 'source_sha256':{x:hashlib.sha256((ROOT/x).read_bytes()).hexdigest() for x in NEW_RTL+['rtl/dma/har_stream_dma.sv']}}
        if metrics:summary['speedup']={name:{'serial_to_fast':metrics[0][name]/metrics[3][name],
                        'ii20_to_fast':metrics[1][name]/metrics[3][name]} for name in
                        ['soc_cycles','application_cycles','warm_cycles','stream_window_cycles','npu_cycles']}
        (out/'results.json').write_text(json.dumps(summary,indent=2)+'\n')
        (WORK/'results').mkdir(exist_ok=True)
        (WORK/'results/stream.json').write_text(json.dumps(summary,indent=2)+'\n')
        print(json.dumps(summary),flush=True);exit_code=0
    finally:finish_run(metadata,exit_code)


if __name__=='__main__':main()
