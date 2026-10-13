// 2240 bytes: FC1 32 banks x 16 x 32b, FC2 6 banks x 8 x 32b.
// Two synchronous read ports per bank: CPU readback and the relevant engine.
// Memory cells have no reset; resettable validity bits give logical zero reads.
// CPU writes are blocked by the wrapper while either compute stage is active.
module har_weight_store(
    input logic clk,rst_ni,cpu_we,cpu_re,
    input logic [9:0] cpu_addr, // normalized word 0..559
    input logic [31:0] cpu_wdata,
    output wire [31:0] cpu_rdata,
    input logic fc1_re,
    input logic [3:0] fc1_addr,
    output wire [1023:0] fc1_data,
    input logic fc2_re,
    input logic [2:0] fc2_addr,
    output wire [191:0] fc2_data
);
    wire cpu_layer=cpu_addr>=512;
    wire [4:0] cpu_bank1=cpu_addr[8:4];
    wire [2:0] cpu_bank2=cpu_addr[5:3];
    logic layer_q;
    logic [4:0] bank_q;
    wire [1023:0] cpu1;
    wire [191:0] cpu2;
    always_ff @(posedge clk or negedge rst_ni)
        if(!rst_ni) begin layer_q<=0;bank_q<=0;end
        else if(cpu_re) begin layer_q<=cpu_layer;bank_q<=cpu_layer ? {2'b0,cpu_bank2}:cpu_bank1;end
    assign cpu_rdata=layer_q ? cpu2[bank_q*32+:32] : cpu1[bank_q*32+:32];
    genvar b;
    generate for(b=0;b<32;b=b+1) begin: fc1_banks
        logic [31:0] mem [0:15];
        logic [15:0] initialized;
        logic [31:0] cpu_q, engine_q;
        assign cpu1[b*32+:32]=cpu_q;
        assign fc1_data[b*32+:32]=engine_q;
        always_ff @(posedge clk or negedge rst_ni)
            if(!rst_ni) initialized<=0;
            else if(cpu_we && !cpu_layer && cpu_bank1==b) initialized[cpu_addr[3:0]]<=1;
        always_ff @(posedge clk) begin
            if(rst_ni && cpu_we && !cpu_layer && cpu_bank1==b) mem[cpu_addr[3:0]]<=cpu_wdata;
            if(cpu_re && !cpu_layer && cpu_bank1==b)
                cpu_q<=initialized[cpu_addr[3:0]] ? mem[cpu_addr[3:0]]:32'd0;
            if(fc1_re) engine_q<=initialized[fc1_addr] ? mem[fc1_addr]:32'd0;
        end
    end
    for(b=0;b<6;b=b+1) begin: fc2_banks
        logic [31:0] mem [0:7];
        logic [7:0] initialized;
        logic [31:0] cpu_q,engine_q;
        assign cpu2[b*32+:32]=cpu_q;
        assign fc2_data[b*32+:32]=engine_q;
        always_ff @(posedge clk or negedge rst_ni)
            if(!rst_ni) initialized<=0;
            else if(cpu_we && cpu_layer && cpu_bank2==b) initialized[cpu_addr[2:0]]<=1;
        always_ff @(posedge clk) begin
            if(rst_ni && cpu_we && cpu_layer && cpu_bank2==b) mem[cpu_addr[2:0]]<=cpu_wdata;
            if(cpu_re && cpu_layer && cpu_bank2==b)
                cpu_q<=initialized[cpu_addr[2:0]] ? mem[cpu_addr[2:0]]:32'd0;
            if(fc2_re) engine_q<=initialized[fc2_addr] ? mem[fc2_addr]:32'd0;
        end
    end endgenerate
endmodule
