"""Read saved mapped reports/netlist and correlate inactive clocks with ICGs.

No technology files, RTL, netlist or original reports are modified. Generate the
gate list first, query it with clock_coverage.tcl in a restored Genus session,
then rerun with --coverage-dir pointing to that independent query's outputs.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--work-dir', type=Path, required=True)
    cli.add_argument('--coverage-dir', type=Path, required=True)
    cli.add_argument('--output', type=Path, required=True)
    args = cli.parse_args()
    reports = args.work_dir / 'reports'
    netlist = args.work_dir / 'outputs/my_soc_top_postsyn.v'
    text = netlist.read_text()
    intent = (reports / 'timing_intent_final.rpt').read_text()
    section = intent.split('Sequential clock pins without clock waveform', 1)[1]
    section = section.split('Timing exceptions with no effect', 1)[0]
    # Include every reported clock pin, including negative-edge CPN and SRAM
    # CLK. Restricting this to /CP would silently miss a new clock problem.
    pins = re.findall(r'^pin:my_soc_top/(\S+)$', section, re.M)
    lint_counts = re.findall(r'Sequential clock pins without clock waveform[ \t]+(\d+)', intent)
    assert lint_counts and len(pins) == int(lint_counts[-1]), (len(pins), lint_counts)
    modules = {}
    for match in re.finditer(r'(?ms)^\s*module\s+(\S+?)\s*\(.*?^\s*endmodule', text):
        instances = {}
        for cell in re.finditer(r'(?ms)^\s*([A-Za-z_$][\w$]*)\s+(\\\S+|[A-Za-z_$][\w$]*)\s*\((.*?)\);', match[0]):
            kind, name, ports = cell.groups()
            if kind == 'module':
                continue
            connections = dict((p.strip(), v.strip()) for p, v in re.findall(r'\.([^\s(]+)\s*\((.*?)\)\s*(?:,|$)', ports, re.S))
            instances[name.lstrip('\\')] = (kind, connections)
        modules[match[1]] = instances
    gate_counts = Counter()
    test_values = {}
    for name in pins:
        parts = name.split('/')
        module = 'my_soc_top'
        for instance in parts[:-2]:
            module = modules[module][instance][0]
        clock = modules[module][parts[-2]][1][parts[-1]]
        drivers = [(i, p) for i, (kind, p) in modules[module].items()
                   if kind.startswith('RC_CG_MOD') and p.get('ck_out') == clock]
        assert len(drivers) == 1, (name, drivers)
        instance, ports = drivers[0]
        gate = '/'.join(parts[:-2] + [instance, 'RC_CGIC_INST', 'E'])
        gate_counts[gate] += 1
        test_values[gate] = ports['test']
    args.coverage_dir.mkdir(parents=True, exist_ok=True)
    gate_file = args.coverage_dir / 'gates.tcl'
    gate_file.write_text('set inactive_gate_enable_pins [list ' + ' '.join('{' + x + '}' for x in gate_counts) + ']\n')
    enable_values = {}
    for name in ('gate_console.log', 'cdc_console.log'):
        log = args.coverage_dir / name
        if log.exists():
            enable_values.update(re.findall(r'^CLOCK_GATE_ENABLE (\S+) computed=(\S+)$', log.read_text(), re.M))
    evidence = {str(netlist): sha(netlist), str(reports / 'timing_intent_final.rpt'): sha(reports / 'timing_intent_final.rpt')}
    for name in ('gate_console.log', 'cdc_console.log'):
        log = args.coverage_dir / name
        if log.exists():
            evidence[str(log)] = sha(log)
    cdc = {}
    for name in ('cdc_jtag_to_sys.rpt', 'cdc_sys_to_jtag.rpt'):
        path = args.coverage_dir / name
        if path.exists():
            report = path.read_text()
            slacks = [float(x) for x in re.findall(r'Slack:=\s+(-?[\d.]+)', report)]
            cdc[name] = {'reported_paths': len(slacks), 'worst_reported_slack_ps': min(slacks) if slacks else None,
                         'max_delay_exception_references': report.count('max_delay')}
            evidence[str(path)] = sha(path)
    result = {
        'scope': 'Read-only audit of the identified mapped netlist, not a new synthesis or physical/CDC signoff',
        'clockless_pins': len(pins),
        'mapped_clockless_pins': sum(gate_counts.values()),
        'inactive_gates': [{'enable_pin': g, 'clockless_flops': n, 'computed_enable': enable_values.get(g),
                            'netlist_test_enable': test_values[g]} for g, n in sorted(gate_counts.items())],
        'all_clockless_pins_explained_by_disabled_icg': all(enable_values.get(g) == '0' and test_values[g] == "1'b0" for g in gate_counts),
        'cdc': cdc,
        'sha256': evidence,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: result[k] for k in ('clockless_pins', 'mapped_clockless_pins', 'all_clockless_pins_explained_by_disabled_icg', 'cdc')}))


if __name__ == '__main__':
    main()
