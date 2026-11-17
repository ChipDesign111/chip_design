"""Passive RTL timing and traffic accounting. No firmware instrumentation."""
import collections
import csv
import json
from pathlib import Path


def monitor_source():
    return r'''
    integer profile_fd,profile_tick=0;
    reg profile_active=0,profile_finished=0;
    initial begin
        profile_fd=$fopen("profile.csv","w");
        if(profile_fd==0) $fatal(1,"Cannot open passive profile");
        $fdisplay(profile_fd,"tick,pc,busy,state,tile_ready,dma_busy,dma_r,dma_w,cpu_accept,cpu_we,cpu_addr,cpu_be,mem_req,mem_we,mem_addr,mem_be,start,k,n,batch,issued,dma_wait");
    end
    always @(posedge clk) begin
        profile_tick=profile_tick+1;
        if(dut.ndmreset_n===1'b1 && dut.boot_ready===1'b1 && dut.firmware_fetch_start)
            profile_active=1;
        if(profile_active && !profile_finished) begin
            $fdisplay(profile_fd,"%0d,%h,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%h,%h,%0d,%0d,%h,%h,%0d,%0d,%0d,%0d,%0d,%0d",
                profile_tick,dut.i_cpu.core_i.pc_id,
                dut.i_npu_subsystem.i_npu_core.core.busy,
                dut.i_npu_subsystem.i_npu_core.core.state,
                dut.i_npu_subsystem.i_npu_core.core.tile_valid_i,
                dut.dma_busy,dut.dma_read_active,dut.dma_write_active,
                dut.data_req && dut.data_gnt,dut.data_we,dut.data_addr,dut.data_be,
                dut.sram_req,dut.sram_we,dut.sram_addr,dut.sram_be,
                dut.i_npu_subsystem.i_npu_core.start,
                dut.i_npu_subsystem.i_npu_core.fc_k,
                dut.i_npu_subsystem.i_npu_core.fc_n,
                dut.i_npu_subsystem.i_npu_core.batch_count,
                dut.i_cpu.core_i.id_valid && dut.i_cpu.core_i.is_decoding,
                {dut.i_dma.i_engine.b_ready_o && !dut.i_dma.i_engine.b_valid_i,
                 dut.i_dma.i_engine.w_valid_o && !dut.i_dma.i_engine.w_ready_i,
                 dut.i_dma.i_engine.aw_valid_o && !dut.i_dma.i_engine.aw_ready_i,
                 dut.i_dma.i_engine.r_ready_o && !dut.i_dma.i_engine.r_valid_i,
                 dut.i_dma.i_engine.ar_valid_o && !dut.i_dma.i_engine.ar_ready_i});
            if(dut.sram_req && dut.sram_we && dut.sram_addr==32'h80001fe0 &&
               dut.sram_wdata==32'hc0dec0de) begin
                profile_finished=1;$fclose(profile_fd);
            end
        end
    end
'''


def summarize(directory,output_name='profile.json'):
    directory=Path(directory)
    meta=json.loads((directory/'manifest.json').read_text())
    stages=collections.Counter();nodes=collections.Counter();states=collections.Counter()
    traffic=collections.Counter();tensor=collections.defaultdict(collections.Counter)
    exclusive=collections.Counter();node_stages=collections.defaultdict(collections.Counter)
    instructions=collections.Counter();last_pc=-1
    dma=collections.Counter()
    jobs=[];current=None;first=None;last=None
    regions=[]
    for name,t in meta['tensors'].items():
        for row in range(t['shape'][0]):
            begin=t['address']+row*t['stride']
            regions.append((begin,begin+t['shape'][1],name))
    def tensor_byte(address,kind):
        for begin,end,name in regions:
            if begin<=address<end:tensor[name][kind]+=1
    def tensor_transaction(address,mask,kind):
        touched=set()
        for begin,end,name in regions:
            if any(mask>>i&1 and begin<=address+i<end for i in range(4)):touched.add(name)
        for name in touched:tensor[name][kind]+=1
    with (directory/'profile.csv').open() as stream:
        for row in csv.DictReader(stream):
            tick=int(row['tick']);first=tick if first is None else first;last=tick
            if int(row['issued']):
                last_pc=int(row['pc'],16)
            pc=last_pc
            match=next((p for p in meta['profile_ranges'] if p['start_pc']<=pc<p['end_pc']),None)
            phase=match['phase'] if match else 'boot_or_pipeline';node=match['node'] if match else 'runtime'
            wait=int(row['dma_wait'])
            dma['busy_cycles']+=int(row['dma_busy'])
            for bit,name in enumerate(['ar_backpressure','r_data_unavailable','aw_backpressure','w_backpressure','b_response_unavailable']):
                dma[name]+=int(bool(wait>>bit&1))
            stages[phase]+=1;nodes[node]+=1;node_stages[node][phase]+=1
            if int(row['issued']):instructions[phase]+=1
            if int(row['start']):
                current=dict(start_tick=tick,k=int(row['k']),n=int(row['n']),batch=int(row['batch']),busy_cycles=0,states=collections.Counter())
                jobs.append(current)
            if int(row['busy']):
                state=int(row['state'])
                label={0:'idle',1:'wait_weight' if row['tile_ready']=='0' else 'tile_ready_control',2:'issue',3:'quant_drain',4:'quant',5:'finish_argmax'}.get(state,'unknown')
                states[label]+=1
                if label=='wait_weight':
                    dma['weight_unready_dma_busy' if row['dma_busy']=='1' else 'weight_unready_dma_idle']+=1
                    dma['weight_unready_with_r_data_unavailable']+=int(bool(wait&2))
                if current:
                    current['busy_cycles']+=1;current['states'][label]+=1
                exclusive['npu_'+label]+=1
            else:
                exclusive[phase]+=1
            traffic['dma_weight_read_bytes']+=4*int(row['dma_r'])
            traffic['dma_weight_NPU_write_bytes']+=4*int(row['dma_w'])
            if int(row['cpu_accept']):
                address=int(row['cpu_addr'],16)&~3;mask=int(row['cpu_be'],16);writing=int(row['cpu_we'])
                kind='cpu_write_bytes' if writing else 'cpu_read_bytes'
                group='sram' if 0x80000000<=address<0x80002000 else 'npu_mmio' if 0x70000000<=address<0x70002000 else 'other_mmio'
                traffic[group+'_'+kind]+=mask.bit_count()
                traffic[group+('_stores' if writing else '_loads')]+=1
                for i in range(4):
                    if mask>>i&1:tensor_byte(address+i,kind)
                tensor_transaction(address,mask,'cpu_write_transactions' if writing else 'cpu_read_transactions')
            if int(row['mem_req']):
                address=int(row['mem_addr'],16)&~3;writing=int(row['mem_we'])
                mask=int(row['mem_be'],16) if writing else 15
                traffic['sram_port_write_bytes' if writing else 'sram_port_read_bytes']+=mask.bit_count()
                for i in range(4):
                    if mask>>i&1:tensor_byte(address+i,'macro_write_bytes' if writing else 'macro_read_bytes')
                tensor_transaction(address,mask,'macro_write_commands' if writing else 'macro_read_commands')
    assert first is not None and last-first+1==sum(stages.values())
    assert sum(exclusive.values())==sum(stages.values())
    assert sum(states.values())==sum(j['busy_cycles'] for j in jobs)
    result=dict(cpu_stage_occupancy_cycles=dict(stages),cpu_node_occupancy_cycles=dict(nodes),
        exclusive_wall_cycles=dict(exclusive),cpu_node_stage_cycles=dict(node_stages),
        issued_instruction_events=dict(instructions),
        dma_handshake_cycles=dict(dma),
        observed_edges=last-first+1,elapsed_edge_difference=last-first,npu_state_cycles=dict(states),jobs=jobs,
        traffic=dict(traffic),tensor_traffic=dict(tensor),rules={
        'cpu_cycles':'Phase of most recently accepted ID instruction (id_valid && is_decoding); hold across bubbles/stalls. No speculative invalid-ID PC attribution. Wall-time boundary convention, not causal stall attribution.',
        'npu_cycles':'Busy-edge state occupancy is a separate overlapping view; never add to CPU stage cycles',
        'exclusive':'Every edge attributed to NPU state while busy, otherwise most recent accepted CPU instruction phase; sums exactly to hardware elapsed count. Accounting convention, not a CPU stall-cause proof.',
        'wait_weight':'WAIT_TILE with tile_valid=0 only; other idle states are not DMA wait',
        'traffic':'CPU LSU accepted byte enables and physical SRAM command reads/writes are distinct levels, not additive. SRAM reads are full32-bit accesses, including replay and instruction fetch. DMA reads counted at real R handshake.',
        'tensor':'Logical tensor byte intervals exclude stride padding; macro_read_bytes also include repeated physical reads. Loader and post-completion SBA checks excluded.'})
    (directory/output_name).write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    return result
