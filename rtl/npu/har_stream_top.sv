// Final W8A4 NPU: packed input staging, continuous compute and batch results.
module har_stream_top(
    input logic clka,rst_ni,ena,wea,
    input logic [11:0] addra,
    input logic [31:0] dina,
    input logic stream_commit_i,stream_abort_i,
    input logic [1:0] stream_commit_count_i,
    output wire busy_o,stream_ready_o,
    output wire [31:0] douta
);
    logic [1023:0] bias1;
    logic [191:0] bias2;
    logic [15:0] mult;
    logic [4:0] shift;
    logic [6:0] count;
    logic error,weight_read_q;
    logic [31:0] read_data,read_q;
    logic [255:0] packet[0:1];
    logic [3:0] packet_index;
    logic [1:0] pending_count;
    logic packet_full,packet_rd;
    logic [2:0] classes[0:63];
    wire write_req=ena && wea;
    wire is_weight=addra>=64 && addra<624;
    wire packet_write=write_req && addra>=896 && addra<912;
    wire config_start=write_req && addra==960 && dina[0] && !busy_o;
    wire start=config_start && count>0 && count<=64;
    wire [255:0] packed_input=packet[packet_rd];
    wire [511:0] expanded;
    wire input_ready;
    wire input_valid=pending_count!=0;
    assign stream_ready_o=busy_o && pending_count==0 && packet_index==0 && !packet_full;
    genvar n;
    generate for(n=0;n<64;n=n+1) begin: unpack
        assign expanded[n*8+:8]={{4{packed_input[n*4+3]}},packed_input[n*4+:4]};
    end endgenerate
    wire [31:0] weight_data;
    wire w1_re,w2_re;
    wire [3:0] w1_addr;
    wire [2:0] w2_addr;
    wire [1023:0] w1_data;
    wire [191:0] w2_data;
    har_weight_store weights(.clk(clka),.rst_ni(rst_ni),
        .cpu_we(write_req && !busy_o && is_weight),.cpu_re(ena && !wea && is_weight),
        .cpu_addr(10'(addra-64)),.cpu_wdata(dina),.cpu_rdata(weight_data),
        .fc1_re(w1_re),.fc1_addr(w1_addr),.fc1_data(w1_data),
        .fc2_re(w2_re),.fc2_addr(w2_addr),.fc2_data(w2_data));
    wire done,result_valid;
    wire [6:0] result_id,accepted,retired;
    wire [255:0] result_hidden;
    wire [191:0] result_scores;
    wire [2:0] result_class;
    wire [31:0] cycles,fc1_issues,fc2_issues,overlap;
    har_stream_core core(.clk(clka),.rst_ni(rst_ni),.start(start),.sample_count(count),
        .in_valid(input_valid),.in_ready(input_ready),.in_features(expanded),
        .bias1(bias1),.bias2(bias2),.requant_mult(mult),.requant_shift(shift),
        .busy(busy_o),.done(done),.result_valid(result_valid),.result_id(result_id),
        .result_hidden(result_hidden),.result_scores(result_scores),.result_class(result_class),
        .cycles(cycles),.fc1_issues(fc1_issues),.fc2_issues(fc2_issues),.overlap(overlap),
        .accepted(accepted),.retired(retired),.w1_re(w1_re),.w1_addr(w1_addr),.w1_data(w1_data),
        .w2_re(w2_re),.w2_addr(w2_addr),.w2_data(w2_data));
    assign douta=weight_read_q ? weight_data:read_q;
    always_ff @(posedge clka or negedge rst_ni) begin
        if(!rst_ni) begin
            bias1<=0;bias2<=0;mult<=1;shift<=0;count<=0;error<=0;
            packet_index<=0;pending_count<=0;packet_full<=0;packet_rd<=0;read_q<=0;weight_read_q<=0;
        end else begin
            read_q<=read_data;weight_read_q<=ena && !wea && is_weight;
            if(result_valid) classes[result_id[5:0]]<=result_class;
            if(config_start) begin error<=!(count>0 && count<=64);packet_index<=0;pending_count<=0;packet_full<=0;packet_rd<=0;end
            if(input_valid && input_ready) begin pending_count<=pending_count-1'b1;packet_rd<=!packet_rd;end
            if(stream_abort_i) begin packet_index<=0;packet_full<=0;error<=1;end
            if(stream_commit_i) begin
                if(pending_count!=0 || stream_commit_count_i==0 || stream_commit_count_i>2 ||
                   (stream_commit_count_i==1 && packet_index!=8) ||
                   (stream_commit_count_i==2 && !packet_full)) error<=1;
                else begin pending_count<=stream_commit_count_i;packet_rd<=0;packet_index<=0;packet_full<=0;end
            end
            if(packet_write) begin
                if(pending_count!=0 || packet_full || addra[3:0]!=packet_index) error<=1;
                else begin
                    packet[packet_index[3]][packet_index[2:0]*32+:32]<=dina;
                    packet_index<=packet_index+1'b1;
                    if(packet_index==15) packet_full<=1;
                end
            end else if(write_req && !config_start) begin
                if(busy_o) error<=1;
                else if(addra==4) begin if(dina[31:16]!=0) error<=1;else mult<=dina[15:0];end
                else if(addra==5) begin if(dina>31) error<=1;else shift<=dina[4:0];end
                else if(addra==962) begin if(dina==0 || dina>64) error<=1;else count<=dina[6:0];end
                else if(addra==963) begin if(dina!=3) error<=1;end
                else if(addra>=624 && addra<656) bias1[(addra-624)*32+:32]<=dina;
                else if(addra>=656 && addra<662) bias2[(addra-656)*32+:32]<=dina;
            end
        end
    end
    always_comb begin
        read_data=0;
        if(ena && !wea) begin
            case(addra)
                1,961:read_data={29'b0,error,busy_o,done};
                4:read_data={16'b0,mult};
                5:read_data={27'b0,shift};
                962:read_data={25'b0,count};
                963:read_data=32'd3;
                964:read_data=cycles;
                965:read_data=fc1_issues;
                966:read_data=fc2_issues;
                967:read_data=overlap;
                968:read_data={25'b0,accepted};
                969:read_data={25'b0,retired};
                default:if(addra>=1024 && addra<1088)
                    read_data=addra-1024<retired ? {29'b0,classes[addra-1024]}:32'd0;
            endcase
        end
    end
endmodule
