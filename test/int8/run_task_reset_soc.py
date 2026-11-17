"""Interrupt real task DMA/postprocessing with POR and actual DMCONTROL NDM.

Reload the entire image after reset and verify recovery through real SBA.
No AXI, DMA status, NPU completion or reset-generator output is forced.
"""
import argparse,datetime,hashlib,json,sys
from pathlib import Path
import torch
from torch import nn
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from compiler.compiler import compile_model
from compiler.sim import execute


def main():
    p=argparse.ArgumentParser();p.add_argument('--vsim',default='vsim');p.add_argument('--lut-cache',action='store_true');args=p.parse_args()
    run=ROOT/'test/int8/runs'/('task_reset_soc_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));run.mkdir(parents=True)
    torch.manual_seed(264);model=nn.Sequential(nn.Linear(64,32),nn.Sigmoid()).eval()
    x=torch.linspace(-1,1,256).reshape(4,64)
    package=compile_model(model,x,[-x,x*0.5],task_engine=True,lut_cache=args.lut_cache)
    prefix=(ROOT/'test/int8/tb_soc.sv').read_text().split('    integer i;',1)[0].replace('module tb_soc;','module tb_task_reset_soc;')
    if args.lut_cache:prefix=prefix.replace('my_soc_top dut(',"my_soc_top #(.TASK_LUT_WORD_CACHE(1'b1)) dut(")
    # Reuse the already checked real-DMCONTROL transaction protocol. RTL has
    # structured nets; the physical export uses escaped flattened field names.
    dmi=(ROOT/'eda/server/postsim/tb_postsim.sv').read_text().split('  task dmi_access',1)[1].split('  // Observe after',1)[0]
    dmi='  task dmi_access'+dmi.replace('dut.\\debug_resp[data] ','dut.debug_resp.data').replace('@(posedge clk);#5;','@(posedge clk);#1;').replace("dmi_operation=writing ? 2'b10 : 2'b01",'dmi_operation=writing ? dm::DTM_WRITE : dm::DTM_READ')
    helper='''
    reg dmi_valid=0,dmi_response_ready=0;
    reg [6:0] dmi_address=0;reg [31:0] dmi_data=0;dm::dtm_op_e dmi_operation=dm::DTM_NOP;
    dm::dmi_req_t dmi_request;
    always_comb begin dmi_request.addr=dmi_address;dmi_request.op=dmi_operation;dmi_request.data=dmi_data;end
    task sba_read(input reg [31:0] address,output reg [31:0] value);
        integer t;
        begin
            @(negedge clk);load_req=1;load_we=0;load_addr=address;load_be=15;t=0;
            @(posedge clk);while(!dut.dm_master_gnt && t<1000)begin @(posedge clk);t=t+1;end
            if(t>=1000)$fatal(1,"SBA read grant timeout");
            @(negedge clk);load_req=0;t=0;
            while(!dut.dm_master_r_valid && t<1000)begin @(posedge clk);t=t+1;end
            if(t>=1000)$fatal(1,"SBA read response timeout");
            value=dut.dm_master_r_rdata;@(negedge clk);
        end
    endtask
    integer i,t;reg [31:0] observed;
    task boot_image;
        begin
            t=0;
            while(dut.ndmreset_n!==1'b1 && t<40)begin @(negedge clk);t=t+1;end
            if(t>=40 || dut.boot_ready || dut.instr_req)$fatal(1,"Reset bypassed guarded boot");
            for(i=0;i<2048;i=i+1)sba_write(32'h80000000+i*4,image[i],15);
            sba_write(32'h0001003c,32'hb007c0de,15);
        end
    endtask
'''
    results=[]
    sources={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'rtl').rglob('*') if p.is_file()}
    for state,kind in [(2,'por'),(12,'ndm'),(19,'por'),(22,'ndm')]:
        out=run/f'{kind}_{state}';values=package.write(out,x.numpy());gold=values[package.graph['output']]
        checks=[];spec=package.metadata['tensors'][package.graph['output']]
        for b,row in enumerate(gold):
            for offset in range(0,32,4):
                address=spec['address']+b*spec['stride']+offset;word=int.from_bytes(row[offset:offset+4].tobytes(),'little')
                checks += [f"sba_read(32'h{address:08x},observed);if(observed!==32'h{word:08x})$fatal(1,\"Recovery tensor mismatch\");"]
        interrupt="rst_n=0;" if kind=='por' else "dmcontrol_write(32'h00000001);dmcontrol_write(32'h00000003);"
        release="rst_n=1;" if kind=='por' else "dmcontrol_write(32'h00000001);"
        body='''
    initial begin
        force dut.dm_master_req=load_req;force dut.dm_master_we=load_we;
        force dut.dm_master_add=load_addr;force dut.dm_master_wdata=load_data;force dut.dm_master_be=load_be;
        force dut.debug_req_valid=dmi_valid;force dut.debug_req=dmi_request;
        force dut.debug_resp_ready=dmi_response_ready;
        $readmemh("firmware.hex",image);
        #1;repeat(5) @(negedge clk);#2;rst_n=1;boot_image();t=0;
        while(dut.i_npu_subsystem.tasks.state!=TARGET && t<20000)begin @(negedge clk);t=t+1;end
        if(t>=20000)$fatal(1,"Reset target state not reached");
        INTERRUPT
        repeat(4) @(negedge clk);#1;
        if(dut.ndmreset_n || dut.boot_ready || dut.i_npu_subsystem.task_busy || dut.dma_busy ||
           dut.i_npu_subsystem.task_valid || dut.i_npu_subsystem.tasks.forward_q ||
           dut.i_npu_subsystem.tasks.partial_q || dut.i_npu_subsystem.tasks.lut_valid_q)
            $fatal(1,"Active reset retained task/AXI/output context");
        if(magic===32'hc0dec0de)$fatal(1,"Reset happened after task completion");
        RELEASE
        fetch_started=0;magic=0;cycles=0;
        boot_image();
        while(magic!==32'hc0dec0de && cycles<20000)begin
            @(negedge clk);cycles=cycles+1;
            if(magic===32'hdeadbeef)$fatal(1,"Recovery firmware failed");
        end
        if(magic!==32'hc0dec0de)$fatal(1,"Recovery firmware timeout");
        CHECKS
        sba_read(32'h70001604,observed);if(observed!==9)$fatal(1,"Recovery status invalid");
        $display("TASK_RESET_SOC PASS kind=KIND state=TARGET cycles=%0d",cycles);$finish;
    end
    initial begin #6000000;$fatal(1,"Active reset watchdog");end
endmodule
'''.replace('TARGET',str(state)).replace('KIND',kind).replace('INTERRUPT',interrupt).replace('RELEASE',release).replace('CHECKS','\n'.join(checks))
        (out/'tb_task_reset_soc.sv').write_text(prefix+helper+dmi+body)
        files=[]
        for line in (ROOT/'rtl/filelist.f').read_text().splitlines():
            if line.startswith('+incdir+'):files.append('+incdir+'+(ROOT/line[8:]).as_posix())
            elif line.strip():files.append((ROOT/line).as_posix())
        files.append((out/'tb_task_reset_soc.sv').as_posix());(out/'soc.f').write_text('\n'.join(files)+'\n')
        commands=['onerror {quit -code 1}','onbreak {resume}']
        commands += ['vmap work ../work','vlog -sv tb_task_reset_soc.sv'] if (run/'work').exists() else ['vlib ../work','vmap work ../work','vlog -sv -f soc.f']
        commands += ['vsim -suppress 12110 -novopt -onfinish stop work.tb_task_reset_soc','run -all','quit -code 0']
        (out/'soc.do').write_text('\n'.join(commands)+'\n')
        execute([args.vsim,'-c','-do','soc.do'],out,'soc','TASK_RESET_SOC PASS')
        results.append(dict(kind=kind,state=state,passed=True))
    for name,digest in sources.items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest,'RTL changed during reset regression: '+name
    (run/'result.json').write_text(json.dumps(dict(passed=True,lut_cache=args.lut_cache,cases=results,rtl_sha256=sources),indent=2)+'\n')
    print('Results: '+str(run))
if __name__=='__main__':main()
