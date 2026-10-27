"""Audit IO controls and four independent supplies after Tie insertion/optimization."""
from pathlib import Path
import json
import re
import sys
root = Path.cwd()
path = Path(sys.argv[1]) if len(sys.argv)>1 else root/'pnr/my_soc_top/my_soc_top_postTie.v'
text = re.sub(r'/\*.*?\*/|//[^\n]*','',path.read_text(),flags=re.S)
body = re.search(r'\bmodule\s+my_soc_top\s*\(.*?\);(.*?)\bendmodule\b',text,re.S).group(1)
parent = {}
def find(n):
    n = n.strip().lstrip('\\')
    parent.setdefault(n,n)
    if parent[n] != n:
        parent[n] = find(parent[n])
    return parent[n]
for a,b in re.findall(r'\bassign\s+([^\s=]+)\s*=\s*([^;]+);',body):
    if re.fullmatch(r'[\w$\[\]\\/.]+',b.strip()):
        parent[find(a)] = find(b)
insts = {}
for m in re.finditer(r'\b([A-Za-z_]\w*)\s+(\\?[^\s(]+)\s*\((.*?)\)\s*;',body,re.S):
    pins = dict(re.findall(r'\.([A-Za-z_]\w*)\s*\(([^()]*)\)',m.group(3)))
    if pins:
        insts[m.group(2).lstrip('\\')] = (m.group(1), {p:n.strip() for p,n in pins.items()})
supplies = {find(n) for n in ['VDD','VSS','VDDPST','VSSPST']}
assert len(supplies)==4, 'Supply nets merged'
ties = {}
for inst,(master,pins) in insts.items():
    if master in ['TIEHBWP7T','TIELBWP7T']:
        net = find(pins['Z' if master=='TIEHBWP7T' else 'ZN'])
        assert net not in supplies, (inst,net)
        ties[net] = 1 if master=='TIEHBWP7T' else 0
powerpads = []
for side in 'NSWE':
    for suffix,supply in [('vss_1','VSS'),('vss_2','VSS'),('vssio','VSSPST'),('vdd_1','VDD'),('vdd_2','VDD'),('vddio','VDDPST'),('poc','VDDPST')]:
        inst='i_pad_'+side+'_'+suffix
        assert find(insts[inst][1][supply])==find(supply), (inst,insts[inst])
        powerpads.append({'instance':inst,'supply':supply})
signals=[]
plan=json.loads((root/'config/io_plan.json').read_text())
expected_masters={signal['port']:signal['master'] for signal in plan['signals']}
for port,pad,core in [('clk_i','clk','C'),('rst_ni','rst_n','C'),('tck_i','tck','C'),('tms_i','tms','C'),('td_i','tdi','C'),('td_o','tdo','I')]:
    inst='i_pad_'+pad
    assert insts[inst][0]==expected_masters[port], (inst,insts[inst][0],expected_masters[port])
    pins=insts[inst][1]
    assert find(pins['PAD'])==find(port)
    assert find(pins[core])!=find(port)
    controls={'OEN':0,'IE':0,'PE':0,'DS':0}
    if core=='C': controls.update(OEN=1,IE=1,I=0)
    for pin,value in controls.items():
        assert ties.get(find(pins[pin]))==value, (inst,pin,pins[pin],value)
    endpoints={(i,p) for i,(_,ps) in insts.items() for p,n in ps.items() if find(n)==find(port)}
    assert endpoints=={(inst,'PAD')}, (port,endpoints)
    signals.append({'port':port,'pad':inst,'core_net':pins[core],'controls':controls,'external_port_only_connects_to_pad':True})
result={'netlist':str(path),'four_supplies_independent':True,'no_top_tie_output_on_supply':True,'all_12_ordinary_io_supply_pins_preserved':True,'power_pads':powerpads,'signals':signals}
target=root/'evidence'/('final_io_ties.json' if 'manual_final' in str(path) else '25_io_ties.json')
target.write_text(json.dumps(result,indent=2))
print(json.dumps({k:v for k,v in result.items() if k not in ['signals','power_pads']},indent=2))
