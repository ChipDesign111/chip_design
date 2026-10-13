// Fixed Lab 3 external interface. V1 windows preserved; V2 batch extension.
module simple_npu_top (
    input logic clka,rst_ni,ena,wea,
    input logic [11:0] addra,
    input logic [31:0] dina,
    output wire [31:0] douta
);
    logic [511:0] input_features,input_features1;
    logic [1023:0] bias1;
    logic [191:0] bias2;
    logic [15:0] requant_mult;
    logic [4:0] requant_shift;
    logic [1:0] batch_count;
    wire [255:0] hidden,hidden1;
    wire [191:0] scores,scores1;
    wire [2:0] class_id,class_id1;
    wire [31:0] cycle_count,overlap_count,fc1_cycles,fc2_cycles;
    wire busy,done;
    logic error,weight_read_q;
    logic [31:0] read_data,read_q;
    wire write_request=ena && wea;
    wire is_weight=addra>=64 && addra<624;
    wire [31:0] weight_cpu_data;
    wire w1_re,w2_re;
    wire [3:0] w1_addr;
    wire [2:0] w2_addr;
    wire [1023:0] w1_data;
    wire [191:0] w2_data;
    assign douta=weight_read_q ? weight_cpu_data:read_q;
    har_weight_store weights(
        .clk(clka),.rst_ni(rst_ni),
        .cpu_we(write_request && !busy && is_weight),
        .cpu_re(ena && !wea && is_weight),
        .cpu_addr(10'(addra-64)),.cpu_wdata(dina),.cpu_rdata(weight_cpu_data),
        .fc1_re(w1_re),.fc1_addr(w1_addr),.fc1_data(w1_data),
        .fc2_re(w2_re),.fc2_addr(w2_addr),.fc2_data(w2_data));
    har_npu_core core(
        .clk(clka),.rst_ni(rst_ni),.start(write_request && addra==0 && dina[0] && !busy),
        .ack_done(write_request && addra==0 && dina[1] && !busy),.batch_two(batch_count==2),
        .input_features(input_features),.input_features1(input_features1),.bias1(bias1),.bias2(bias2),
        .requant_mult(requant_mult),.requant_shift(requant_shift),
        .busy(busy),.done(done),.hidden(hidden),.hidden1(hidden1),.scores(scores),.scores1(scores1),
        .class_id(class_id),.class_id1(class_id1),.cycle_count(cycle_count),
        .overlap_count(overlap_count),.fc1_cycles(fc1_cycles),.fc2_cycles(fc2_cycles),
        .w1_re(w1_re),.w1_addr(w1_addr),.w1_data(w1_data),
        .w2_re(w2_re),.w2_addr(w2_addr),.w2_data(w2_data));
    always_ff @(posedge clka or negedge rst_ni) begin
        if(!rst_ni) begin
            input_features<=0;input_features1<=0;bias1<=0;bias2<=0;
            requant_mult<=1;requant_shift<=0;batch_count<=1;error<=0;read_q<=0;weight_read_q<=0;
        end else begin
            read_q<=read_data;weight_read_q<=ena && !wea && is_weight;
            if(write_request) begin
                if(busy) error<=1;
                else if(addra==0) begin if(dina[0] || dina[1]) error<=0;end
                else if(addra==4) begin if(dina[31:16]!=0) error<=1;else requant_mult<=dina[15:0];end
                else if(addra==5) begin if(dina>31) error<=1;else requant_shift<=dina[4:0];end
                else if(addra==6) begin if(dina!=1 && dina!=2) error<=1;else batch_count<=dina[1:0];end
                else if(addra>=16 && addra<32) input_features[(addra-16)*32+:32]<=dina;
                else if(addra>=624 && addra<656) bias1[(addra-624)*32+:32]<=dina;
                else if(addra>=656 && addra<662) bias2[(addra-656)*32+:32]<=dina;
                else if(addra>=768 && addra<784) input_features1[(addra-768)*32+:32]<=dina;
            end
        end
    end
    always_comb begin
        read_data=0;
        if(ena && !wea) begin
            case(addra)
                1:read_data={29'b0,error,busy,done};
                2:read_data={29'b0,class_id};
                3:read_data=cycle_count;
                4:read_data={16'b0,requant_mult};
                5:read_data={27'b0,requant_shift};
                6:read_data={30'b0,batch_count};
                7:read_data=overlap_count;
                8:read_data=fc1_cycles;
                9:read_data=fc2_cycles;
                806:read_data={29'b0,class_id1};
                default:begin
                    if(addra>=16 && addra<32) read_data=input_features[(addra-16)*32+:32];
                    else if(addra>=624 && addra<656) read_data=bias1[(addra-624)*32+:32];
                    else if(addra>=656 && addra<662) read_data=bias2[(addra-656)*32+:32];
                    else if(addra>=672 && addra<680) read_data=hidden[(addra-672)*32+:32];
                    else if(addra>=704 && addra<710) read_data=scores[(addra-704)*32+:32];
                    else if(addra>=768 && addra<784) read_data=input_features1[(addra-768)*32+:32];
                    else if(addra>=784 && addra<792) read_data=hidden1[(addra-784)*32+:32];
                    else if(addra>=800 && addra<806) read_data=scores1[(addra-800)*32+:32];
                end
            endcase
        end
    end
endmodule
