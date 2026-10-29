"""Fail-closed report parsing and structural delivery checks (not foundry LVS)."""
import gzip
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
from gds_audit import audit as gds_audit


def load_text(path):
    if not path.is_file():
        raise ValueError('Required report missing: ' + str(path))
    with (gzip.open(str(path), 'rt', errors='replace') if path.suffix == '.gz' else path.open(encoding='utf-8', errors='replace')) as f:
        return f.read()


def clear_step_outputs(work, step):
    """Remove only owned outputs that this step must regenerate, never inputs."""
    root = work / 'pnr/my_soc_top'
    candidates = []
    names = {8: ['my_soc_top_io_connected.v'], 11: ['my_soc_top_pg_bound.v'], 14: ['my_soc_top_physicalPins.def'], 15: ['my_soc_top_pg_drc.rpt'], 19: ['my_soc_top_pg_drc.rpt'], 21: ['my_soc_top_pg_drc.rpt', 'my_soc_top_pg_noDangling.rpt'], 23: ['my_soc_top_welltap.rpt', 'my_soc_top_postPhysCells_pg_drc.rpt'], 24: ['my_soc_top_place_check.rpt'], 25: ['my_soc_top_postTie_place.rpt', 'my_soc_top_postTie.v'], 28: ['my_soc_top_postCTS_place_check.rpt'], 29: ['my_soc_top_postHoldFix_place.rpt']}
    candidates.extend(root / name for name in names.get(step, []))
    for prefix in {31: ['postRoute', 'postAntennaFix'], 32: ['postHoldAuto'], 33: ['postFiller']}.get(step, []):
        candidates.extend(root.glob('my_soc_top_' + prefix + '*.rpt'))
    directories = {26: ['preCTS'], 28: ['postCTS'], 29: ['postCTS_holdFix', 'postCTS_holdFix_check', 'postCTS_nativeOpt', 'postCTS_fanoutReserve'], 32: ['postRoute', 'postRoute_margin', 'postRoute_setupAuto', 'postRoute_holdAuto', 'postRoute_holdAuto_check'], 33: ['postFiller']}
    for name in directories.get(step, []):
        candidates.extend((root / 'reports' / name).glob('*.summary*'))
    if step == 34:
        candidates.extend((root / 'outputs/manual_final').glob('*'))
    candidates.extend((work / 'evidence/commands' / ('%02d' % step)).glob('*.tcl'))
    for p in candidates:
        if p.is_file():
            p.resolve().relative_to(work.resolve())
            p.unlink()


def archive_report_references(work, step, value):
    if isinstance(value, dict):
        p = Path(value['report']) if isinstance(value.get('report'), str) else None
        if p is not None and p.is_file():
            relative = p.resolve().relative_to(work.resolve())
            target = work / 'evidence/stage_reports' / ('%02d' % step) / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(str(p), str(target))
            value['archived_report'] = str(target.relative_to(work))
            value['report_sha256'] = hashlib.sha256(p.read_bytes()).hexdigest()
        for item in list(value.values()):
            archive_report_references(work, step, item)
    elif isinstance(value, list):
        for item in value:
            archive_report_references(work, step, item)


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def area_summary(path):
    body = load_text(path)
    row = next((line.split()[1:] for line in body.splitlines() if re.match(r'^my_soc_top\s+\d', line)), None)
    if row is None or len(row) < 12:
        raise ValueError('Unrecognized Genus area report: ' + str(path))
    numbers = list(map(float, row))
    if numbers[1] <= 0:
        raise ValueError('Empty synthesis result')
    return {'cell_count': int(numbers[0]), 'cell_area_um2': numbers[1], 'net_area_um2': numbers[2], 'latch_area_um2': numbers[7], 'memory_area_um2': numbers[9], 'report': str(path)}


def timing(directory, require_clean=False):
    found = {}
    for p in sorted(directory.glob('*.summary*')):
        text = load_text(p)
        mode = 'Hold' if 'Hold mode' in text else 'Setup' if 'Setup mode' in text else None
        if mode is None:
            continue
        fields = [re.search(pattern, text) for pattern in [r'WNS \(ns\):\|\s*([-\d.]+)', r'TNS \(ns\):\|\s*([-\d.]+)', r'Violating Paths:\|\s*(\d+)']]
        if not all(fields):
            raise ValueError('Incomplete timing summary: ' + str(p))
        drv = {kind: {'real': int(real), 'total': int(total)} for kind, real, total in re.findall(r'\|\s*(max_\w+)\s*\|\s*(\d+)\s*\(\d+\)\s*\|[^|]*\|\s*(\d+)\s*\(\d+\)', text)}
        # Innovus 21.16 emits electrical DRVs in Setup summaries, while its
        # Hold summary normally omits that table. Require it in Setup and
        # identify the omission in Hold rather than inventing zero fields.
        if mode == 'Setup' and not {'max_cap', 'max_tran', 'max_fanout'}.issubset(drv):
            raise ValueError('Missing electrical DRV fields: ' + str(p))
        value = {'report': str(p), 'wns_ns': float(fields[0].group(1)), 'tns_ns': float(fields[1].group(1)), 'violating_paths': int(fields[2].group(1)), 'drv': drv, 'electrical_drv_table_reported_here': bool(drv)}
        value['minimum_wns_ns'] = 0.0
        value['targets_met'] = value['wns_ns'] >= value['minimum_wns_ns'] and value['tns_ns'] == 0 and value['violating_paths'] == 0 and all(x['real'] == x['total'] == 0 for x in drv.values())
        if mode in found:
            raise ValueError('Ambiguous multiple timing summaries for ' + mode + ': ' + str(directory))
        found[mode] = value
    if set(found) != {'Setup', 'Hold'}:
        raise ValueError('Missing separate Setup/Hold summaries: ' + str(directory))
    if require_clean and not all(v['targets_met'] for v in found.values()):
        raise ValueError('Timing/electrical targets still violated: ' + json.dumps(found))
    return found


def require_clean_report(path, kind):
    text = load_text(path)
    patterns = {'drc': r'No DRC violations were found', 'connectivity': r'Found no problems or warnings\.', 'tap': r'Found 0 violations in total'}
    if not re.search(patterns[kind], text):
        raise ValueError('Check did not establish zero violations (%s): %s' % (kind, path))
    # A success-looking header cannot hide a second actual problem section.
    if kind == 'connectivity' and re.search(r'\b[1-9]\d*\s+(?:Problem\(s\)|Warning\(s\))', text):
        raise ValueError('Connectivity report contains additional problems: ' + str(path))
    return {'report': str(path), 'zero_reported_violations': True, 'scope': kind}


def antenna_count(path):
    text = load_text(path)
    m = re.search(r'Number of nets violated:\s+(\d+)', text)
    if m:
        return int(m.group(1))
    if 'No Violations Found' in text:
        return 0
    raise ValueError('Unrecognized antenna report: ' + str(path))


def placement(path):
    text = load_text(path)
    unplaced = re.search(r'Number of Unplaced Instances\s*=\s*(\d+)', text)
    if not unplaced or int(unplaced.group(1)):
        raise ValueError('Unplaced instances or unreadable placement report: ' + str(path))
    expected = {'i_pad_' + side + '_' + suffix for side in 'NSWE' for suffix in ['vdd_1', 'vdd_2', 'vddio', 'vss_1', 'vss_2', 'vssio', 'poc']}
    expected.update('i_pad_' + name for name in ['clk', 'rst_n', 'tck', 'tms', 'tdi', 'tdo'])
    observed = None
    for name, body in re.findall(r'set\s+(pchk\w+List)\s+\[list\s*(.*?)\]', text, re.S):
        items = set(re.findall(r'\{([^}]+)\}', body))
        if name == 'pchkIoOverlapList':
            observed = items
        elif items:
            raise ValueError('Unexpected placement violation: ' + name)
    if observed != expected:
        raise ValueError('IO/Bond overlap objects differ from the current fixed perimeter: ' + str(path))
    return {'report': str(path), 'unplaced': 0, 'expected_io_bond_covers': sorted(expected), 'no_other_listed_placement_violations': True}


def helper(work, name, *args):
    p = work / 'flow/tools' / name
    result = subprocess.run([sys.executable, str(p)] + [str(x) for x in args], cwd=str(work), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode:
        raise ValueError(name + ' failed:\n' + result.stdout[-1000:] + result.stderr[-3000:])
    return {'program': name, 'exit_code': 0}


def io_native(work):
    p = work / 'pnr/my_soc_top/my_soc_top_io_pg_connectivity.rpt'
    text = load_text(p)
    clean = 'Found no problems or warnings.' in text
    if not clean:
        if not io_abstract_only(text):
            raise ValueError('Unexpected IO PG connectivity problem: ' + str(p))
    if not (work / 'evidence/step_12.json').is_file() or not (work / 'evidence/11_pg_topology.json').is_file():
        raise ValueError('IO exception requires fresh side continuity and four-net topology checks')
    config = json.loads((work / 'config/design.json').read_text())
    native = Path(config['pdk_root']) / 'tpd018nv_280a/TSMCHOME/digital/Back_End/gds/tpd018nv_280a/mt_2/6lm/tpd018nv.gds'
    plan = json.loads((work / 'config/io_plan.json').read_text())
    signal_masters = {signal['master'] for signal in plan['signals']}
    if signal_masters != {'PDDW0204CDG', 'PDDW1216CDG'}:
        raise ValueError('Unverified signal PAD GDS mapping')
    masters = signal_masters | {'PVDD1CDG', 'PVSS1CDG', 'PVDD2CDG', 'PVSS2CDG', 'PVDD2POC', 'PFILLER20', 'PFILLER10', 'PFILLER5', 'PFILLER1', 'PFILLER05', 'PFILLER0005', 'PCORNER'}
    result = gds_audit(native, masters)
    if result['undefined_references'] or not masters.issubset(result['selected_native_m4_geometry']):
        raise ValueError('Incomplete native IO GDS')
    save(work / 'evidence/native_io_gds.json', result)
    helper(work, 'audit_native_io_rails.py')
    return {'native_rails_and_corner_turns_checked': True, 'actual_perimeter_continuity_checked_at_step': 12, 'io_abstract_no_routing_nets': [] if clean else ['VDDPST', 'VSSPST'], 'scope': 'Native rail geometry + actual placement; not merged-chip LVS/IR/EM/ESD'}


def io_abstract_only(text):
    nets = re.findall(r'^Net (\S+): no routing\s*$', text, re.M)
    problems = re.findall(r'^\s*(\d+) Problem\(s\) \(([^)]+)\):', text, re.M)
    return sorted(nets) == ['VDDPST', 'VSSPST'] and problems == [('2', 'IMPVFC-98')] and bool(re.search(r'^\s*2 total info\(s\) created\.\s*$', text, re.M)) and not re.search(r'\bWarning\(s\)', text)


def signal_connectivity(work, path):
    text = load_text(path)
    if 'Found no problems or warnings.' in text:
        return require_clean_report(path, 'connectivity')
    proof = work / 'evidence/step_22.json'
    if not io_abstract_only(text) or not proof.is_file():
        raise ValueError('Unverified signal connectivity problem: ' + str(path))
    record = json.loads(proof.read_text())
    identity = hashlib.sha256((work / 'evidence/input_manifest.json').read_bytes()).hexdigest()
    native = record.get('automatic_checks', {}).get('io_native_geometry', {})
    if record.get('input_manifest_sha256') != identity or not native.get('native_rails_and_corner_turns_checked') or native.get('actual_perimeter_continuity_checked_at_step') != 12 or not (work / 'evidence/native_io_rails_check.json').is_file():
        raise ValueError('IO abstract exception lacks same-run native/placement evidence')
    return {'report': str(path), 'unresolved_signal_problems': 0, 'classified_io_abstract_nets': ['VDDPST', 'VSSPST'], 'same_input_native_geometry_proof_step': 22, 'not_independent_LVS': True}


def modules(text):
    text = re.sub(r'/\*.*?\*/|//[^\n]*', '', text, flags=re.S)
    data = {}
    def canonical(value):
        return re.sub(r'\\(?=[^\s])', '', value.strip())
    for m in re.finditer(r'\bmodule\s+(\S+)\s*\(.*?\);(.*?)\bendmodule\b', text, re.S):
        entries = {}
        for x in re.finditer(r'\b([A-Za-z_]\w*)\s+(\\?[^\s(]+)\s*\((.*?)\)\s*;', m.group(2), re.S):
            pins = dict(re.findall(r'\.([A-Za-z_]\w*)\s*\(([^()]*)\)', x.group(3)))
            if pins:
                entries[canonical(x.group(2))] = (x.group(1), {p: canonical(n) for p, n in pins.items()})
        data[canonical(m.group(1))] = entries
    if 'my_soc_top' not in data:
        raise ValueError('Missing my_soc_top module in mapped netlist')
    return data


def flatten(data, name='my_soc_top', prefix='', ancestors=()):
    if name in ancestors:
        raise ValueError('Cyclic netlist hierarchy')
    result = {}
    for instance, (master, pins) in data[name].items():
        path = prefix + instance
        if master in data:
            result.update(flatten(data, master, path + '/', ancestors + (name,)))
        else:
            result[path] = master
    return result


def mapped_netlist_check(work):
    data = modules(load_text(work / 'syn/my_soc_top/my_soc_top_postsyn.v'))
    leaves = flatten(data)
    if list(leaves.values()).count('RA1SHD_2048x32M8') != 1:
        raise ValueError('Expected exactly one mapped native SRAM')
    library_paths = json.loads((work / 'evidence/doctor.json').read_text())['libraries_sha256']
    allowed = set()
    for path in library_paths:
        if path.endswith('.lib'):
            allowed.update(re.findall(r'\bcell\s*\(\s*"?([^\s)";]+)"?\s*\)', load_text(Path(path))))
    unknown = set(leaves.values()) - allowed
    if unknown:
        raise ValueError('Unmapped or missing-library leaf cells: ' + ', '.join(sorted(unknown)[:20]))
    area = area_summary(work / 'syn/my_soc_top/reports/area/area.rpt')
    if area['latch_area_um2'] != 0:
        raise ValueError('Unexpected data latch area; inspect latch/gating mapping before proceeding')
    report = load_text(work / 'syn/my_soc_top/reports/area/area.rpt')
    if not all(name in report for name in ['i_npu_subsystem', 'i_dma']):
        raise ValueError('Expected NPU/DMA area hierarchy absent; inspect accidental pruning')
    config=json.loads((work/'config/design.json').read_text())
    automatic_gates=[path for path in leaves if 'RC_CG_HIER_INST' in path]
    controlled_ffs=[path for path,master in leaves.items() if re.match(r'^(EDF|SDF|SEDF|GSDF|DFK|DFX)',master)]
    combo_policy=work/'evidence/combinational_mapping_policy.json'
    combo=json.loads(combo_policy.read_text()) if combo_policy.is_file() else {'mapping':'native_unrestricted'}
    excluded=set(combo.get('excluded_native_masters',{}))
    remaining_combo=[path for path,master in leaves.items() if master in excluded]
    if config.get('combinational_cell_mapping')=='tt_nonnegative_tables' and remaining_combo:
        save(work/'evidence/combinational_mapping_mismatch.json',{
            'requested_mapping':'tt_nonnegative_tables','remaining_instances':len(remaining_combo),
            'examples':remaining_combo[:20]})
        raise ValueError('Selected native TT combinational mapping not applied: %d instances remain'%len(remaining_combo))
    if config.get('functional_enable_mapping')=='mux_dff' and controlled_ffs:
        # Verify the selected implementation really happened. This is not a
        # new timing margin or a restriction on the native zero-slack profile.
        save(work/'evidence/register_mapping_mismatch.json',{
            'requested_mapping':'mux_dff','remaining_controlled_flops':len(controlled_ffs),
            'examples':controlled_ffs[:20],
            'reason':'The selected library mapping did not take effect; do not continue physical implementation.'})
        raise ValueError('mux_dff mapping not applied: %d controlled flip-flops remain'%len(controlled_ffs))
    return {'native_main_srams': 1, 'mapped_leaf_instances': len(leaves), 'all_leaf_types_have_library_models': True, 'npu_dma_area_hierarchy_present': True, 'latch_area_um2': 0,
            'automatic_clock_gating_requested':config.get('insert_automatic_clock_gating',True),
            'mapped_automatic_clock_gate_instances':len(automatic_gates),
            'functional_enable_mapping':config.get('functional_enable_mapping','library_enable'),
            'mapped_controlled_flip_flop_instances':len(controlled_ffs),
            'combinational_cell_mapping':combo['mapping'],
            'mapped_excluded_TT_combinational_instances':len(remaining_combo)}


def physical_pins(work, path):
    text = load_text(path)
    unit = re.search(r'UNITS DISTANCE MICRONS (\d+)\s*;', text)
    section = re.search(r'\bPINS\s+(\d+)\s*;(.*?)END PINS', text, re.S)
    if not unit or not section or int(section.group(1)) != 10:
        raise ValueError('Expected ten physical ports with explicit DEF units')
    dbu = int(unit.group(1))
    expected = json.loads((work / 'evidence/geometry.json').read_text())['pin_rectangles_um']
    entries = re.findall(r'^-\s+(\S+)\s+(.*?);', section.group(2), re.M | re.S)
    if {name for name, _ in entries} != set(expected):
        raise ValueError('Physical port set mismatch')
    for name, body in entries:
        xy = re.search(r'\+ FIXED\s*\(\s*(-?\d+)\s+(-?\d+)\s*\)\s+N', body)
        offset = re.search(r'LAYER METAL4\s*\(\s*(-?\d+)\s+(-?\d+)\s*\)\s*\(\s*(-?\d+)\s+(-?\d+)\s*\)', body)
        if not xy or not offset:
            raise ValueError('Missing physical pin geometry: ' + name)
        a, b = map(int, xy.groups())
        actual = [(int(v) + (a if i % 2 == 0 else b)) / dbu for i, v in enumerate(offset.groups())]
        if any(abs(x - y) > 0.001 for x, y in zip(actual, expected[name])):
            raise ValueError('Physical rectangle mismatch: ' + name)
        direction = 'INOUT' if name in ['VDD', 'VSS', 'VDDPST', 'VSSPST'] else 'OUTPUT' if name == 'td_o' else 'INPUT'
        use = 'GROUND' if name in ['VSS', 'VSSPST'] else 'POWER' if name in ['VDD', 'VDDPST'] else 'SIGNAL'
        if '+ DIRECTION ' + direction not in body or '+ USE ' + use not in body:
            raise ValueError('Physical port direction/USE mismatch: ' + name)
    return {'ports': sorted(expected), 'dbu_per_um': dbu, 'all_rectangles_directions_uses_match_geometry_plan': True}


def export_audit(work):
    out = work / 'pnr/my_soc_top/outputs/manual_final'
    prefix = 'my_soc_top'
    result = {'independent_foundry_DRC_LVS_executed': False, 'SDF_simulation_executed': False}
    result['def_pins'] = physical_pins(work, out / (prefix + '.def'))
    geometry = json.loads((work / 'evidence/geometry.json').read_text())
    cfg = json.loads((work/'config/design.json').read_text())
    result['whole_die_area_mm2']=geometry['die_um'][2]*geometry['die_um'][3]/1e6
    result['max_whole_die_area_mm2']=cfg['max_die_area_mm2']
    if result['whole_die_area_mm2']>cfg['max_die_area_mm2']:
        raise ValueError('Exported whole die area exceeds limit')
    lef = load_text(out / (prefix + '.lef'))
    size = re.search(r'SIZE\s+([\d.]+)\s+BY\s+([\d.]+)\s*;', lef)
    if not size or any(abs(float(x) - y) > 0.001 for x, y in zip(size.groups(), geometry['die_um'][2:])):
        raise ValueError('LEF size mismatch')
    if set(re.findall(r'^\s*PIN\s+(\S+)', lef, re.M)) != set(geometry['pin_rectangles_um']):
        raise ValueError('LEF physical pin set mismatch')
    for name, rect in geometry['pin_rectangles_um'].items():
        part = re.search(r'\bPIN\s+' + re.escape(name) + r'\s+(.*?)\bEND\s+' + re.escape(name) + r'\b', lef, re.S)
        found = re.search(r'RECT\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s*;', part.group(1)) if part else None
        if not found or any(abs(float(x) - y) > 0.001 for x, y in zip(found.groups(), rect)):
            raise ValueError('LEF/DEF pin rectangle mismatch: ' + name)
    hier = modules(load_text(out / (prefix + '_hier_postpnr.v')))
    leaves = flatten(hier)
    sdf = load_text(out / (prefix + '_tt_io.sdf.gz'))
    sdf_cells = re.findall(r'\(CELL\s+\(CELLTYPE\s+"([^"]+)"\)\s+\(INSTANCE\s*([^)]*)\)', sdf)
    if not sdf_cells:
        raise ValueError('Missing SDF cell records')
    for master, instance in sdf_cells:
        instance = re.sub(r'\\(?=[^\s])', '', instance.strip())
        if instance and leaves.get(instance) != master:
            raise ValueError('SDF/hierarchical netlist instance mismatch: ' + instance)
    result['sdf_non_top_instances_matched'] = sum(bool(p.strip()) for _, p in sdf_cells)
    spef = load_text(out / (prefix + '_tt_io.spef.gz'))
    dn = len(re.findall(r'^\*D_NET\s', spef, re.M))
    if not dn or dn != len(re.findall(r'^\*END\s*$', spef, re.M)) or not re.search(r'\*DESIGN\s+"my_soc_top"', spef):
        raise ValueError('SPEF design or record mismatch')
    result['spef_networks'] = dn
    flat = modules(load_text(out / (prefix + '_flat_lvs.v')))
    if len(flat) != 1 or list(flatten(flat).values()).count('RA1SHD_2048x32M8') != 1:
        raise ValueError('Flat netlist hierarchy/native SRAM mismatch')
    helper(work, 'audit_io_ties.py', out / (prefix + '_flat_lvs.v'))
    sdc = load_text(out / (prefix + '.sdc'))
    config = json.loads((work / 'config/design.json').read_text())
    for name, period in [('sys_clk', config['system_period_ns']), ('jtag_clk', 100), ('virtual_jtag_tck', 1000)]:
        line = next((x for x in sdc.splitlines() if x.startswith('create_clock ') and re.search(r'-name\s+' + name + r'\b', x)), '')
        found = re.search(r'-period\s+([\d.]+)', line)
        if not found or float(found.group(1)) != period:
            raise ValueError('Final SDC clock mismatch: ' + name)
    if re.search(r'set_propagated_clock[^\n]*virtual_jtag_tck', sdc):
        raise ValueError('Virtual clock incorrectly propagated')
    gds = gds_audit(out / (prefix + '.gds.gz'), set())
    if gds['undefined_references'] or abs(gds['dbu_um'] - 0.0005) > 1e-12 or prefix not in gds['structures']:
        raise ValueError('GDS references/units/top mismatch')
    result['gds_structures'] = gds['structure_count']
    result['gds_undefined_references'] = []
    result['scope'] = 'Structural correspondence only; not equivalence, foundry DRC/LVS, IR/EM/ESD or actual SDF backannotation'
    save(work / 'evidence/export_audit.json', result)
    return result


def audit_step(work, step):
    pnr = work / 'pnr/my_soc_top'
    checks = {}
    temperatures = json.loads((work / 'evidence/rc_temperatures.json').read_text())
    cfg = json.loads((work / 'config/design.json').read_text())
    expected_temperatures = {'tt_1p80v_25c':25}
    if cfg['analysis_profile'].startswith('matched_'):
        expected_temperatures.update({'ss_pvt':125,'ff0_pvt':0,'ffm40_pvt':-40})
    if temperatures != expected_temperatures:
        raise ValueError('Actual restored RC corner temperatures mismatch')
    checks['actual_rc_temperatures_C'] = dict(temperatures)
    if step == 1:
        if not (work / 'evidence/current_macro.txt').read_text().strip():
            raise ValueError('Native SRAM not resolved')
        checks['native_sram_resolved'] = True
    if step == 2:
        checks['geometry'] = json.loads((work / 'evidence/geometry.json').read_text())
    if step == 8:
        checks['topology'] = helper(work, 'audit_io_topology.py')
    if step == 11:
        checks['four_supply_topology'] = helper(work, 'audit_io_topology.py', pnr / 'my_soc_top_pg_bound.v')
    if step in [15, 19, 21]:
        checks['special_drc'] = require_clean_report(pnr / 'my_soc_top_pg_drc.rpt', 'drc')
    if step == 21:
        checks['core_pg_without_dangling_check'] = require_clean_report(pnr / 'my_soc_top_pg_noDangling.rpt', 'connectivity')
        checks['scope_note'] = 'Full connectivity report retained; noAntenna scope excludes dangling checks here. Final step33 requires the full PG report clean.'
    if step == 22:
        checks['io_native_geometry'] = io_native(work)
    if step == 23:
        checks['tap'] = require_clean_report(pnr / 'my_soc_top_welltap.rpt', 'tap')
        checks['special_drc'] = require_clean_report(pnr / 'my_soc_top_postPhysCells_pg_drc.rpt', 'drc')
    place_files = {24: 'my_soc_top_place_check.rpt', 25: 'my_soc_top_postTie_place.rpt', 28: 'my_soc_top_postCTS_place_check.rpt', 29: 'my_soc_top_postHoldFix_place.rpt', 32: 'my_soc_top_postHoldAuto_place.rpt', 33: 'my_soc_top_postFiller_place.rpt'}
    if step in place_files:
        checks['placement'] = placement(pnr / place_files[step])
    if step == 25:
        checks['io_controls'] = helper(work, 'audit_io_ties.py')
    timing_dirs = {26: 'preCTS', 28: 'postCTS', 29: 'postCTS_holdFix_check', 32: 'postRoute_holdAuto_check', 33: 'postFiller'}
    if step in timing_dirs:
        cfg=json.loads((work/'config/design.json').read_text())
        checks['timing'] = timing(pnr / 'reports' / timing_dirs[step], step in [32,33])
        if cfg.get('analysis_profile','').startswith('matched_'):
            checks['expanded_analysis_views']={}
            for view in ['func_tt_io','func_ss_io','func_ff0_io','func_ffm40_io']:
                directory=pnr/'reports'/timing_dirs[step]/view
                pair={}
                for mode,pattern in [('Setup','*_all.tarpt.gz'),('Hold','*_all_hold.tarpt.gz')]:
                    reports=list(directory.glob(pattern))
                    if len(reports)!=1 or not load_text(reports[0]).strip():raise ValueError('Missing expanded PVT path report: '+view+' '+mode)
                    pair[mode]={'report':str(reports[0]),'analysis_view':view}
                checks['expanded_analysis_views'][view]=pair
        if step in [26, 28, 29]:
            checks['timing_scope'] = 'Pre-route diagnostic: residuals are recorded; only post-route steps32/33 require all timing/electrical targets met.'
    if step == 14:
        checks['physical_pins'] = physical_pins(work, pnr / 'my_soc_top_physicalPins.def')
    if step in [31, 32, 33]:
        stem = {31: 'postAntennaFix', 32: 'postHoldAuto', 33: 'postFiller'}[step]
        checks['default_drc'] = require_clean_report(pnr / ('my_soc_top_' + stem + '_drc.rpt'), 'drc')
        checks['signal_connectivity'] = signal_connectivity(work, pnr / ('my_soc_top_' + stem + '_signal.rpt'))
        # Full PG must be clean by final fill; early reports remain available.
        if step == 33:
            checks['full_core_pg'] = require_clean_report(pnr / 'my_soc_top_postFiller_pg.rpt', 'connectivity')
        ant = pnr / ('my_soc_top_' + stem + '_antenna.rpt')
        if antenna_count(ant):
            raise ValueError('Antenna violations remain: ' + str(ant))
        checks['antenna'] = {'report': str(ant), 'violating_nets': 0}
    if step == 34:
        audit_step(work, 33)
        checks['exports'] = export_audit(work)
    identity = hashlib.sha256((work / 'evidence/input_manifest.json').read_bytes()).hexdigest()
    archive_report_references(work, step, checks)
    record = {'step': step, 'commands_completed': True, 'input_manifest_sha256': identity, 'automatic_checks': checks, 'scope': 'Only the listed automatic checks are asserted. Tcl guards also check object counts, IO geometry and halo. Not complete signoff.'}
    save(work / 'evidence' / ('step_%02d.json' % step), record)
    return record
