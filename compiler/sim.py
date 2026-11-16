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

def simulate(directory,vsim='vsim'):
    directory=Path(directory).resolve()
    metadata=json.loads((directory/'manifest.json').read_text())
    expected=json.loads((directory/'reference.json').read_text());ts=metadata['tensors']
    # No expected values are embedded in generated CPU code. The testbench
    # reads real SRAM through the Debug SBA/AXI boundary after execution.
    checks=['result_fd=$fopen("actual_tensors.hex","w"); if(result_fd==0) $fatal(1,"Cannot open tensor dump");']
    for name,values in expected.items():
        t=ts[name];b,n=t['shape']
        for sample in range(b):
            row=bytes(v&255 for v in values[sample])+bytes(t['stride']-n)
            for offset in range(0,len(row),4):
                word=int.from_bytes(row[offset:offset+4],'little')
                address=t["address"]+sample*t["stride"]+offset
                checks.append(f"sba_read(32'h{address:08x},observed);")
                checks.append(f"$fdisplay(result_fd,\"%08x %08x\",32'h{address:08x},observed);")
                checks.append(f"if(observed!==32'h{word:08x}) $fatal(1,\"Tensor {name} row {sample} word {offset//4} mismatch actual %h\",observed);")
    checks.append('$fclose(result_fd);')
    starts=sum(len(n.get('jobs',[])) for n in metadata['nodes'] if n['backend']=='NPU')
    tb=(ROOT/'test/int8/tb_soc.sv').read_text().replace('module tb_soc;','module tb_compiled_model;')
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
    tb=tb.replace('    integer i;',insert+'\n    integer i;')
    tb=tb.replace('if(read_overlap==0 || write_overlap==0) $fatal(1,"Full AXI SoC did not overlap DMA and MAC");',
                  f'if(npu_starts!={starts}) $fatal(1,"Wrong NPU job count %0d",npu_starts);')
    tb=tb.replace('        $display("INT8_SOC PASS', '\n'.join(checks)+'\n        $display("INT8_SOC PASS')
    tb=tb.replace('        // User-authorized shared reset',f'        $display("COMPILED_MODEL_PASS npu_jobs=%0d npu_issue=%0d",npu_starts,npu_issue);\n        // User-authorized shared reset')
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
    return log


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('package',type=Path);p.add_argument('--vsim',default='vsim');a=p.parse_args()
    simulate(a.package,a.vsim)
