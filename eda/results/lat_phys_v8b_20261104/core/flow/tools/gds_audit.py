"""Read GDS records without external libraries; inspect structure and native M4 shapes."""
import argparse
from collections import Counter
import gzip
import json
import math
from pathlib import Path
import struct

def real8(data):
    if not any(data):
        return 0.0
    sign = -1 if data[0] & 128 else 1
    return sign * int.from_bytes(data[1:], 'big') / 2**56 * 16**((data[0] & 127) - 64)

def audit(path, selected):
    opener = gzip.open if str(path).endswith('.gz') else open
    cells, refs, labels, shapes = set(), Counter(), {}, {}
    all_m4, hierarchy = {}, {}
    current = None
    element = None
    units = None
    records = 0
    ended = False
    with opener(path, 'rb') as f:
        while True:
            head = f.read(4)
            if not head:
                break
            assert len(head) == 4, 'Truncated GDS header'
            length, kind, dtype = struct.unpack('>HBB', head)
            assert length >= 4 and length % 2 == 0, 'Invalid GDS record length'
            data = f.read(length - 4)
            assert len(data) == length - 4, 'Truncated GDS record'
            records += 1
            if kind == 0x03:
                units = [real8(data[:8]), real8(data[8:16])]
            elif kind == 0x06:
                current = data.rstrip(b'\0').decode('ascii')
                assert current not in cells, 'Duplicate structure: ' + current
                cells.add(current)
            elif kind in (0x08, 0x09, 0x0A, 0x0B, 0x0C, 0x2D):
                element = {'kind': kind}
            elif element is not None:
                if kind in (0x0D, 0x0E, 0x16):
                    element[{0x0D:'layer', 0x0E:'datatype', 0x16:'texttype'}[kind]] = struct.unpack('>h', data)[0]
                elif kind in (0x12, 0x19):
                    element['name' if kind == 0x12 else 'text'] = data.rstrip(b'\0').decode('ascii')
                elif kind == 0x10:
                    element['xy'] = list(struct.unpack('>'+'i'*(len(data)//4), data))
                elif kind == 0x1A:
                    element['reflect_x'] = bool(struct.unpack('>H', data)[0] & 0x8000)
                elif kind in (0x1B, 0x1C):
                    element['mag' if kind == 0x1B else 'angle'] = real8(data)
                elif kind == 0x13:
                    element['colrow'] = list(struct.unpack('>hh', data))
                elif kind == 0x11:
                    if 'name' in element:
                        refs[element['name']] += 1
                        if selected:
                            hierarchy.setdefault(current, []).append(element)
                    if element['kind'] == 0x0C and current == 'my_soc_top' and element.get('layer') == 43:
                        labels.setdefault(current, []).append(element)
                    # gds2.map: M4 conductor=31; M4 pin/label=43.
                    if selected and element.get('layer') in (31, 43) and element['kind'] in (0x08, 0x09, 0x0C, 0x2D):
                        all_m4.setdefault(current, []).append(element)
                    element = None
            if kind == 0x04:
                ended = True
                # Foundry GDS files may pad tape blocks with zero bytes after ENDLIB.
                assert not any(f.read()), 'Nonzero trailing data after ENDLIB'
                break
    assert ended and units is not None, 'Missing ENDLIB or UNITS'
    cache = {}
    def flatten(name, ancestors=()):
        assert name not in ancestors, 'Cyclic GDS hierarchy'
        if name in cache:
            return cache[name]
        result = list(all_m4.get(name, []))
        for ref in hierarchy.get(name, []):
            child = flatten(ref['name'], ancestors + (name,))
            if not child:
                continue
            xy = ref['xy']
            cols, rows = ref.get('colrow', [1, 1])
            ax, ay = ((xy[2]-xy[0])/cols, (xy[3]-xy[1])/cols) if cols > 1 else (0, 0)
            bx, by = ((xy[4]-xy[0])/rows, (xy[5]-xy[1])/rows) if rows > 1 else (0, 0)
            theta = math.radians(ref.get('angle', 0))
            cs, sn = math.cos(theta), math.sin(theta)
            mag = ref.get('mag', 1)
            sy = -1 if ref.get('reflect_x') else 1
            for col in range(cols):
                for row in range(rows):
                    tx, ty = xy[0]+col*ax+row*bx, xy[1]+col*ay+row*by
                    for shape in child:
                        out = dict(shape)
                        coords = []
                        for x, y in zip(shape.get('xy', [])[::2], shape.get('xy', [])[1::2]):
                            coords.extend([round(tx+mag*(cs*x-sn*sy*y),6),
                                           round(ty+mag*(sn*x+cs*sy*y),6)])
                        out['xy'] = coords
                        result.append(out)
        cache[name] = result
        return result
    native_counts = {}
    for name in sorted(selected):
        if name in cells:
            raw = flatten(name)
            native_counts[name] = len(raw)
            # Keep long rail/pad polygons and all labels; omit thousands of small slot shapes.
            limit = 10 / (units[1] * 1e6)
            shapes[name] = [e for e in raw if e['kind'] == 0x0C or
                           max(max(e['xy'][::2])-min(e['xy'][::2]),
                               max(e['xy'][1::2])-min(e['xy'][1::2])) >= limit]
    return {'file': str(path), 'records': records, 'structure_count': len(cells),
            'structures': sorted(cells), 'undefined_references': sorted(set(refs)-cells),
            'reference_counts': dict(refs), 'units_user_per_dbu': units[0],
            'units_meters_per_dbu': units[1], 'dbu_um': units[1]*1e6,
            'top_labels': labels, 'selected_native_m4_geometry': shapes,
            'native_m4_element_counts_before_filter': native_counts,
            'native_geometry_filter': 'All labels; conductor/pin polygons with bbox span >=10 um; small slot shapes omitted.',
            'top_labels_filter': 'M4 pin labels on layer 43; instance-name labels on layer 59 omitted from this JSON, retained in original GDS.',
            'note': 'Record/structure and geometry inspection only; not independent LVS or foundry DRC.'}

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('file', type=Path)
    p.add_argument('output', type=Path)
    p.add_argument('--masters', nargs='*', default=[])
    args = p.parse_args()
    result = audit(args.file, set(args.masters))
    args.output.write_text(json.dumps(result, indent=2))
    print(json.dumps({k: result[k] for k in ['structure_count','undefined_references','dbu_um','records']}))
