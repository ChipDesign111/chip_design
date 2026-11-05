"""Compare every original top-level signal endpoint after PAD insertion, including aliases."""
from pathlib import Path
import json
import re
import sys

def parse(path):
    text = path.read_text()
    text = re.sub(r'/\*.*?\*/|//[^\n]*', '', text, flags=re.S)
    m = re.search(r'\bmodule\s+my_soc_top\b(.*?)\bendmodule\b', text, re.S)
    assert m, 'Missing top module'
    body = m.group(1)
    parents = {}
    def find(x):
        if x not in parents:
            parents[x] = x
        if parents[x] != x:
            parents[x] = find(parents[x])
        return parents[x]
    for a, b in re.findall(r'\bassign\s+([^\s=]+)\s*=\s*([^;]+);', body):
        b = b.strip()
        if re.fullmatch(r'[\w$\[\]\\/.]+', a) and re.fullmatch(r'[\w$\[\]\\/.]+', b):
            parents[find(a)] = find(b)
    insts = {}
    for m in re.finditer(r'\b([A-Za-z_]\w*)\s+(\\?[^\s(]+)\s*\((.*?)\)\s*;', body, re.S):
        pins = dict(re.findall(r'\.([A-Za-z_]\w*)\s*\(([^()]*)\)', m.group(3)))
        if pins:
            insts[m.group(2)] = {p:n.strip() for p,n in pins.items()}
    return find, insts

root = Path.cwd()
old_find, old = parse(root / 'syn/my_soc_top/my_soc_top_postsyn.v')
new_path = Path(sys.argv[1]) if len(sys.argv) > 1 else root / 'pnr/my_soc_top/my_soc_top_io_connected.v'
new_find, new = parse(new_path)
mapping = [('clk_i','i_pad_clk','C'),('rst_ni','i_pad_rst_n','C'),
           ('tck_i','i_pad_tck','C'),('tms_i','i_pad_tms','C'),
           ('td_i','i_pad_tdi','C'),('td_o','i_pad_tdo','I')]
results = []
for port, pad, core_pin in mapping:
    assert new[pad]['PAD'] == port, (port, new[pad])
    core = new[pad][core_pin]
    assert new_find(core) != new_find(port), port
    expected = {(i,p) for i,pins in old.items() for p,n in pins.items() if old_find(n)==old_find(port)}
    actual = {(i,p) for i,pins in new.items() if not i.startswith('i_pad_') for p,n in pins.items() if new_find(n)==new_find(core)}
    assert expected == actual, (port, sorted(expected-actual), sorted(actual-expected))
    external = {(i,p) for i,pins in new.items() for p,n in pins.items() if new_find(n)==new_find(port)}
    assert external == {(pad,'PAD')}, (port, external)
    control = {'OEN':"1'b0",'IE':"1'b0",'PE':"1'b0",'DS':"1'b0"}
    if core_pin == 'C':
        control.update({'OEN':"1'b1",'IE':"1'b1",'I':"1'b0"})
    for pin, val in control.items():
        assert new[pad][pin] == val, (pad,pin,new[pad][pin])
    results.append({'port':port,'pad':pad,'core_net':core,'original_endpoints':sorted(expected),
                    'all_original_endpoints_preserved':True,'external_pad_only':True,
                    'controls':control})
if len(sys.argv) > 1:
    assert len({new_find(n) for n in ['VDD','VSS','VDDPST','VSSPST']}) == 4, 'Supply nets merged'
    powers = []
    for side in ['N','S','W','E']:
        for suffix, supply in [('vss_1','VSS'),('vss_2','VSS'),('vssio','VSSPST'),
                               ('vdd_1','VDD'),('vdd_2','VDD'),('vddio','VDDPST'),('poc','VDDPST')]:
            inst = 'i_pad_' + side + '_' + suffix
            assert new[inst][supply] == supply, (inst,new[inst])
            powers.append({'instance':inst,'supply':supply})
    (root / 'evidence/11_pg_topology.json').write_text(json.dumps({'signals':results,'power_pads':powers,'four_nets_independent':True},indent=2))
else:
    (root / 'evidence/08_topology.json').write_text(json.dumps(results,indent=2))
print(json.dumps([{'port':r['port'],'core_net':r['core_net'],'endpoints':len(r['original_endpoints'])} for r in results]))
