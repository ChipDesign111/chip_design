"""Match this small probe's source SDF requests to Xcelium annotation rows."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work', type=Path, required=True)
    args = parser.parse_args()
    sdf_path = args.work / 'mapped.sdf'
    log_path = args.work / 'simulation_console.log'
    sdf = sdf_path.read_text()
    log = log_path.read_text()
    requests = Counter(re.findall(r'\((SETUPHOLD|RECREM|WIDTH)\b', sdf))
    rows = {}
    for kind, potential, disabled, annotated in re.findall(r'^\s*\$(\w+)\s+(\d+)\s+(\d+)\s+(\d+)\s+[\d.]+\s*$', log, re.M):
        rows[kind.upper()] = {'model_potential': int(potential), 'disabled': int(disabled), 'annotated': int(annotated)}
    counts_match = all(rows[k]['annotated'] == count for k, count in requests.items())
    source_paths = len(re.findall(r'\(IOPATH\b', sdf))
    path_stats = re.search(r'Path Delays\s+(\d+)\s+(\d+)\s+(\d+)\s+[\d.]+', log)
    paths_match = bool(path_stats) and int(path_stats[3]) == source_paths
    warnings = re.findall(r'^.*\*[WEF],SDF[^\n]*$', log, re.M)
    result = {
        'scope': 'Small reset-phase probe only; not complete SoC SDF acceptance',
        'source_sdf_requests': dict(requests), 'source_iopath_requests': source_paths,
        'model_annotation_rows': rows, 'source_requests_all_annotated': counts_match and paths_match,
        'sdf_warnings_or_errors': warnings,
        'timing_violation_count': len(re.findall('Timing violation', log, re.I)),
        'reset_release_times_ns': re.findall(r'RESET_RELEASE time_ns=([\d.]+)', log),
        'known_states': re.findall(r'RESET_PHASE_STATE counter=(\S+) known=(\d+)', log),
        'sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (sdf_path, log_path)},
    }
    (args.work / 'annotation_audit.json').write_text(json.dumps(result, indent=2) + '\n')
    assert result['source_requests_all_annotated'] and not warnings, result
    print(json.dumps(result))


if __name__ == '__main__':
    main()
