"""Developer check for an ISOLATED, idle prepared work directory only.

Temporarily mutates then restores user_define.tcl to test resume protection.
Never run this against an active implementation project.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work', type=Path, required=True)
    parser.add_argument('--entry', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    work = args.work.resolve()
    if (work / 'evidence/flow.lock').exists() or (work / 'evidence/last_step.txt').exists():
        raise ValueError('Use an isolated, idle preparation-only validation project')
    files = list((work / 'flow').rglob('*.tcl'))
    for p in files:
        command = 'set f [open {' + str(p) + '} r]; set s [read $f]; close $f; puts [info complete $s]\n'
        result = subprocess.run(['tclsh'], input=command, universal_newlines=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode or result.stdout.strip() != '1' or result.stderr:
            raise ValueError('Tcl incomplete: ' + str(p))
    target = work / 'config/user_define.tcl'
    original = target.read_bytes()
    try:
        target.write_bytes(original + b'\n# temporary compatibility validation mutation\n')
        result = subprocess.run(['bash', str(args.entry), 'status', '--work', str(work)], universal_newlines=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode == 0 or 'Inputs changed' not in result.stderr:
            raise ValueError('Changed inputs did not invalidate resume')
    finally:
        target.write_bytes(original)
    result = subprocess.run(['bash', str(args.entry), 'status', '--work', str(work)], universal_newlines=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode:
        raise ValueError('Exact restoration did not recover input identity: ' + result.stderr)
    doctor = json.loads((work / 'evidence/doctor.json').read_text())
    record = {'validation_python': sys.version.split()[0], 'controller_python': doctor['python'], 'tcl_complete_files': len(files), 'fresh_prepare': True, 'doctor_library_files': len(doctor['libraries_sha256']), 'input_mutation_rejected': True, 'exact_input_restore_passed': True, 'controller_sha256': hashlib.sha256((work / 'flow/bin/flow.py').read_bytes()).hexdigest(), 'remote_work': str(work), 'scope': 'Preparation and controller compatibility only; no Genus/Innovus execution in this test'}
    record['input_manifest_sha256'] = hashlib.sha256((work / 'evidence/input_manifest.json').read_bytes()).hexdigest()
    record['control_files_sha256'] = {p.relative_to(work / 'flow').as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((work / 'flow').rglob('*')) if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc'}
    args.output.write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps(record))


if __name__ == '__main__':
    main()
