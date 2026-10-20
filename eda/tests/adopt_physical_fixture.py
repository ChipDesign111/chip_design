"""Developer-only continuation from an idle, PASSED step31 checkpoint.

Preserve original early-stage input IDs; do not re-label them as fresh execution.
Only for equivalent RTL/synthesis/PNR configuration and a new control program.
Normal users should run the documented complete flow from RTL.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--reference', type=Path, required=True)
p.add_argument('--work', type=Path, required=True)
a = p.parse_args()
reference, work = a.reference.resolve(), a.work.resolve()
spec = importlib.util.spec_from_file_location('eda_fixture_flow', str(work / 'flow/bin/flow.py'))
flow = importlib.util.module_from_spec(spec)
spec.loader.exec_module(flow)
for root in [reference, work]:
    if (root / 'evidence/flow.lock').exists():
        raise ValueError('Both projects must be idle')
    flow.verify_inputs(root)
    flow.verify_libraries(root)
if int((reference / 'evidence/last_step.txt').read_text()) != 31:
    raise ValueError('This fixture importer supports the passed step31 state only')
if (work / 'evidence/synthesis_status.json').exists() or (work / 'evidence/last_step.txt').exists():
    raise ValueError('Use a fresh prepared + doctor-only target')
if (reference / 'evidence/unexpected_tool_errors.json').exists():
    raise ValueError('Reference has unresolved tool errors')

def normalized(path, root):
    return '\n'.join(x.strip() for x in path.read_text().replace(str(root), '<WORK>').splitlines() if x.strip())

old = {str(p.relative_to(reference)) for p in (reference / 'pnr/scripts').rglob('*') if p.is_file()}
new = {str(p.relative_to(work)) for p in (work / 'pnr/scripts').rglob('*') if p.is_file()}
if old != new or any(normalized(reference / n, reference) != normalized(work / n, work) for n in old):
    raise ValueError('PNR input scripts differ')
subprocess.run([sys.executable, str(Path(__file__).with_name('adopt_synthesis_fixture.py')), '--reference', str(reference), '--work', str(work)], check=True)

source = reference / 'pnr/my_soc_top'
target = work / 'pnr/my_soc_top'
for path in source.iterdir():
    if path.is_file() and path.suffix in ['.rpt', '.v', '.def', '.io', '.txt'] and 'postHoldAuto' not in path.name:
        shutil.copyfile(str(path), str(target / path.name))
for name in ['preCTS', 'postCTS', 'postCTS_holdFix', 'postCTS_holdFix_check']:
    if (source / 'reports' / name).is_dir():
        shutil.copytree(str(source / 'reports' / name), str(target / 'reports' / name))

inherited = {}
for step in range(1, 32):
    name = 'step_%02d.json' % step
    original = reference / 'evidence' / name
    record = json.loads(original.read_text())
    if not record['commands_completed'] or record['input_manifest_sha256'] != flow.sha(reference / 'evidence/input_manifest.json'):
        raise ValueError('Reference early-stage evidence identity mismatch')
    inherited[str(step)] = flow.sha(original)
    shutil.copyfile(str(original), str(work / 'evidence' / name))
    for folder in ['commands', 'stage_reports']:
        old_dir = reference / 'evidence' / folder / ('%02d' % step)
        if old_dir.is_dir():
            shutil.copytree(str(old_dir), str(work / 'evidence' / folder / ('%02d' % step)))
for name in ['geometry.json', 'current_macro.txt', '08_topology.json', '11_pg_topology.json', 'native_io_gds.json', 'native_io_rails_check.json']:
    path = reference / 'evidence' / name
    if path.exists():
        shutil.copyfile(str(path), str(work / 'evidence' / name))
reference_logs = {}
for path in (reference / 'evidence').glob('innovus_*_to_*.log'):
    match = re.fullmatch(r'innovus_\d+_to_(\d+)\.log', path.name)
    if match and int(match.group(1)) <= 31:
        body = path.read_text(errors='replace')
        if 'EDA_REQUEST_COMPLETE' not in body or 'EDA_STAGE_FAILED' in body:
            raise ValueError('Incomplete source log for inherited prefix: ' + path.name)
        destination = work / 'evidence/reference_logs' / path.name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(str(path), str(destination))
        reference_logs[path.name] = {'source': str(path), 'sha256': flow.sha(destination), 'bytes': destination.stat().st_size}
flow.write_json(work / 'evidence/reference_logs_manifest.json', reference_logs)

checkpoint = Path('pnr/my_soc_top/backup/step31.enc')
shutil.copyfile(str(reference / checkpoint), str(work / checkpoint))
data = Path(str(checkpoint) + '.dat')
shutil.copytree(str(reference / data), str(work / data))
seed = {}
for path in [work / checkpoint] + [p for p in (work / data).rglob('*') if p.is_file()]:
    relative = path.relative_to(work).as_posix()
    digest = flow.sha(path)
    if digest != flow.sha(reference / relative):
        raise ValueError('Seed database copy mismatch: ' + relative)
    seed[relative] = digest
fixture = {'scope': 'Imported passed physical step31 for corrected postRoute-control validation; steps01-31 were executed in the reference, not rerun here', 'seed_step': 31, 'reference_work': str(reference), 'reference_input_manifest_sha256': flow.sha(reference / 'evidence/input_manifest.json'), 'target_input_manifest_sha256': flow.sha(work / 'evidence/input_manifest.json'), 'inherited_stage_records_sha256': inherited, 'seed_files_sha256': seed, 'RTL_and_normalized_synthesis_configuration_proof': 'synthesis_fixture.json', 'normalized_PNR_scripts_equal': True}
flow.write_json(work / 'evidence/physical_fixture.json', fixture)
# Re-measure native library rails now. Connectivity/placement reports and the
# physical state are inherited with their ORIGINAL identities, not forged IDs.
from checks import io_native
native = io_native(work)
flow.write_json(work / 'evidence/inherited_io_reaudit.json', {'scope': 'Fresh native-rail re-audit over the identical imported physical seed; not a fresh Innovus step22 execution', 'input_manifest_sha256': fixture['target_input_manifest_sha256'], 'source_step22_sha256': inherited['22'], 'automatic_checks': {'io_native_geometry': native}})
(work / 'evidence/last_step.txt').write_text('31\n')
preparation = json.loads((work / 'evidence/preparation.json').read_text())
preparation.update(physical_seed_step=31, physical_seed_reference=str(reference), early_steps_reexecuted_here=False)
flow.write_json(work / 'evidence/preparation.json', preparation)
flow.sizing(work)
flow.verify_inputs(work)
flow.report(work)
print('Validated physical seed adopted at step31; original source records and input manifests preserved')
