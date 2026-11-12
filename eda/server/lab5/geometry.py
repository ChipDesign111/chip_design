"""Assemble native seal-ring references and a measured POC label in private GDS.

No cell flattening, scaling, connectivity shortcuts or changes to shared models.
Uses the course native 1um edge/corner masters. Full Calibre checks still required.
"""
import argparse
import gzip
import json
import math
from pathlib import Path
import tempfile
import zipfile
import gdstk


def assemble(source, output, ring_zip, evidence):
    with tempfile.TemporaryDirectory() as temp:
        original = Path(temp)/'original.gds'
        with gzip.open(source, 'rb') as f:
            original.write_bytes(f.read())
        lib = gdstk.read_gds(str(original))
        ring_file = Path(temp)/'sealring.gds'
        with zipfile.ZipFile(ring_zip) as z:
            ring_file.write_bytes(z.read('tsmc_c018_sealring_1p6m.gds'))
        ring_lib = gdstk.read_gds(str(ring_file), unit=lib.unit)
    top = next(c for c in lib.cells if c.name == 'my_soc_top')
    original_counts = {c.name: [len(c.polygons),len(c.paths),len(c.labels),len(c.references)] for c in lib.cells}
    # DIEAREA from DEF, not the polygon/instance text bounding box.
    import re
    text = source.with_name('my_soc_top.def').read_text()
    dbu = float(re.search(r'UNITS DISTANCE MICRONS\s+(\d+)',text).group(1))
    coords = [int(x) / dbu for x in re.search(r'DIEAREA\s+\(\s*(-?\d+)\s+(-?\d+)\s*\)\s+\(\s*(-?\d+)\s+(-?\d+)\s*\)',text).groups()]
    x0,y0,x1,y1 = coords
    if x0 != 0 or y0 != 0 or abs(x1-y1)>0.001 or x1>1950:
        raise ValueError('Unsupported/non-square DIEAREA; geometry requires explicit adaptation')
    size = math.ceil(x1)
    if size + 30 > 1980:
        raise ValueError('Final sealring exceeds course 1980um limit')
    ring = next(c for c in ring_lib.cells if c.name == 'tsmc_c018_sealring_1p6m')
    if ring.bounding_box() != ((-15.0,-15.0),(1875.0,2005.0)):
        raise ValueError('Native sealring differs from measured course reference')
    native_edge = next(c for c in ring_lib.cells if c.name == 'tsmc_c018_seal_ring_edge_1p6m')
    native_corner = next(c for c in ring_lib.cells if c.name == 'tsmc_c018_sealring_corner_1p6m')
    new_ring = gdstk.Cell('sealring_my_soc_top')
    # Native source has -5..boundary+4 at 1um cadence, same corner orientations.
    for k in range(-5,size+5):
        new_ring.add(gdstk.Reference(native_edge,(k,0),x_reflection=True),
                     gdstk.Reference(native_edge,(k,size)),
                     gdstk.Reference(native_edge,(0,k),rotation=math.pi/2),
                     gdstk.Reference(native_edge,(size,k),rotation=math.pi/2,x_reflection=True))
    for xy,rot,reflect in [((-15,-15),0,False),((size+15,-15),math.pi/2,False),
                           ((-15,size+15),0,True),((size+15,size+15),3*math.pi/2,True)]:
        new_ring.add(gdstk.Reference(native_corner,xy,rotation=rot,x_reflection=reflect))
    # Retain native boundary LPP; no scaling of physical master geometry.
    if len(ring.polygons)!=1:
        raise ValueError('Unexpected reference boundary count')
    boundary = ring.polygons[0]
    new_ring.add(gdstk.rectangle((0,0),(size,size),layer=boundary.layer,datatype=boundary.datatype))
    present = {c.name for c in lib.cells}
    deps = [c for c in new_ring.dependencies(True) if c.name not in present]
    lib.add(*deps,new_ring)
    offset = (x1-size)/2
    top.add(gdstk.Reference(new_ring,(offset,offset)))
    # Actual bottom PVDD2CDG reference is located from its transformation.
    candidates = [r for r in top.references if r.cell_name=='PVDD2CDG' and abs(r.origin[1])<0.001 and not r.x_reflection and abs(r.rotation or 0)<1e-9]
    if not candidates:
        raise ValueError('No native bottom PVDD2CDG; cannot infer POC location')
    ref = sorted(candidates,key=lambda r:r.origin[0])[0]
    point=(ref.origin[0]+30,ref.origin[1]+113.215)
    polygons = ref.get_polygons(layer=28,datatype=0)
    if not gdstk.inside([point],polygons)[0]:
        raise ValueError('Measured POC anchor not inside native METAL3')
    top.add(gdstk.Label('POC',point,layer=42,texttype=0))
    bbox=new_ring.bounding_box()
    actual = ((bbox[0][0]+offset,bbox[0][1]+offset),(bbox[1][0]+offset,bbox[1][1]+offset))
    if abs((actual[1][0]-actual[0][0])-(size+30))>0.001:
        raise ValueError('Unexpected sealring bbox')
    for c in lib.cells:
        if c.name in original_counts and c.name!='my_soc_top':
            if original_counts[c.name]!=[len(c.polygons),len(c.paths),len(c.labels),len(c.references)]:
                raise ValueError('Native original cell changed: '+c.name)
    lib.write_gds(str(output))
    evidence.write_text(json.dumps({'gdstk':gdstk.__version__,'unit_m':lib.unit,'precision_m':lib.precision,
        'die_um':coords,'ring_reference_um':size,'ring_external_bbox_um':actual,
        'ring_external_size_um':size+30,'ring_edges':4*(size+10),'ring_corners':4,
        'poc_master':ref.cell_name,'poc_instance_origin_um':ref.origin,'poc_anchor_um':point,
        'original_subcell_element_counts_unchanged':True,
        'method':'Native GDS cell assembly; no scaling or flattening. Native OA import and Calibre required.'},indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('output',type=Path)
    p.add_argument('ring_zip',type=Path);p.add_argument('evidence',type=Path)
    a=p.parse_args();assemble(a.source,a.output,a.ring_zip,a.evidence)
