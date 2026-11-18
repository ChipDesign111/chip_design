#!/usr/bin/env python3
"""Run fresh VCS gate controls and MAXIMUM SDF without changing EDA inputs."""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def execute(command, directory, log):
    (directory/(log+'.command.json')).write_text(json.dumps(command,indent=2)+'\n')
    start=time.time()
    with (directory/log).open('w') as f:
        code=subprocess.call(command,cwd=str(directory),stdout=f,stderr=subprocess.STDOUT)
    (directory/(log+'.exit.json')).write_text(json.dumps({'code':code,'elapsed_s':time.time()-start})+'\n')
    if code:
        raise RuntimeError('Command failed: '+str(directory/log))

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--eda-work',type=Path,required=True)
    ap.add_argument('--run-root',type=Path,required=True);ap.add_argument('--firmware',type=Path,required=True)
    ap.add_argument('--scenario-manifest',type=Path,required=True)
    ap.add_argument('--simulator',choices=['vcs','xcelium'],default='vcs')
    ap.add_argument('--sdf-mode',choices=['tt','pvt-min','pvt-max'],default='tt')
    args=ap.parse_args();work=args.eda_work.resolve();root=args.run_root.resolve()
    if root.exists():raise ValueError('Choose a NEW post-simulation run directory')
    if not (work/'evidence/step_34.json').is_file():raise ValueError('Missing completed EDA input')
    manifest_path=args.scenario_manifest.resolve();manifest=json.loads(manifest_path.read_text())
    if (manifest.get('schema')!=1 or not isinstance(manifest.get('legacy'),dict) or
        not isinstance(manifest.get('raw'),list) or not manifest['raw']):
        raise ValueError('Unsupported post-simulation scenario manifest')
    firmware_root=args.firmware.resolve().parent
    def firmware_file(name):
        if not isinstance(name,str) or Path(name).name!=name or Path(name).suffix!='.hex':
            raise ValueError('Unsafe firmware name in scenario manifest')
        path=(firmware_root/name).resolve()
        if path.parent!=firmware_root or not path.is_file():raise ValueError('Missing scenario firmware: '+name)
        return path
    primary=firmware_file(manifest['legacy'].get('primary'))
    if primary!=args.firmware.resolve():raise ValueError('Primary firmware differs from scenario manifest')
    gate_unit=firmware_file(manifest['legacy'].get('gate_unit'))
    reset_names=manifest['legacy'].get('reset_sweep')
    if not isinstance(reset_names,list):raise ValueError('Missing legacy reset sweep')
    reset_firmware=[firmware_file(name) for name in reset_names]
    raw_cases=[]
    seen_names=set()
    for item in manifest['raw']:
        if not isinstance(item,dict) or not re.fullmatch(r'[a-z0-9_]+',str(item.get('name',''))):
            raise ValueError('Invalid RAW scenario name')
        for field in ('tiles','outputs','inputs','reads','w1_base'):
            if type(item.get(field)) is not int or item[field]<=0:raise ValueError('Invalid RAW scenario '+field)
        output_blocks=(item['outputs']+31)//32
        input_blocks=(item['inputs']+63)//64
        expected_tiles=output_blocks*input_blocks
        expected_reads=sum(min(32,item['outputs']-block*32)*input_blocks
                           for block in range(output_blocks))
        if item['tiles']!=expected_tiles or item['reads']!=expected_reads:
            raise ValueError('RAW scenario tile/read shape is inconsistent')
        if item['w1_base']%4 or item['w1_base']>0xffffffff:raise ValueError('Invalid RAW W1 base')
        if item['name'] in seen_names:raise ValueError('Duplicate RAW scenario name')
        seen_names.add(item['name'])
        raw_cases.append({**item,'path':firmware_file(item.get('firmware'))})
    root.mkdir(parents=True);inputs=root/'inputs';inputs.mkdir()
    out=work/'pnr/my_soc_top/outputs/manual_final'
    config=json.loads((work/'config/design.json').read_text())
    if config['system_period_ns']!=20:raise ValueError('Bench requires20ns matching physical timing')
    paths={'netlist':out/'my_soc_top_hier_postpnr.v','sdf_gz':out/('my_soc_top_tt_io.sdf.gz' if args.sdf_mode=='tt' else 'my_soc_top_pvt.sdf.gz'),
           'firmware':args.firmware.resolve(),'scenario_manifest':manifest_path,
           'testbench':Path(__file__).resolve().with_name('tb_postsim.sv'),
           'standard_cells':Path('/lec/pdk/tsmc180/tcb018gbwp7t_290a/TSMCHOME/digital/Front_End/verilog/tcb018gbwp7t_270a/tcb018gbwp7t.v'),
           'io_cells':Path('/lec/pdk/tsmc180/tpd018nv_280a/TSMCHOME/digital/Front_End/verilog/tpd018nv_260a/tpd018nv.v'),
           'sram':work/'src/macro/RA1SHD_2048x32M8/RA1SHD_2048x32M8.v'}
    record={k:{'source':str(p),'sha256':sha(p)} for k,p in paths.items()}
    for p in reset_firmware+[raw['path'] for raw in raw_cases]:
        record[p.stem]={'source':str(p.resolve()),'sha256':sha(p)}
    (root/'input_manifest.json').write_text(json.dumps({'eda_work':str(work),'simulator':args.simulator,'sdf_mode':args.sdf_mode,'files':record},indent=2)+'\n')
    driver=root/'export.tcl'
    driver.write_text('set eda_work {'+str(work)+'}\nset sim_inputs {'+str(inputs)+'}\nsource {'+str(Path(__file__).resolve().with_name('export_view.tcl'))+'}\n')
    execute(['innovus','-batch','-files',str(driver),'-log',str(root/'view_export')],root,'view_export.log')
    if not (inputs/'netlist.v').is_file():raise ValueError('Missing same-database simulation view')
    with gzip.open(paths['sdf_gz'],'rb') as source,(inputs/'timing.sdf').open('wb') as dest:shutil.copyfileobj(source,dest)
    shutil.copyfile(paths['firmware'],inputs/'firmware.hex');shutil.copyfile(paths['testbench'],inputs/'tb_postsim.sv')
    # Private native-model copy: bind the SDF's missing negedge period check.
    # Reuse the native notifier; annotated limits come from the original SDF.
    text=paths['sram'].read_text()
    if '$period(negedge CLK' not in text:
        text,count=re.subn(r'(?m)^(\s*)specify\s*$',r'\1specify\n\1$period(negedge CLK, 0, NOT_CLK_PER);',text,count=1)
        if count!=1 or 'NOT_CLK_PER' not in text:raise ValueError('Unexpected native SRAM model')
    macro=inputs/'sram_period_adapter.v';macro.write_text(text)
    record['simulation_netlist']={'source':str(inputs/'netlist.v'),'sha256':sha(inputs/'netlist.v')}
    record['sram_simulation_adapter']={'source':str(macro),'sha256':sha(macro),'change':'Add negedge period declaration; native notifier, SDF limits; licensed copy retained server-only'}
    (root/'input_manifest.json').write_text(json.dumps({'eda_work':str(work),'simulator':args.simulator,'sdf_mode':args.sdf_mode,'files':record},indent=2)+'\n')
    build=root/'build';build.mkdir()
    # VCS precompiles literal $sdf_annotate inputs during elaboration.
    shutil.copyfile(inputs/'timing.sdf',build/'timing.sdf')
    command=['vcs','-full64','-sverilog','-j4','-negdelay','+neg_tchk',
             '+define+NTC+RECREM','+sdfverbose','-timescale=1ns/1ps','-top','tb_postsim',
             '-o',str(build/'simv'),str(inputs/'tb_postsim.sv'),str(inputs/'netlist.v')]
    for key in ['standard_cells','io_cells']:command+=['-v',str(paths[key])]
    command+=['-v',str(macro)]
    if args.simulator=='xcelium':
        command=['xrun','-64bit','-sv','-elaborate','-xmlibdirname',str(build/'xcelium.d'),
                 '-snapshot','tb_postsim_sdf','-access','+rwc','-negdelay','-neg_verbose',
                 '-sdf_verbose','-sdfstats',str(build/'sdfstats.log'),'-define','NTC',
                 '-define','RECREM','-timescale','1ns/1ps','-top','tb_postsim',
                 str(inputs/'tb_postsim.sv'),str(inputs/'netlist.v')]
        for key in ['standard_cells','io_cells']:command+=['-v',str(paths[key])]
        command+=['-v',str(macro)]
    if args.sdf_mode=='pvt-min':
        command+=(['+define+SDF_MINIMUM'] if args.simulator=='vcs' else ['-define','SDF_MINIMUM'])
    execute(command,build,'compile.log')
    results={}
    cases=[{'mode':'sdf_max','kind':'legacy','flags':[],'firmware':primary,'metadata':{}},
           {'mode':'gate_unit','kind':'legacy_gate_unit','flags':['+NO_SDF'],'firmware':gate_unit,'metadata':{}}]
    # Sweep asynchronous reset assertion across a full system period, without
    # masking timing checks/notifiers. Keep the first case at the old2ns phase.
    cases += [{'mode':'sdf_'+p.stem,'kind':'legacy_reset_sweep',
               'flags':['+RESET_OFFSET_PS=%d'%(250+1400*i)],'firmware':p,
               'metadata':{'reset_offset_ps':250+1400*i}}
              for i,p in enumerate(reset_firmware)]
    for raw in raw_cases:
        cases.append({'mode':'sdf_raw_'+raw['name'],'kind':'raw_soc',
                      'flags':['+RAW_SCENARIO','+RAW_TILES=%d'%raw['tiles'],
                               '+RAW_OUTPUTS=%d'%raw['outputs'],'+RAW_INPUTS=%d'%raw['inputs'],
                               '+RAW_READS=%d'%raw['reads'],'+RAW_W1_BASE=%x'%raw['w1_base']],
                      'firmware':raw['path'],
                      'metadata':{k:raw[k] for k in ('fixture','tiles','outputs','inputs','reads','w1_base')}})
    plan=[{**{k:v for k,v in case.items() if k!='firmware'},'firmware':str(case['firmware'])}
          for case in cases]
    (root/'run_plan.json').write_text(json.dumps(plan,indent=2)+'\n')
    for case in cases:
        mode=case['mode'];flags=case['flags'];firmware=case['firmware']
        run=root/mode;run.mkdir();shutil.copyfile(firmware,run/'firmware.hex')
        os.link(inputs/'timing.sdf',run/'timing.sdf')
        executable=build/'simv'
        if mode=='gate_unit':
            # Main uses an independent unit-delay control for the linebuffer;
            # native models remain original in all SDF cases. Removing SDF alone leaves a mixture of
            # ideal interconnect and intrinsic cell delays. SDF cases retain
            # all annotated delays, checks and native notifiers.
            control=root/'build_unit';control.mkdir()
            zero=command.copy()
            if args.simulator=='vcs':
                zero[zero.index('-o')+1]=str(control/'simv')
                zero+=['+notimingcheck','+delay_mode_unit','+define+NO_SDF']
            else:
                zero[zero.index('-xmlibdirname')+1]=str(control/'xcelium.d')
                zero[zero.index('-sdfstats')+1]=str(control/'sdfstats.log')
                zero+=['-notimingchecks','-delay_mode','unit','-define','NO_SDF']
            execute(zero,control,'compile.log');executable=control/'simv'
        if args.simulator=='vcs':
            execute([str(executable)]+flags,run,'simulation.log')
        else:
            cache=control if mode=='gate_unit' else build
            execute(['xrun','-64bit','-R','-xmlibdirname',str(cache/'xcelium.d'),
                     '-snapshot','tb_postsim_sdf']+flags,run,'simulation.log')
        text=(run/'simulation.log').read_text(errors='replace')
        legacy_match=re.search(r'FUNCTIONAL_PASS cycles=(\d+) npu_cycles=(\d+) dma_mac_overlap=(\d+) read_overlap=(\d+) write_overlap=(\d+)',text)
        raw_match=re.search(r'FUNCTIONAL_PASS cycles=(\d+) scenario=raw_soc tiles=(\d+) outputs=(\d+) inputs=(\d+) reads=(\d+)',text)
        reset_match=re.search(r'RESET_ASSERT offset_ps=(\d+)',text)
        match=raw_match if case['kind']=='raw_soc' else legacy_match
        if not match or not reset_match or 'POSTSIM_DONE' not in text:raise RuntimeError('Functional/reset result missing: '+mode)
        io_events=[{'time_ps':int(t),'instance':i.strip()} for t,i in re.findall(r'ERROR\s*:\s*(\d+)\s*\+\+BUS CONFLICT\+\+\s*:\s*([^\r\n]+)',text)]
        if case['kind']=='raw_soc':
            raw_values=dict(zip(('observed_cpu_cycles','raw_tiles','raw_outputs','raw_inputs','raw_reads'),map(int,match.groups())))
            if (raw_values['raw_tiles']!=case['metadata']['tiles'] or
                raw_values['raw_outputs']!=case['metadata']['outputs'] or
                raw_values['raw_inputs']!=case['metadata']['inputs'] or
                raw_values['raw_reads']!=case['metadata']['reads']):
                raise RuntimeError('RAW SoC scenario shape mismatch: '+mode)
            result_values=raw_values
        else:
            result_values=dict(zip(('observed_cpu_cycles','npu_cycles','dma_mac_overlap','read_overlap','write_overlap'),
                                   map(int,legacy_match.groups())))
        results[mode]={'functional_pass':True,'kind':case['kind'],'values':result_values,
                       'timing_violation_messages':len(re.findall(r'Timing violation',text,re.I)),
                       'reset_offset_ps':int(reset_match.group(1)),
                       'pad_drive_ps':int(re.search(r'PAD_DRIVE_ON time_ns=[\d.]+ delay_ps=(\d+)',text).group(1)),
                       'io_bus_conflicts':io_events,
                       'timezero_io_warning_free':not io_events}
        (root/'partial_results.json').write_text(json.dumps(results,indent=2)+'\n')
        initial_io=[e for e in io_events if e['time_ps']==0]
        later_io=[e for e in io_events if e['time_ps']!=0]
        expected={'tb_postsim.dut.i_pad_'+n for n in ['clk','rst_n','tck','tms','tdi']}
        if any(e['instance'] not in expected for e in initial_io):
            raise RuntimeError('Unclassified time-zero IO conflict: '+mode)
        if later_io:raise RuntimeError('Unexpected nonzero-time IO conflict: '+mode)
    for item in record.values():
        if sha(Path(item['source']))!=item['sha256']:raise RuntimeError('Input changed: '+item['source'])
    (root/'results.json').write_text(json.dumps(results,indent=2)+'\n')
    print(json.dumps(results,indent=2))

if __name__=='__main__':main()
