"""Choose native combinational masters whose TT delay tables are nonnegative.

This changes mapped hardware, never a Liberty/SDF value or timing exception.
Actual post-route SDF must still be checked: table selection alone cannot prove
the absence of negative calculated delays or extrapolation at operating points.
"""
import hashlib
import json
from pathlib import Path
import re


NUMBER = r'[-+]?(?:\d+\.\d*|\.\d+|\d+)(?:[eE][-+]?\d+)?'


def negative_combinational_masters(text):
    starts = list(re.finditer(r'\bcell\s*\(\s*"?([A-Za-z0-9_]+)"?\s*\)\s*\{', text))
    if not starts:
        raise ValueError('No native Liberty cell definitions found')
    excluded = {}
    table_cells = 0
    for i, match in enumerate(starts):
        body = text[match.end():starts[i+1].start() if i+1<len(starts) else len(text)]
        if re.search(r'\b(?:ff|ff_bank|latch|latch_bank)\s*\(', body):
            continue  # Sequential mapping has its own independently checked policy.
        values = []
        for table in re.finditer(r'\bcell_(?:rise|fall)\s*\([^)]*\)\s*\{([^{}]*)\}', body, re.S):
            data = re.search(r'\bvalues\s*\((.*?)\)\s*;', table.group(1), re.S)
            if data:
                values.extend(float(x) for x in re.findall(NUMBER, data.group(1)))
        if not values:
            continue
        table_cells += 1
        if min(values) < 0:
            excluded[match.group(1)] = {'minimum_native_TT_table_delay_ns': min(values),
                                        'negative_table_entries': sum(v < 0 for v in values)}
    if not table_cells or not excluded:
        raise ValueError('TT table policy did not identify the expected native combinational tables')
    return excluded, table_cells


def prepare_mapping(work, config):
    mode = config['combinational_cell_mapping']
    report = {'mapping': mode, 'timing_values_modified': False,
              'timing_exceptions_added': False, 'postroute_SDF_still_requires_measurement': True}
    masters = {}
    if mode == 'tt_nonnegative_tables':
        paths = list(Path(config['pdk_root']).glob(
            'tcb018gbwp7t_290a/TSMCHOME/digital/Front_End/timing_power_noise/NLDM/tcb018gbwp7t_270a/*tc.lib'))
        if len(paths) != 1:
            raise ValueError('Expected exactly one matching native standard-cell TT library')
        raw = paths[0].read_bytes()
        masters, count = negative_combinational_masters(raw.decode('utf-8'))
        report.update(native_TT_library=str(paths[0]), native_TT_library_sha256=hashlib.sha256(raw).hexdigest(),
                      combinational_cells_with_tables=count, excluded_native_masters=masters)
    report['excluded_master_count'] = len(masters)
    (work/'flow/config/combinational_mapping.tcl').write_text(
        '# Generated from the unmodified native TT library; not an SDF edit.\n'
        'set ::eda_tt_negative_table_masters {%s}\n' % ' '.join(sorted(masters)), encoding='utf-8')
    (work/'evidence/combinational_mapping_policy.json').write_text(
        json.dumps(report, indent=2)+'\n', encoding='utf-8')
    return report
