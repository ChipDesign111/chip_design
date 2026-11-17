"""Exact RTL requantization against independent wide integer arithmetic."""
import datetime,json,random,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from run import execute

def main():
    run=ROOT/'test/int8/runs'/('task_scale_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S'))
    run.mkdir(parents=True)
    rng=random.Random(96317)
    values=[-(1<<21),-(1<<21)+1,-129,-128,-127,-3,-2,-1,0,1,2,3,126,127,128,(1<<21)-1]
    multipliers=[-(1<<31),-16777217,-65537,-256,-3,-1,0,1,3,255,256,65537,16777217,(1<<31)-1]
    vectors=[(v,m,s) for v in values for m in multipliers for s in range(25)]
    vectors += [(rng.randrange(-(1<<21),1<<21),rng.randrange(-(1<<31),1<<31),rng.randrange(25)) for _ in range(2000)]
    def golden(v,m,s):
        q,r=divmod(v*m,2**s)
        if s and r>=2**(s-1):q+=1
        return max(-128,min(127,q))
    (run/'vectors.hex').write_text(''.join(f'{v&0x3fffff:06x}{m&0xffffffff:08x}{s:02x}{golden(v,m,s)&255:02x}\n' for v,m,s in vectors))
    tb='''module tb_task_scale;
reg clk=0,rst=0,start=0;always #5 clk=~clk;
reg signed [21:0] v=0;reg signed [31:0] m=0;reg [4:0] s=0;
wire busy,done;wire signed [7:0] out;
har_task_scale dut(clk,rst,start,v,m,s,busy,done,out);
reg [71:0] vectors[0:COUNT-1];integer i,t;
initial begin
$readmemh("vectors.hex",vectors);#1;repeat(3) @(negedge clk);rst=1;
for(i=0;i<COUNT;i=i+1) begin
  @(negedge clk);v=vectors[i][69:48];m=vectors[i][47:16];s=vectors[i][12:8];start=1;
  @(negedge clk);start=0;t=0;
  // Change all external inputs while a multiply is active: operands are latched.
  v=22'h1fffff;m=32'hdeadbeef;s=24;
  while(!done && t<10) begin @(negedge clk);t=t+1;end
  if(!done || busy || out!==vectors[i][7:0])
    $fatal(1,"vector %0d got %h expected %h t=%0d",i,out,vectors[i][7:0],t);
end
// Reset during a nontrivial request withdraws completion and pending state.
@(negedge clk);start=1;v=-3;m=3;s=1;
@(negedge clk);start=0;rst=0;@(negedge clk);rst=1;
repeat(8) @(negedge clk);
if(busy || done) $fatal(1,"reset published an old request");
$display("TASK_SCALE PASS vectors=%0d",COUNT);$finish;
end
endmodule
'''.replace('COUNT',str(len(vectors)))
    (run/'tb_task_scale.sv').write_text(tb)
    execute(['iverilog','-g2012','-s','tb_task_scale','-o','scale.vvp',ROOT/'rtl/npu/har_task_scale.sv',run/'tb_task_scale.sv'],run,'compile')
    execute(['vvp','scale.vvp'],run,'simulate','TASK_SCALE PASS')
    (run/'result.json').write_text(json.dumps(dict(passed=True,vectors=len(vectors)),indent=2))
    print('Results: '+str(run))
if __name__=='__main__':main()
