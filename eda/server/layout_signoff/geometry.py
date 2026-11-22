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


def assemble(source, output, ring_zip, evidence, patch_io=False,
             outer_side_um=1980.0, inner_gap_um=5.0):
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
    changes=[]
    if patch_io:
        # Native CO.R.4 marker measured on b54663c, same physical source.
        # 3b928b8 identified the remaining four instances as PVDD2POC.
        for master in ['PVDD2CDG','PVDD2POC']:
            cell=next(c for c in lib.cells if c.name==master)
            pp=[p for p in cell.get_polygons(layer=7,datatype=0) if all(abs(a-b)<1e-6 for a,b in zip(sum(p.bounding_box(),()),(2.7,52.91,57.3,73.795)))]
            co=[p for p in cell.get_polygons(layer=15,datatype=0) if all(abs(a-b)<1e-6 for a,b in zip(sum(p.bounding_box(),()),(57.23,72.13,57.45,72.35)))]
            npoly=cell.get_polygons(layer=8,datatype=0)
            if len(pp)!=1 or len(co)!=1 or not any(any(abs(x-57.59)<1e-6 and abs(y-73.795)<1e-6 for x,y in p.points) for p in npoly):
                raise ValueError('Private IO patch does not match measured PP/CO/NP geometry: '+master)
            cell.add(gdstk.rectangle((57.3,52.91),(57.59,73.795),layer=7,datatype=0))
            changes.append({'cell':master,'layer':7,'datatype':0,'added_rect_um':[[57.3,52.91],[57.59,73.795]],'reason':'Measured CO.R.4; PP extends to existing NP boundary; shared PDK unchanged'})
    # DIEAREA from DEF, not the polygon/instance text bounding box.
    import re
    text = source.with_name('my_soc_top.def').read_text()
    dbu = float(re.search(r'UNITS DISTANCE MICRONS\s+(\d+)',text).group(1))
    coords = [int(x) / dbu for x in re.search(r'DIEAREA\s+\(\s*(-?\d+)\s+(-?\d+)\s*\)\s+\(\s*(-?\d+)\s+(-?\d+)\s*\)',text).groups()]
    x0,y0,x1,y1 = coords
    if x0 != 0 or y0 != 0 or abs(x1-y1)>0.001 or x1>1950:
        raise ValueError('Unsupported/non-square DIEAREA; geometry requires explicit adaptation')
    if abs(outer_side_um-1980.0)>1e-6:
        raise ValueError('This profile requires a 1980um seal-ring outer side')
    if abs(inner_gap_um-5.0)>1e-6:
        raise ValueError('This profile requires a 5um die-to-seal-ring inner gap')
    size_float=outer_side_um-30.0
    size=int(round(size_float))
    if abs(size-size_float)>1e-6:
        raise ValueError('Seal-ring outer side must map to an integer native boundary')
    ring = next(c for c in ring_lib.cells if c.name == 'tsmc_c018_sealring_1p6m')
    if ring.bounding_box() != ((-15.0,-15.0),(1875.0,2005.0)):
        raise ValueError('Native sealring differs from measured course reference')
    native_edge = next(c for c in ring_lib.cells if c.name == 'tsmc_c018_seal_ring_edge_1p6m')
    native_corner = next(c for c in ring_lib.cells if c.name == 'tsmc_c018_sealring_corner_1p6m')
    nominal_inner=[p for p in native_edge.get_polygons(layer=3,datatype=0)]
    if len(nominal_inner)!=1 or nominal_inner[0].bounding_box()!=((0.0,5.0),(1.0,15.0)):
        raise ValueError('Unexpected native seal-ring nominal inner/outer geometry')
    # The ring-cell reference boundary is its inner frame. The native
    # assembly occupies 15um outward from it, while the user requires an
    # additional 5um clear space between DIEAREA and that inner frame.
    origin=-inner_gap_um
    expected_die=size-2.0*inner_gap_um
    if abs(x1-expected_die)>0.001 or abs(y1-expected_die)>0.001:
        raise ValueError('DIEAREA %.6f does not realize %.6fum ring origin with %.6fum gap' %
                         (x1,origin,inner_gap_um))
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
    offset = origin
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
            expected=list(original_counts[c.name])
            if c.name in [x['cell'] for x in changes]:expected[0]+=1
            if expected!=[len(c.polygons),len(c.paths),len(c.labels),len(c.references)]:
                raise ValueError('Native original cell changed: '+c.name)
    lib.write_gds(str(output))
    gap_bbox=((origin,origin),(size+origin,size+origin))
    evidence.write_text(json.dumps({'gdstk':gdstk.__version__,'unit_m':lib.unit,'precision_m':lib.precision,
        'die_um':coords,'ring_reference_um':size,'ring_origin_um':[offset,offset],
        'seal_ring_inner_gap_um':inner_gap_um,'seal_ring_reference_bbox_um':gap_bbox,
        'seal_ring_native_outward_width_um':15.0,
        'ring_external_bbox_um':actual,'ring_external_size_um':outer_side_um,
        'ring_edges':4*(size+10),'ring_corners':4,
        'poc_master':ref.cell_name,'poc_instance_origin_um':ref.origin,'poc_anchor_um':point,
        'original_subcell_element_counts_unchanged':not patch_io,'private_cell_changes':changes,
        'method':'Native GDS cell assembly; no scaling or flattening. Native OA import and Calibre required.'},indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('output',type=Path)
    p.add_argument('ring_zip',type=Path);p.add_argument('evidence',type=Path)
    p.add_argument('--patch-io',action='store_true')
    p.add_argument('--outer-side-um',type=float,default=1980.0)
    p.add_argument('--inner-gap-um',type=float,default=5.0)
    a=p.parse_args();assemble(a.source,a.output,a.ring_zip,a.evidence,a.patch_io,
                              a.outer_side_um,a.inner_gap_um)
