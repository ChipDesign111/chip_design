"""Check native IO M4 rail cross-sections from the parsed foundry GDS geometry."""
from pathlib import Path
import json

root = Path.cwd()
data = json.loads((root / 'evidence/native_io_gds.json').read_text())
scale = data['dbu_um']
widths = {'PDDW0204CDG':60, 'PDDW1216CDG':60, 'PVDD1CDG':60, 'PVSS1CDG':60,
          'PVDD2CDG':60, 'PVSS2CDG':60, 'PVDD2POC':60,
          'PFILLER20':20, 'PFILLER10':10, 'PFILLER5':5,
          'PFILLER1':1, 'PFILLER05':0.5, 'PFILLER0005':0.005}
levels = {'VSSPST':20.95,'VDDPST':63.92,'VSS':90.435}

def intersections(shape, y):
    q = shape['xy']
    pts = [(x*scale,v*scale) for x,v in zip(q[::2],q[1::2])]
    xs = []
    for (x0,y0),(x1,y1) in zip(pts,pts[1:]+pts[:1]):
        if (y0 <= y < y1) or (y1 <= y < y0):
            xs.append(x0+(y-y0)*(x1-x0)/(y1-y0))
    xs.sort()
    return list(zip(xs[::2],xs[1::2]))

results = []
for name, width in widths.items():
    shapes = [e for e in data['selected_native_m4_geometry'][name]
              if e['kind']==8 and e.get('layer')==31 and e.get('datatype')==0]
    for net, y in levels.items():
        spans = sorted(s for e in shapes for s in intersections(e,y))
        end = 0.0
        for a,b in spans:
            if a <= end+1e-6:
                end = max(end,b)
        assert end >= width-1e-6, (name,net,end,width)
        results.append({'master':name,'net':net,'local_y_um':y,
                        'continuous_x_um':[0,width]})
corner = [e for e in data['selected_native_m4_geometry']['PCORNER']
          if e['kind']==8 and e.get('layer')==31 and e.get('datatype')==0]
for net,y in levels.items():
    def contains(shape,x,y0):
        return any(a-1e-6<=x<=b+1e-6 for a,b in intersections(shape,y0))
    assert any(contains(e,114.995,y) and contains(e,y,114.995) for e in corner), net
report = {'native_gds':data['file'],'gds_m4_conductor_layer':31,'gds_m4_pin_label_layer':43,
          'straight_master_count':len(widths),'rail_cross_sections':results,
          'PCORNER_turns_connected_for':list(levels),
          'scope':'Native per-master rail cross-sections and corner turns. Combine with actual placement continuity/orientations; not independent merged-chip LVS/IR/EM/ESD.'}
(root / 'evidence/native_io_rails_check.json').write_text(json.dumps(report,indent=2))
print('Native M4 rail continuity passed for',len(widths),'straight masters and PCORNER turns.')
