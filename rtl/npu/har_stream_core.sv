// W8A4 continuous scheduler. Same 2x(16x4) FC1 and 1x(6x2) FC2 tiles.
// Runtime mode 0=serialized, 1=II20, 3=adjacent frames (II16).
module har_stream_core(
    input logic clk,rst_ni,start,
    input logic [6:0] sample_count,
    input logic [1:0] mode,
    input logic in_valid,
    output wire in_ready,
    input logic [511:0] in_features,
    input logic [1023:0] bias1,
    input logic [191:0] bias2,
    input logic [15:0] requant_mult,
    input logic [4:0] requant_shift,
    output logic busy,done,
    output logic result_valid,
    output logic [6:0] result_id,
    output logic [255:0] result_hidden,
    output logic [191:0] result_scores,
    output logic [2:0] result_class,
    output logic [31:0] cycles,fc1_issues,fc2_issues,overlap,
    output logic [6:0] accepted,retired,
    output wire w1_re,w2_re,
    output wire [3:0] w1_addr,
    output wire [2:0] w2_addr,
    input logic [1023:0] w1_data,
    input logic [191:0] w2_data
);
    logic [511:0] xb[0:1];
    logic [255:0] hb[0:1],snap[0:1];
    logic [1:0] xv,hv,occupied;
    logic xwr,xrd,hwr,hrd,hcommit;
    logic s1_run,s2_run,s1_hslot;
    logic [3:0] c1,c2;
    logic [6:0] total,launched;
    logic [1:0] mode_q;
    logic [4:0] cooldown;
    logic [1023:0] b1;
    logic [191:0] b2;
    logic [15:0] mult;
    logic [4:0] shift;
    wire launch1=busy && !s1_run && xv[xrd] && (!occupied[hwr] || (s2_run && hrd==hwr)) &&
        (mode_q[0] || launched==retired) && cooldown==0;
    wire launch2=busy && !s2_run && hv[hrd];
    wire [3:0] issue1=launch1 ? 4'd0:c1;
    wire [3:0] issue2=launch2 ? 4'd0:c2;
    assign in_ready=busy && accepted<total && !xv[xwr] && (mode_q[0] || accepted==retired);
    assign w1_re=busy && (s1_run || launch1);
    assign w2_re=busy && (s2_run || launch2);
    assign w1_addr=issue1;
    assign w2_addr=issue2[3:1];
    logic v1,f1,l1,v2,f2,l2,half2;
    logic [31:0] xchunk;
    logic [15:0] hchunk;
    wire [95:0] wchunk;
    wire [511:0] r0,r1;
    wire [191:0] r2;
    wire rv0,rv1,rv2;
    genvar g;
    generate for(g=0;g<6;g=g+1) begin: halves
        assign wchunk[g*16+:16]=w2_data[g*32+half2*16+:16];
    end endgenerate
    har_dot_tile #(.OUTPUTS(16),.LANES(4)) fc1_tile0(
        .clk(clk),.rst_ni(rst_ni),.valid_i(v1),.first_i(f1),.last_i(l1),
        .activation_i(xchunk),.weight_i(w1_data[511:0]),.bias_i(b1[511:0]),.valid_o(rv0),.result_o(r0));
    har_dot_tile #(.OUTPUTS(16),.LANES(4)) fc1_tile1(
        .clk(clk),.rst_ni(rst_ni),.valid_i(v1),.first_i(f1),.last_i(l1),
        .activation_i(xchunk),.weight_i(w1_data[1023:512]),.bias_i(b1[1023:512]),.valid_o(rv1),.result_o(r1));
    har_dot_tile #(.OUTPUTS(6),.LANES(2)) fc2_tile(
        .clk(clk),.rst_ni(rst_ni),.valid_i(v2),.first_i(f2),.last_i(l2),
        .activation_i(hchunk),.weight_i(wchunk),.bias_i(b2),.valid_o(rv2),.result_o(r2));
    function automatic [7:0] quant(input logic signed [31:0] a);
        logic [63:0] value;
        begin
            value=0;
            if(a>0) begin
                value={32'b0,$unsigned(a)}*{48'b0,mult};
                if(shift!=0) value=(value+(64'd1<<(shift-1)))>>shift;
            end
            quant=value>15 ? 8'd15:value[7:0];
        end
    endfunction
    function automatic [2:0] argmax(input logic [191:0] a);
        logic signed [31:0] best;
        integer j;
        begin best=$signed(a[31:0]);argmax=0;
            for(j=1;j<6;j=j+1) if($signed(a[j*32+:32])>best) begin
                best=$signed(a[j*32+:32]);argmax=j;
            end
        end
    endfunction
    integer i;
    always_ff @(posedge clk or negedge rst_ni) begin
        if(!rst_ni) begin
            busy<=0;done<=0;result_valid<=0;result_id<=0;result_hidden<=0;result_scores<=0;result_class<=0;
            cycles<=0;fc1_issues<=0;fc2_issues<=0;overlap<=0;accepted<=0;retired<=0;launched<=0;
            xv<=0;hv<=0;occupied<=0;xwr<=0;xrd<=0;hwr<=0;hrd<=0;hcommit<=0;
            s1_run<=0;s2_run<=0;s1_hslot<=0;c1<=0;c2<=0;cooldown<=0;
            v1<=0;f1<=0;l1<=0;v2<=0;f2<=0;l2<=0;half2<=0;xchunk<=0;hchunk<=0;
            total<=0;mode_q<=0;b1<=0;b2<=0;mult<=0;shift<=0;
        end else begin
            result_valid<=0;
            v1<=w1_re;v2<=w2_re;
            if(w1_re) begin
                xchunk<=xb[xrd][issue1*32+:32];f1<=issue1==0;l1<=issue1==15;
            end
            if(w2_re) begin
                hchunk<=hb[hrd][issue2*16+:16];half2<=issue2[0];f2<=issue2==0;l2<=issue2==15;
            end
            if(start && !busy) begin
                busy<=1;done<=0;cycles<=0;fc1_issues<=0;fc2_issues<=0;overlap<=0;
                accepted<=0;retired<=0;launched<=0;total<=sample_count;mode_q<=mode;
                xv<=0;hv<=0;occupied<=0;xwr<=0;xrd<=0;hwr<=0;hrd<=0;hcommit<=0;
                s1_run<=0;s2_run<=0;c1<=0;c2<=0;cooldown<=0;
                b1<=bias1;b2<=bias2;mult<=requant_mult;shift<=requant_shift;
            end else if(busy) begin
                cycles<=cycles+1'b1;
                if(cooldown!=0) cooldown<=cooldown-1'b1;
                if(in_valid && in_ready) begin
                    xb[xwr]<=in_features;xv[xwr]<=1;xwr<=!xwr;accepted<=accepted+1'b1;
                end
                if(launch1) begin
                    s1_run<=1;c1<=1;s1_hslot<=hwr;hwr<=!hwr;
                    launched<=launched+1'b1;
                    if(mode_q==1) cooldown<=19;
                end else if(w1_re) begin
                    if(c1==15) begin s1_run<=0;xv[xrd]<=0;xrd<=!xrd;end
                    else c1<=c1+1'b1;
                end
                if(rv0 && rv1) begin
                    for(i=0;i<16;i=i+1) begin
                        hb[hcommit][i*8+:8]<=quant($signed(r0[i*32+:32]));
                        hb[hcommit][(i+16)*8+:8]<=quant($signed(r1[i*32+:32]));
                    end
                    hv[hcommit]<=1;occupied[hcommit]<=1;hcommit<=!hcommit;
                end
                if(launch2) begin
                    s2_run<=1;c2<=1;hv[hrd]<=0;snap[hrd]<=hb[hrd];
                end else if(w2_re) begin
                    if(c2==15) begin s2_run<=0;occupied[hrd]<=0;hrd<=!hrd;end
                    else c2<=c2+1'b1;
                end
                if(w1_re) fc1_issues<=fc1_issues+1'b1;
                if(w2_re) fc2_issues<=fc2_issues+1'b1;
                if(w1_re && w2_re) overlap<=overlap+1'b1;
                if(rv2) begin
                    result_valid<=1;result_id<=retired;result_hidden<=snap[retired[0]];
                    result_scores<=r2;result_class<=argmax(r2);retired<=retired+1'b1;
                    if(retired+1==total) begin busy<=0;done<=1;end
                end
            end
        end
    end
endmodule
