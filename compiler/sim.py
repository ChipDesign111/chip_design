"""Boot a compiled deployment package through the real Debug SBA / AXI path."""
import json,re,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def execute(command,run,name,marker):
    result=subprocess.run([str(v) for v in command],cwd=run,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=300)
    (run/(name+'.log')).write_text(result.stdout,encoding='utf-8')
    if result.returncode or marker not in result.stdout or re.search(r'FATAL:|# \*\* (?:Fatal|Error):|TIMEOUT',result.stdout):
        raise RuntimeError(name+' failed; see '+str(run/(name+'.log'))+'\n'+result.stdout[-4000:])
    print(name+': PASS',flush=True)
    return result.stdout

def simulate(directory,vsim='vsim',profile=False,word_checks=None):
    directory=Path(directory).resolve()
    metadata=json.loads((directory/'manifest.json').read_text())
    expected=json.loads((directory/'reference.json').read_text());ts=metadata['tensors']
    # No expected values are embedded in generated CPU code. The testbench
    # reads real SRAM through the Debug SBA/AXI boundary after execution.
    checks=['result_fd=$fopen("actual_tensors.hex","w"); if(result_fd==0) $fatal(1,"Cannot open tensor dump");']
    for name,values in expected.items():
        t=ts[name];b,n=t['shape']
        if t.get('storage') in ('internal','fused','special_fc','special_hidden'):continue
        for sample in range(b):
            row=bytes(v&255 for v in values[sample])+bytes(t['stride']-n)
            for offset in range(0,len(row),4):
                word=int.from_bytes(row[offset:offset+4],'little')
                address=t["address"]+sample*t["stride"]+offset
                checks.append(f"sba_read(32'h{address:08x},observed);")
                checks.append(f"$fdisplay(result_fd,\"%08x %08x\",32'h{address:08x},observed);")
                checks.append(f"if(observed!==32'h{word:08x}) $fatal(1,\"Tensor {name} row {sample} word {offset//4} mismatch actual %h\",observed);")
    checks.append('$fclose(result_fd);')
    if word_checks:
        for check in word_checks:
            address,value,mask=(check[k] for k in ('address','expected','mask'))
            if any(type(v) is not int or not 0<=v<2**32 for v in (address,value,mask)):
                raise ValueError('Invalid expected-word check')
            checks.append(f"sba_read(32'h{address:08x},observed);if((observed & 32'h{mask:08x})!==32'h{value&mask:08x})$fatal(1,\"Expected-word mismatch addr={address:08x} got %h\",observed);")
        checks.append(f'$display("WORD_CHECKS_PASS words={len(word_checks)}");')
    starts=metadata.get('npu_core_starts',sum(len(n.get('jobs',[])) for n in metadata['nodes'] if n['backend']=='NPU'))
    tb=(ROOT/'test/int8/tb_soc.sv').read_text().replace('module tb_soc;','module tb_compiled_model;')
    # Fitting in8KiB does not imply a CPU fallback finishes in200k clocks.
    # Increase only the testbench watchdog; no instructions/cycles are added.
    cpu_macs=sum(ts[n['inputs'][0]]['shape'][0]*ts[n['inputs'][0]]['shape'][1]*ts[n['name']]['shape'][1]
        for n in metadata['nodes'] if n['backend']=='CPU' and n['op']=='linear')
    cpu_elements=sum(ts[n['name']]['shape'][0]*ts[n['name']]['shape'][1] for n in metadata['nodes'] if n['backend']=='CPU')
    watchdog=max(200000,50000+64*cpu_macs+256*cpu_elements)
    tb=tb.replace('cycles<200000',f'cycles<{watchdog}')
    if metadata.get('rtl_parameters',{}).get('TASK_LUT_WORD_CACHE'):
        tb=tb.replace('my_soc_top dut(',"my_soc_top #(.TASK_LUT_WORD_CACHE(1'b1)) dut(")
    insert="""
    reg [31:0] observed;
    integer npu_starts=0,npu_issue=0,result_fd;
    always @(posedge clk) begin
        if(dut.i_npu_subsystem.i_npu_core.start) npu_starts<=npu_starts+1;
        if(dut.i_npu_subsystem.i_npu_core.core.product_valid) npu_issue<=npu_issue+1;
    end
    task sba_read(input reg [31:0] address,output reg [31:0] value);
        integer timeout;
        begin
            @(negedge clk);load_req=1;load_we=0;load_addr=address;load_be=15;timeout=0;
            @(posedge clk);
            while(!dut.dm_master_gnt && timeout<1000) begin @(posedge clk);timeout=timeout+1;end
            if(timeout>=1000) $fatal(1,"SBA read grant timeout");
            @(negedge clk);load_req=0;timeout=0;
            while(!dut.dm_master_r_valid && timeout<1000) begin @(posedge clk);timeout=timeout+1;end
            if(timeout>=1000) $fatal(1,"SBA read response timeout");
            value=dut.dm_master_r_rdata;
            @(negedge clk);
        end
    endtask
"""
    segments=metadata.get('task_segments',[])
    if segments:
        insert+='''
    integer task_trace_fd,task_segments_seen=0;
    initial begin
        task_trace_fd=$fopen("task_trace.csv","w");
        if(task_trace_fd==0)$fatal(1,"Cannot open task trace");
        $fdisplay(task_trace_fd,"segment,task,sample,element,fc_quant,output");
    end
    always @(posedge clk) begin
        if(dut.i_npu_subsystem.tasks.start && !dut.i_npu_subsystem.task_busy &&
           !dut.i_npu_subsystem.core_busy && !dut.dma_busy)
            task_segments_seen<=task_segments_seen+1;
        if(dut.i_npu_subsystem.post_write)
            $fdisplay(task_trace_fd,"%0d,%0d,%0d,%0d,%0d,%0d",task_segments_seen-1,
                dut.i_npu_subsystem.tasks.index_q,dut.i_npu_subsystem.post_index[6:5],
                dut.i_npu_subsystem.post_index[4:0],$signed(dut.i_npu_subsystem.tasks.quant_q),
                $signed(dut.i_npu_subsystem.post_data));
    end
'''
        checks.insert(0,f'if(task_segments_seen!={len(segments)}) $fatal(1,"Wrong segment count");$fclose(task_trace_fd);')
    specials=metadata.get('special_segments',[])
    if specials:
        insert+='''
    integer special_fd,special_seen=0;
    reg special_pending=0;
    reg [1:0] special_sample;
    reg [4:0] special_element;
    reg signed [21:0] special_raw;
    initial begin
        special_fd=$fopen("special_trace.csv","w");
        if(special_fd==0)$fatal(1,"Cannot open special trace");
        $fdisplay(special_fd,"segment,sample,element,accumulator,hidden");
    end
    always @(posedge clk) begin
        if(dut.i_npu_subsystem.i_npu_core.start && !dut.i_npu_subsystem.i_npu_core.single_mode)
            special_seen<=special_seen+1;
        special_pending<=dut.i_npu_subsystem.i_npu_core.core.quant_value_valid_q;
        special_sample<=dut.i_npu_subsystem.i_npu_core.core.quant_value_sample_q;
        special_element<=dut.i_npu_subsystem.i_npu_core.core.quant_value_index_q;
        special_raw<=dut.i_npu_subsystem.i_npu_core.core.quant_value_q;
    end
    always @(negedge clk) if(special_pending)
        $fdisplay(special_fd,"%0d,%0d,%0d,%0d,%0d",special_seen-1,special_sample,special_element,
            special_raw,$signed(dut.i_npu_subsystem.i_npu_core.core.h[special_sample][special_element*8+:8]));
'''
        checks.insert(0,f'if(special_seen!={len(specials)})$fatal(1,"Wrong MODE0 count");$fclose(special_fd);')
    tb=tb.replace('    integer i;',insert+'\n    integer i;')
    if profile:
        from .profiling import monitor_source
        tb=tb.replace('    integer i;',monitor_source(task_engine=bool(metadata.get('task_abi')))+'\n    integer i;')
    tb=tb.replace('if(read_overlap==0 || write_overlap==0) $fatal(1,"Full AXI SoC did not overlap DMA and MAC");',
                  f'if(npu_starts!={starts}) $fatal(1,"Wrong NPU job count %0d",npu_starts);')
    tb=tb.replace('        $display("INT8_SOC PASS', '\n'.join(checks)+'\n        $display("INT8_SOC PASS')
    # Attach completion to the executable end of the bench, not a comment
    # whose wording can change when the reset contract is updated.
    finish='        $finish;'
    if tb.count(finish)!=1:raise ValueError('Expected one compiled-model completion point')
    tb=tb.replace(finish,f'        $display("COMPILED_MODEL_PASS npu_jobs=%0d npu_issue=%0d",npu_starts,npu_issue);\n'+finish)
    (directory/'tb_compiled_model.sv').write_text(tb)
    fl=[]
    for line in (ROOT/'rtl/filelist.f').read_text().splitlines():
        if line.startswith('+incdir+'):fl.append('+incdir+'+(ROOT/line[8:]).as_posix())
        elif line.strip():fl.append((ROOT/line).as_posix())
    fl.append((directory/'tb_compiled_model.sv').as_posix());(directory/'soc.f').write_text('\n'.join(fl)+'\n')
    shared=(directory.parent/'work').exists()
    compile_commands=['vmap work ../work','vlog -sv tb_compiled_model.sv'] if shared else ['vlib ../work','vmap work ../work','vlog -sv -f soc.f']
    commands=['onerror {quit -code 1}','onbreak {resume}']+compile_commands+[
              'vsim -suppress 12110 -novopt -onfinish stop work.tb_compiled_model','run -all',
              'set status [examine -radix hex /tb_compiled_model/magic]',
              'if {![string equal -nocase $status c0dec0de]} {quit -code 3}','quit -code 0']
    (directory/'soc.do').write_text('\n'.join(commands)+'\n')
    log=execute([vsim,'-c','-do','do soc.do'],directory,'soc','COMPILED_MODEL_PASS')
    if segments:
        import csv
        observed={}
        for row in csv.DictReader((directory/'task_trace.csv').open()):
            si,ti,b,e=(int(row[k]) for k in ('segment','task','sample','element'))
            record=segments[si]['tasks'][ti];e+=record['output_offset']
            for key,column in [('fc_node','fc_quant'),('output_node','output')]:
                name=record[key]
                if name is None:continue
                index=(name,b,e);v=int(row[column])
                if index in observed and observed[index]!=v:raise AssertionError('Inconsistent task trace '+str(index))
                observed[index]=v
                if v!=expected[name][b][e]:raise AssertionError(f'Task integer mismatch {index}: {v} != {expected[name][b][e]}')
        for node in metadata['nodes']:
            if 'segment' not in node:continue
            for b,row in enumerate(expected[node['name']]):
                for e in range(len(row)):
                    if (node['name'],b,e) not in observed:raise AssertionError('Missing task trace '+str((node['name'],b,e)))
        (directory/'task_validation.json').write_text(json.dumps(dict(passed=True,segments=len(segments),
            descriptors=sum(s['count'] for s in segments),observed_integer_values=len(observed)),indent=2)+'\n')
    if specials:
        import csv
        from .compiler import rescale
        nodes={n['name']:n for n in metadata['nodes']};seen=set()
        for row in csv.DictReader((directory/'special_trace.csv').open()):
            si,b,e,acc,h=(int(row[k]) for k in ('segment','sample','element','accumulator','hidden'))
            segment=specials[si];node=nodes[segment['fc1']]
            q=int(rescale(acc,node['mult'][0],node['shift']))
            if q!=expected[segment['fc1']][b][e] or h!=expected[segment['hidden']][b][e]:
                raise AssertionError(f'MODE0 integer boundary mismatch {(si,b,e)}')
            if (si,b,e) in seen:raise AssertionError('Duplicate MODE0 hidden output')
            seen.add((si,b,e))
        if len(seen)!=sum(s['batch']*32 for s in specials):raise AssertionError('Incomplete MODE0 trace')
        (directory/'special_validation.json').write_text(json.dumps(dict(passed=True,segments=len(specials),
            intermediate_values=len(seen)*2),indent=2)+'\n')
    words={int(line.split()[0],16):int(line.split()[1],16) for line in (directory/'actual_tensors.hex').read_text().splitlines()}
    out=ts[metadata['output']];rows=[]
    for sample in range(out['shape'][0]):
        row=[]
        for i in range(out['shape'][1]):
            address=out['address']+sample*out['stride']+i
            byte=(words[address&~3]>>((address&3)*8))&255
            row.append(byte if byte<128 else byte-256)
        rows.append(row)
    (directory/'actual_output.json').write_text(json.dumps(dict(int8=rows,scale=out['scale'],
        dequantized=[[v*out['scale'] for v in row] for row in rows]),indent=2)+'\n')
    if profile:
        from .profiling import summarize
        summarize(directory)
    return log


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('package',type=Path);p.add_argument('--vsim',default='vsim');a=p.parse_args()
    simulate(a.package,a.vsim)
