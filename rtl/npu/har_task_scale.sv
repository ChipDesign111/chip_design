// Exact signed INT22 x INT32 scaling with one small 22x9 multiplier.
// Four byte products and a separate rounding boundary keep the wide multiply
// out of the existing MAC/legacy quantizer paths. One request at a time.
module har_task_scale (
    input logic clk_i,rst_ni,start_i,
    input logic signed [21:0] value_i,
    input logic signed [31:0] multiplier_i,
    input logic [4:0] shift_i,
    output logic busy_o,done_o,
    output logic signed [7:0] value_o
);
    logic signed [21:0] value_q;
    logic signed [31:0] multiplier_q;
    logic [4:0] shift_q;
    logic [1:0] index_q;
    logic rounding_q;
    logic signed [53:0] sum_q;
    wire [7:0] coefficient_byte=multiplier_q[index_q*8+:8];
    wire signed [8:0] coefficient={index_q==3 && multiplier_q[31],coefficient_byte};
    wire signed [30:0] product=value_q*coefficient;
    wire signed [53:0] extended_product={{23{product[30]}},product};
    wire signed [53:0] contribution=extended_product<<<(index_q*8);
    wire signed [53:0] rounded=shift_q==0 ? sum_q :
        (sum_q+(54'sd1<<<(shift_q-1)))>>>shift_q;
    function automatic [7:0] saturate(input logic signed [53:0] v);
        if(v>54'sd127) saturate=8'd127;
        else if(v< -54'sd128) saturate=8'h80;
        else saturate=v[7:0];
    endfunction
    always_ff @(posedge clk_i or negedge rst_ni) begin
        if(!rst_ni) begin
            busy_o<=0;done_o<=0;value_o<=0;value_q<=0;multiplier_q<=0;
            shift_q<=0;index_q<=0;rounding_q<=0;sum_q<=0;
        end else begin
            done_o<=0;
            if(start_i && !busy_o) begin
                if(multiplier_i==1 && shift_i==0) begin
                    value_o<=saturate({{32{value_i[21]}},value_i});done_o<=1;
                end else begin
                    value_q<=value_i;multiplier_q<=multiplier_i;shift_q<=shift_i;
                    index_q<=0;sum_q<=0;rounding_q<=0;busy_o<=1;
                end
            end else if(busy_o) begin
                if(rounding_q) begin
                    value_o<=saturate(rounded);busy_o<=0;done_o<=1;rounding_q<=0;
                end else begin
                    sum_q<=sum_q+contribution;
                    if(index_q==3) rounding_q<=1;
                    else index_q<=index_q+1'b1;
                end
            end
        end
    end
endmodule
