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
    ap.add_argument('--simulator',choices=['vcs','xcelium'],default='vcs')
    ap.add_argument('--sdf-mode',choices=['tt','pvt-min','pvt-max'],default='tt')
    args=ap.parse_args();work=args.eda_work.resolve();root=args.run_root.resolve()
    if root.exists():raise ValueError('Choose a NEW post-simulation run directory')
    if not (work/'evidence/step_34.json').is_file():raise ValueError('Missing completed EDA input')
    root.mkdir(parents=True);inputs=root/'inputs';inputs.mkdir()
    out=work/'pnr/my_soc_top/outputs/manual_final'
    config=json.loads((work/'config/design.json').read_text())
    if config['system_period_ns']!=20:raise ValueError('Bench requires20ns matching physical timing')
    paths={'netlist':out/'my_soc_top_hier_postpnr.v','sdf_gz':out/('my_soc_top_tt_io.sdf.gz' if args.sdf_mode=='tt' else 'my_soc_top_pvt.sdf.gz'),
           'firmware':args.firmware.resolve(),'testbench':Path(__file__).resolve().with_name('tb_postsim.sv'),
           'standard_cells':Path('/lec/pdk/tsmc180/tcb018gbwp7t_290a/TSMCHOME/digital/Front_End/verilog/tcb018gbwp7t_270a/tcb018gbwp7t.v'),
           'io_cells':Path('/lec/pdk/tsmc180/tpd018nv_280a/TSMCHOME/digital/Front_End/verilog/tpd018nv_260a/tpd018nv.v'),
           'sram':work/'src/macro/RA1SHD_2048x32M8/RA1SHD_2048x32M8.v'}
    record={k:{'source':str(p),'sha256':sha(p)} for k,p in paths.items()}
    additional=sorted(args.firmware.parent.glob('firmware_*.hex'))
    for p in additional:record[p.stem]={'source':str(p.resolve()),'sha256':sha(p)}
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
    cases=[('sdf_max',[],inputs/'firmware.hex'),('gate_zero',['+NO_SDF'],inputs/'firmware.hex')]
    # Sweep asynchronous reset assertion across a full system period, without
    # masking timing checks/notifiers. Keep the first case at the old2ns phase.
    cases += [('sdf_'+p.stem,['+RESET_OFFSET_PS=%d'%(250+1400*i)],p) for i,p in enumerate(additional)]
    (root/'run_plan.json').write_text(json.dumps([{'mode':m,'flags':f,'firmware':str(p)} for m,f,p in cases],indent=2)+'\n')
    for mode,flags,firmware in cases:
        run=root/mode;run.mkdir();shutil.copyfile(firmware,run/'firmware.hex')
        os.link(inputs/'timing.sdf',run/'timing.sdf')
        executable=build/'simv'
        if mode=='gate_zero':
            # A zero-delay netlist driving a native nonzero-setup SRAM is not
            # a timing experiment. This explicit control alone disables checks.
            control=root/'build_zero';control.mkdir()
            zero=command.copy()
            if args.simulator=='vcs':
                zero[zero.index('-o')+1]=str(control/'simv')
                zero+=['+notimingcheck','+define+NO_SDF']
            else:
                zero[zero.index('-xmlibdirname')+1]=str(control/'xcelium.d')
                zero[zero.index('-sdfstats')+1]=str(control/'sdfstats.log')
                zero+=['-notimingchecks','-define','NO_SDF']
            execute(zero,control,'compile.log');executable=control/'simv'
        if args.simulator=='vcs':
            execute([str(executable)]+flags,run,'simulation.log')
        else:
            cache=control if mode=='gate_zero' else build
            execute(['xrun','-64bit','-R','-xmlibdirname',str(cache/'xcelium.d'),
                     '-snapshot','tb_postsim_sdf']+flags,run,'simulation.log')
        text=(run/'simulation.log').read_text(errors='replace')
        match=re.search(r'FUNCTIONAL_PASS cycles=(\d+) npu_cycles=(\d+) dma_mac_overlap=(\d+) read_overlap=(\d+) write_overlap=(\d+)',text)
        reset_match=re.search(r'RESET_ASSERT offset_ps=(\d+)',text)
        if not match or not reset_match or 'POSTSIM_DONE' not in text:raise RuntimeError('Functional/reset result missing: '+mode)
        io_events=[{'time_ps':int(t),'instance':i.strip()} for t,i in re.findall(r'ERROR\s*:\s*(\d+)\s*\+\+BUS CONFLICT\+\+\s*:\s*([^\r\n]+)',text)]
        results[mode]={'functional_pass':bool(match),'values':list(map(int,match.groups())) if match else None,
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
