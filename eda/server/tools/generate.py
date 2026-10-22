"""Generate this SoC's physical steps from measured Die geometry and IO data."""
import json
import math
from pathlib import Path
import re


def generate_steps(work, die):
    if len(die) != 4 or die[:2] != [0, 0] or any(not isinstance(v,(int,float)) or not math.isfinite(v) for v in die):
        raise ValueError('Expected a rectangular Die with origin at zero')
    w, h = die[2:]
    if min(w, h) < 1800:
        raise ValueError('Die too small for the documented perimeter')
    config = json.loads((work / 'config/design.json').read_text())
    if w*h/1e6>config['max_die_area_mm2']:
        raise ValueError('Measured whole Die including PAD exceeds %.3f mm2: %.6f' % (config['max_die_area_mm2'],w*h/1e6))
    io = json.loads((work / 'config/io_plan.json').read_text())
    signals, powers = io['signals'], io['power_slots']
    expected = {'clk_i', 'rst_ni', 'tck_i', 'tms_i', 'td_i', 'td_o'}
    if {s['port'] for s in signals} != expected or len(signals) != 6 or len(powers) != 7:
        raise ValueError('Changed IO contract; this six-signal profile must be adapted explicitly')
    if len({s['pad'] for s in signals}) != 6 or any(s['side'] not in ['N', 'S'] for s in signals):
        raise ValueError('Signal PAD names must be unique; this profile supports north/south signals')
    for side in 'NSWE':
        offsets = [p['offset_um'] for p in powers] + [s['offset_um'] for s in signals if s['side'] == side]
        length = w if side in 'NS' else h
        ordered = sorted(offsets)
        if min(ordered) < 115 or max(ordered) + 60 > length - 115 or any(b - a < 60 for a, b in zip(ordered, ordered[1:])):
            raise ValueError('IO overlap or out-of-range offsets on ' + side)
    raw = work / 'flow/tcl/steps'
    out = work / 'pnr/generated'
    out.mkdir(parents=True, exist_ok=True)
    bodies = {p.name: p.read_text(encoding='utf-8') for p in raw.glob('*.tcl')}
    bodies['02.tcl'] = 'floorPlan -coreMarginsBy die -site core7T -s $eda_core_size $eda_core_size 150 150 150 150\n'
    bodies['04.tcl'] += 'if {[lsort [dbGet top.terms.name]] ne [lsort {clk_i rst_ni tck_i tms_i td_i td_o}]} {error "Unexpected top-level signal ports"}\n'
    corners = [('bottom_left', 0, 0, 'R0'), ('bottom_right', w - 115, 0, 'MY'), ('top_left', 0, h - 115, 'MX'), ('top_right', w - 115, h - 115, 'R180')]
    bodies['05.tcl'] = '\n'.join('addInst -physical -cell PCORNER -inst corner_%s -loc {%.6f %.6f} -ori %s -place_status fixed -dontSnapToPlacementGrid' % c for c in corners) + '\n'
    for name, x, y, direction in corners:
        bodies['05.tcl'] += 'if {[dbGet [dbGet top.insts.name corner_%s -p].pStatus] ne "fixed" || [dbGet [dbGet top.insts.name corner_%s -p].orient] ne "%s"} {error "Corner placement failed"}\n' % (name, name, direction)
    ori = {'N': 'R180', 'S': 'R0', 'W': 'R270', 'E': 'R90'}

    def location(side, offset, depth):
        return {'N': (offset, h - depth), 'S': (offset, 0), 'W': (0, offset), 'E': (w - depth, offset)}[side]

    def add(master, name, side, offset, physical=False, depth=115):
        x, y = location(side, offset, depth)
        return 'addInst %s-cell %s -inst %s -loc {%.6f %.6f} -ori %s -place_status fixed -dontSnapToPlacementGrid\n' % ('-physical ' if physical else '', master, name, x, y, ori[side])

    bodies['07.tcl'] = ''.join(add('PDDW0204CDG', 'i_pad_' + s['pad'], s['side'], s['offset_um']) for s in signals)
    bodies['07.tcl'] += 'if {[llength [dbGet -e top.insts.cell.name PDDW0204CDG -p2]] != 6} {error "Signal PAD count mismatch"}\n'
    lines = []
    for s in signals:
        port, pad = s['port'], 'i_pad_' + s['pad']
        control = {'OEN': 1, 'IE': 1, 'PE': 0, 'DS': 0, 'I': 0} if s['direction'] == 'input' else {'OEN': 0, 'IE': 0, 'PE': 0, 'DS': 0}
        if s['direction'] not in ['input', 'output'] or (port == 'td_o') != (s['direction'] == 'output'):
            raise ValueError('Unexpected signal direction: ' + port)
        lines += ['set eda_term [dbGet top.terms.name %s -p]' % port,
                  'set eda_core_object [dbGet $eda_term.net]',
                  # detachModulePort can move internal connections onto a NEW
                  # net while the original net object remains on the port side.
                  # A real internal pin is stable across that transformation.
                  'set eda_core_anchor [lindex [dbGet -e $eda_core_object.instTerms] 0]',
                  'if {$eda_core_anchor in {{} 0x0}} {error "Signal has no internal pin anchor"}',
                  'addNet %s_pad' % port,
                  'detachModulePort - %s' % port,
                  'attachModulePort - %s %s_pad' % (port, port),
                  'set eda_core_net [dbGet $eda_core_anchor.net.name]',
                  'set eda_ext_net [dbGet [dbGet top.terms.name %s -p].net.name]' % port,
                  'if {$eda_core_net in {{} 0x0} || $eda_ext_net in {{} 0x0} || $eda_core_net eq $eda_ext_net} {error "Invalid core/PAD split"}',
                  'attachTerm %s PAD $eda_ext_net' % pad,
                  'attachTerm %s %s $eda_core_net' % (pad, 'C' if s['direction'] == 'input' else 'I')]
        lines.extend("attachTerm %s %s 1'b%d" % (pad, pin, bit) for pin, bit in control.items())
    lines += ['saveNetlist ../my_soc_top/my_soc_top_io_connected.v']
    bodies['08.tcl'] = '\n'.join(lines) + '\n'
    registration = bodies['09.tcl'][bodies['09.tcl'].index('puts "POWER_PAD_COUNT'):]
    bodies['09.tcl'] = ''.join(add(p['master'], 'i_pad_' + side + '_' + p['suffix'], side, p['offset_um']) for side in 'NSWE' for p in powers) + registration
    bodies['10.tcl'] = ''.join(add('PAD60LU_OBV', 'i_bond_' + s['pad'], s['side'], s['offset_um'], True, 73.16) for s in signals)
    bodies['10.tcl'] += ''.join(add('PAD60LU_OBV', 'i_bond_' + side + '_' + p['suffix'], side, p['offset_um'], True, 73.16) for side in 'NSWE' for p in powers)
    bodies['10.tcl'] += 'if {[llength [dbGet -e top.insts.cell.name PAD60LU_OBV -p2]] != 34} {error "Bond PAD count mismatch"}\n'
    # The continuity check uses both measured dimensions, which may differ
    # slightly after the tool snaps the square request to legal row/site grids.
    text = bodies['12_check.tcl']
    text = text.replace('abs($y1-1800.4)', 'abs($y1-%.6f)' % h).replace('abs($x1-1800.4)', 'abs($x1-%.6f)' % w)
    text = text.replace('if {abs($last-1685.4)>0.001}', 'set eda_edge_end [expr {$side in {N S} ? %.6f : %.6f}]\n if {abs($last-$eda_edge_end)>0.001}' % (w - 115, h - 115))
    bodies['12_check.tcl'] = text
    rects = {}
    for s in signals:
        x = s['offset_um'] + 10
        y = h - 2.4 if s['side'] == 'N' else 1
        rects[s['port']] = [x, y, x + 10, y + 1]
    power_offset = {p['suffix']: p['offset_um'] for p in powers}
    for net, suffix in [('VDD', 'vdd_1'), ('VSS', 'vss_1'), ('VDDPST', 'vddio'), ('VSSPST', 'vssio')]:
        x = power_offset[suffix] + 10
        rects[net] = [x, h - 2.4, x + 10, h - 1.4]
    lines = []
    for name, rect in rects.items():
        coords = ' '.join('%.6f' % v for v in rect)
        if name in expected:
            lines.append('createPhysicalPin %s -net %s -layer METAL4 -rect {%s}' % (name, name, coords))
        else:
            lines.append('createPGPin %s -net %s -geom METAL4 %s' % (name, name, coords))
    lines += ['defOut ../my_soc_top/my_soc_top_physicalPins.def', 'eda_picture 14_floorplan.gif']
    bodies['14.tcl'] = '\n'.join(lines) + '\n'
    mx, my = config['macro_xy_um']
    for name in ['13.tcl', '18.tcl', '19.tcl']:
        mapping = {'250': mx, '650': my, '636': my - 14, '630': my - 20, '804.595': mx + 554.595, '1387.85': my + 737.85, '1393.85': my + 743.85, '230': mx - 20, '660': my + 10, '824.595': mx + 574.595, '1365': my + 715}
        bodies[name] = re.sub(r'(?<![\w.])(?:' + '|'.join(re.escape(k) for k in sorted(mapping, key=len, reverse=True)) + r')(?![\w.])', lambda m: '%.6f' % mapping[m.group()], bodies[name])
    bodies['20.tcl'] = bodies['20.tcl'].replace('{80 80 1720 1720}', '{80 80 %.6f %.6f}' % (w - 80.4, h - 80.4))
    bodies['31_fix.tcl'] = bodies['31_fix.tcl'].replace('open ../my_soc_top/my_soc_top_postRoute_antenna.rpt r', 'open $eda_antenna_report r')
    bodies['33.tcl'] = bodies['33.tcl'].replace('timeDesign -postRoute -expandedViews', 'extractRC\ntimeDesign -postRoute -expandedViews', 1)
    for name, body in bodies.items():
        body = re.sub(r'^fit\s*$', '', body, flags=re.M)
        body = re.sub(r'^dumpToGIF ../../evidence/(\S+)\s*$', r'eda_picture \1', body, flags=re.M)
        (out / name).write_text(body, encoding='utf-8')
    result = {'die_um': die, 'whole_die_area_mm2':w*h/1e6, 'max_whole_die_area_mm2':config['max_die_area_mm2'], 'signal_pads': signals, 'power_slots': powers, 'pin_rectangles_um': rects, 'main_macro_xy_um': [mx, my], 'generated_from_measured_database_geometry': True}
    (work / 'evidence/geometry.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
