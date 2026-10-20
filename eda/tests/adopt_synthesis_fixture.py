"""Developer verification only: reuse identical synthesis inputs in a NEW work.

Never edits either work's input manifest or claims a fresh Genus execution.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import shutil

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--reference', type=Path, required=True)
p.add_argument('--work', type=Path, required=True)
a = p.parse_args()
ref, work = a.reference.resolve(), a.work.resolve()
spec = importlib.util.spec_from_file_location('eda_current_flow', str(work / 'flow/bin/flow.py'))
flow = importlib.util.module_from_spec(spec)
spec.loader.exec_module(flow)
for root in [ref, work]:
    if (root / 'evidence/flow.lock').exists():
        raise ValueError('Reference and target must both be idle')
    flow.verify_inputs(root)
    flow.verify_libraries(root)
if (work / 'evidence/synthesis_status.json').exists() or (work / 'evidence/last_step.txt').exists():
    raise ValueError('Target must be fresh prepared + doctor only')
if not json.loads((ref / 'evidence/synthesis_status.json').read_text())['commands_completed']:
    raise ValueError('Reference synthesis incomplete')

def normalized(path, root):
    text = path.read_text().replace(str(root), '<WORK>')
    return '\n'.join(line.strip() for line in text.splitlines() if line.strip())

compared = []
for directory in ['config', 'syn/scripts', 'src/chip_design/rtl']:
    old_files = {str(p.relative_to(ref)) for p in (ref / directory).rglob('*') if p.is_file() and p.name not in ['eda_elaborate.tcl', 'eda_synthesis.tcl']}
    new_files = {str(p.relative_to(work)) for p in (work / directory).rglob('*') if p.is_file() and p.name not in ['eda_elaborate.tcl', 'eda_synthesis.tcl']}
    if old_files != new_files:
        raise ValueError('Synthesis input file sets differ: ' + directory)
    for name in sorted(old_files):
        left, right = ref / name, work / name
        equal = left.read_bytes() == right.read_bytes() if directory.startswith('src/') else normalized(left, ref) == normalized(right, work)
        if not equal:
            raise ValueError('Synthesis inputs differ beyond whitespace/work-root: ' + name)
        compared.append(name)
if normalized(ref / 'src/filelist_syn.f', ref) != normalized(work / 'src/filelist_syn.f', work):
    raise ValueError('RTL list/defines differ')

def library_identity(root):
    data = json.loads((root / 'evidence/doctor.json').read_text())['libraries_sha256']
    return {name.replace(str(root), '<WORK>'): digest for name, digest in data.items()}
if library_identity(ref) != library_identity(work):
    raise ValueError('Library identities differ')

files = {}
source = ref / 'syn/my_soc_top'
target = work / 'syn/my_soc_top'
for path in list(source.glob('*.v')) + list(source.glob('*.sdc')) + list(source.glob('*.sdf')) + list((source / 'reports').rglob('*')) + list((source / 'backup').glob('*.sdc')):
    if not path.is_file():
        continue
    dest = target / path.relative_to(source)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(str(path), str(dest))
    if flow.sha(path) != flow.sha(dest):
        raise ValueError('Copy mismatch')
    files[str(dest.relative_to(work))] = {'bytes': dest.stat().st_size, 'sha256': flow.sha(dest)}

record = {'scope': 'Reused mapped synthesis fixture for current-controller PNR smoke test, NOT a fresh Genus run in this target work',
          'reference_work': str(ref), 'reference_input_manifest_sha256': flow.sha(ref / 'evidence/input_manifest.json'),
          'target_input_manifest_sha256': flow.sha(work / 'evidence/input_manifest.json'),
          'rtl_byte_identity_and_normalized_synthesis_config_checked': compared,
          'library_identity_equal': True, 'copied_files': files}
flow.write_json(work / 'evidence/synthesis_fixture.json', record)
value = json.loads((ref / 'evidence/synthesis.json').read_text())
value['report'] = str(work / 'syn/my_soc_top/reports/area/area.rpt')
flow.write_json(work / 'evidence/synthesis.json', value)
flow.write_json(work / 'evidence/synthesis_status.json', {'commands_completed': True, 'reused_validated_fixture': True, 'fresh_Genus_executed_here': False, 'reference_work': str(ref), 'scope': record['scope']})
flow.verify_inputs(work)
print('Validated and copied same-input synthesis fixture; no input manifest changed')
