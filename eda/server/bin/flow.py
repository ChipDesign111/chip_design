#!/usr/bin/env python3
"""Python 3.8+ deployment and staged implementation for the INT8 tiled SoC."""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone, timedelta
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import signal
import socket
import subprocess
import sys
import tarfile

if sys.version_info < (3, 8):
    raise SystemExit('EDA requires Python 3.8+. Use bash server/bin/eda.sh or set EDA_PYTHON to a supported interpreter.')

SERVER = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVER / 'tools'))
from checks import audit_step, area_summary, load_text, mapped_netlist_check, clear_step_outputs, timing
from generate import generate_steps
from cleanup import clean_work, generated_path, remove_generated


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + '.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    os.replace(str(temp), str(path))


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for data in iter(lambda: stream.read(1048576), b''):
            h.update(data)
    return h.hexdigest()


def tcl(value):
    return '"' + str(value).replace('\\', '\\\\').replace('$', '\\$').replace('[', '\\[').replace(']', '\\]').replace('"', '\\"').replace('\n', '\\n') + '"'


def read_config(path):
    c = json.loads(path.read_text(encoding='utf-8'))
    if c['schema'] != 1 or c['top'] != 'my_soc_top' or c['profile'] != 'xzx_int8_tiled_tsmc180':
        raise ValueError('This implementation profile supports only the documented xzx INT8 my_soc_top')
    for key in ['system_period_ns', 'target_utilization', 'min_core_size_um', 'core_margin_um']:
        if not isinstance(c[key], (int, float)) or not math.isfinite(c[key]) or c[key] <= 0:
            raise ValueError('Invalid numeric configuration: ' + key)
    if not 0 < c['target_utilization'] <= 1 or not isinstance(c['cpus'], int) or not 1 <= c['cpus'] <= 16:
        raise ValueError('Expected utilization fraction in (0,1] and CPU count in 1..16')
    c.setdefault('optimizer_max_density', c['target_utilization'])
    density=c['optimizer_max_density']
    if not isinstance(density,(int,float)) or not math.isfinite(density) or not 0<density<=1:
        raise ValueError('Optimizer density must be a finite fraction in (0,1]')
    if c.get('acceptance_profile') != 'native_library_zero_slack':
        raise ValueError('Use the current native-library, zero-slack acceptance configuration')
    obsolete={'min_hold_slack_ns','postroute_setup_target_ns','hold_optimizer_max_density'} & set(c)
    if obsolete:raise ValueError('Remove retired custom acceptance/budget keys: '+','.join(sorted(obsolete)))
    if c['min_core_size_um'] < 1500 or c['core_margin_um'] != 150:
        raise ValueError('Validated perimeter profile requires core >=1500 um and 150 um margins')
    if not isinstance(c.get('max_die_area_mm2'),(int,float)) or not math.isfinite(c['max_die_area_mm2']) or not 0<c['max_die_area_mm2']<=4.0:
        raise ValueError('This design requires a finite whole-die limit at most 4.0 mm2')
    if c['core_size_um'] is not None and c['core_size_um'] < c['min_core_size_um']:
        raise ValueError('Fixed core size is below profile minimum')
    if c['cpu_clock_gate'] != 'repository_passthrough':
        raise ValueError('Changing CPU clock gating requires a separate validated profile')
    if c['analysis_profile'] not in ['single_TT_SI_off_native_low_RC','matched_TT_SS_FF0_FFm40_SI_off_native_low_RC']:
        raise ValueError('Unknown library PVT profile')
    if not isinstance(c['max_repair_iterations'], int) or not 1 <= c['max_repair_iterations'] <= 10 or c['hold_target_ns'] not in [0,0.02]:
        raise ValueError('Invalid repair iteration count/target')
    if len(c['macro_xy_um']) != 2 or any(not isinstance(x, (int, float)) or not math.isfinite(x) or x < 200 for x in c['macro_xy_um']):
        raise ValueError('Macro coordinates must leave room for core rings and halo')
    return c


def package_root():
    # Deployment archives contain server/ and rtl/ at the same level.
    if (SERVER.parent / 'rtl/filelist.f').is_file():
        return SERVER.parent
    if (SERVER.parents[1] / 'rtl/filelist.f').is_file():
        return SERVER.parents[1]
    raise ValueError('Missing deployed rtl/. Use eda/package_server.py to build the archive')


def fingerprint_inputs(work):
    paths = []
    for folder in ['src', 'config', 'flow', 'syn/scripts', 'pnr/scripts']:
        for p in (work / folder).rglob('*'):
            if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc' and p.name not in ['eda_elaborate.tcl', 'eda_synthesis.tcl']:
                paths.append(p)
    return {p.relative_to(work).as_posix(): sha(p) for p in sorted(paths)}


def verify_inputs(work):
    expected = json.loads((work / 'evidence/input_manifest.json').read_text(encoding='utf-8'))
    actual = fingerprint_inputs(work)
    if expected != actual:
        differences = [p for p in sorted(set(expected) | set(actual)) if expected.get(p) != actual.get(p)]
        raise ValueError('Inputs changed; prepare a NEW work directory: ' + ', '.join(differences[:12]))


def prepare(args):
    root = package_root()
    provenance_path = root / 'source.json'
    if provenance_path.is_file():
        deployed = json.loads(provenance_path.read_text(encoding='utf-8'))
        for name, expected in deployed['files'].items():
            p = (root / name).resolve()
            p.relative_to(root.resolve())
            if not p.is_file() or sha(p) != expected['sha256']:
                raise ValueError('Deployment content changed: ' + name)
    config_path = Path(args.config).resolve() if args.config else SERVER / 'config/design.json'
    config = read_config(config_path)
    work = Path(args.work).expanduser().resolve()
    if not re.fullmatch(r'[A-Za-z0-9_./-]+', str(work)):
        raise ValueError('Use an absolute Linux work path without spaces or Tcl metacharacters')
    if work.exists():
        raise ValueError('Work directory already exists; choose a NEW path: ' + str(work))
    pdk = Path(config['pdk_root']).expanduser().resolve()
    macro = Path(config['macro_source']).expanduser().resolve()
    if not pdk.is_dir() or not macro.is_dir():
        raise ValueError('PDK/macro source missing; edit your COPY of server/config/design.json')
    names = ['RA1SHD_2048x32M8_tt_1p8_25C_syn.lib', 'RA1SHD_2048x32M8.vclef', 'RA1SHD_2048x32M8_ant.lef']
    if not all((macro / name).is_file() for name in names) or not list(macro.glob('*.gds*')):
        raise ValueError('Incomplete native macro views: ' + str(macro))
    work.mkdir(parents=True)
    shutil.copytree(str(SERVER), str(work / 'flow'), ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    shutil.copytree(str(root / 'rtl'), str(work / 'src/chip_design/rtl'))
    shutil.copytree(str(macro), str(work / 'src/macro/RA1SHD_2048x32M8'))
    (work / 'config').mkdir()
    for name in ['user_define.tcl', 'global_define.tcl', 'constraints_my_soc_top.sdc']:
        shutil.copyfile(str(work / 'flow/config' / name), str(work / 'config' / name))
    for name in ['syn', 'pnr']:
        shutil.copytree(str(work / 'flow' / name), str(work / name))
    (work / 'config/design.json').write_text(json.dumps(config, indent=2) + '\n', encoding='utf-8')
    shutil.copyfile(str(SERVER / 'config/io_plan.json'), str(work / 'config/io_plan.json'))
    (work / 'flow/config/repair.tcl').write_text('set eda_repair_iterations %d\nset eda_hold_target %g\n' % (config['max_repair_iterations'],config['hold_target_ns']),encoding='utf-8')
    user = work / 'config/user_define.tcl'
    text = user.read_text(encoding='utf-8')
    for key, value in [('PROJECT_ROOT', tcl(work)), ('PDK_ROOT', tcl(pdk)), ('rm_clock_period', config['system_period_ns']), ('eda_opt_max_density', config['optimizer_max_density']), ('syn_cpus', config['cpus']), ('pnr_cpus', config['cpus'])]:
        text, n = re.subn(r'^set ' + key + r' .*$', lambda match: 'set ' + key + ' ' + str(value), text, flags=re.M)
        if n != 1:
            raise ValueError('Project configuration variable missing: ' + key)
    text+='\nset eda_enable_pvt %d\n'%int(config['analysis_profile'].startswith('matched_'))
    user.write_text(text, encoding='utf-8')
    listed, includes, lines = [], [], ['+define+SYNTHESIS', '+define+CHIP_USE_RA1SHD']
    rtl = work / 'src/chip_design'
    for raw in (root / 'rtl/filelist.f').read_text(encoding='utf-8').splitlines():
        line = raw.strip()
        if not line or line.startswith(('#', '//')):
            continue
        if line.startswith('+incdir+'):
            relative = line[8:]
            if not (rtl / relative).is_dir():
                raise ValueError('Missing include: ' + line)
            includes.append(relative)
            lines.append('+incdir+' + str(rtl / relative))
        else:
            path = (rtl / line).resolve()
            path.relative_to(rtl.resolve())
            if not path.is_file() or path.name == 'ra1shd_blackbox.sv':
                raise ValueError('Invalid synthesis source: ' + line)
            listed.append(line)
            lines.append(str(path))
    if len(set(listed)) != len(listed) or not all(x in listed for x in ['rtl/soc/my_soc_top.sv','rtl/npu/har_npu_core.sv','rtl/dma/har_dma.sv','rtl/memory/bootram.sv','rtl/cpu_cv32e40p/rtl/cv32e40p_core.sv']):
        raise ValueError('Duplicate sources or missing required CPU/NPU/DMA/boot integration')
    (work / 'src/filelist_syn.f').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    for folder in ['syn/logs', 'pnr/logs', 'pnr/generated', 'pnr/my_soc_top/backup', 'pnr/my_soc_top/reports', 'syn/my_soc_top/backup', 'evidence']:
        (work / folder).mkdir(parents=True, exist_ok=True)
    for folder in ['area', 'timing', 'runtime', 'time_intent', 'others', 'power']:
        (work / 'syn/my_soc_top/reports' / folder).mkdir(parents=True, exist_ok=True)
    provenance = root / 'source.json'
    if provenance.exists():
        shutil.copyfile(str(provenance), str(work / 'evidence/source.json'))
    write_json(work / 'evidence/preparation.json', {'rtl_files': len(listed), 'include_dirs': includes, 'macro_source': str(macro), 'work': str(work), 'functional_retested_here': False, 'profile_changes': ['CHIP_USE_RA1SHD and SYNTHESIS', 'absolute source paths', 'no hidden path_adjust tightening', 'guard empty async net selection', 'original CPU clock passthrough']})
    write_json(work / 'evidence/input_manifest.json', fingerprint_inputs(work))
    print('Prepared NEW project: ' + str(work))
    print('Next: bash ' + str(work / 'flow/bin/eda.sh') + ' doctor --work ' + str(work))


@contextmanager
def project_lock(work):
    path = work / 'evidence/flow.lock'
    fd = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    old_term = signal.getsignal(signal.SIGTERM)
    def terminate_request(signum, frame):
        raise RuntimeError('Received termination request; stopping this flow and its child tool')
    signal.signal(signal.SIGTERM, terminate_request)
    try:
        os.write(fd, json.dumps({'pid': os.getpid(), 'host': socket.gethostname()}).encode())
        os.close(fd)
        yield
    finally:
        signal.signal(signal.SIGTERM, old_term)
        try:
            path.unlink()
        except FileNotFoundError:
            pass


def doctor(work):
    verify_inputs(work)
    c = read_config(work / 'config/design.json')
    missing = [name for name in ['genus', 'innovus'] if not shutil.which(name)]
    libraries = list((Path(c['pdk_root'])).glob('tcb018gbwp7t_290a/TSMCHOME/digital/Front_End/timing_power_noise/NLDM/tcb018gbwp7t_270a/*tc.lib'))
    if not libraries:
        missing.append('standard-cell TT liberty')
    if missing:
        raise ValueError('Missing EDA dependencies: ' + ', '.join(missing))
    # Evaluate only variable/configuration Tcl in plain tclsh: no licenses used.
    source = 'cd ' + tcl(work / 'pnr/logs') + '\nsource ../../config/user_define.tcl\nsource ../../config/global_define.tcl\n'
    source += 'set eda_check_libs {}\nforeach c $proj(corners) {set eda_check_libs [concat $eda_check_libs $proj(library_set,$c)]}\nlappend eda_check_libs ${io_lib}tc.lib\nif {[info exists eda_enable_pvt] && $eda_enable_pvt} {foreach s {wc bc lt} {lappend eda_check_libs ${io_lib}${s}.lib}}\n'
    source += 'foreach p [concat $rm_lef_reflib $eda_check_libs $gds_list [list $rm_captable_file $rm_lef_layer_map]] {if {![file readable $p]} {error "Missing library: $p"}; puts [file normalize $p]}\n'
    result = subprocess.run(['tclsh'], input=source, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode or result.stderr.strip():
        raise ValueError('Configuration/library check failed: ' + result.stderr)
    paths = [Path(x) for x in result.stdout.splitlines() if x.startswith('/')]
    lib_hashes = {str(p): sha(p) for p in paths}
    record = {'python': sys.version.split()[0], 'genus': shutil.which('genus'), 'innovus': shutil.which('innovus'), 'libraries_sha256': lib_hashes, 'Xvfb': shutil.which('Xvfb'), 'no_eda_stage_executed': True}
    previous = work / 'evidence/doctor.json'
    if previous.exists() and json.loads(previous.read_text())['libraries_sha256'] != lib_hashes:
        raise ValueError('Library identity changed since preparation; doctor cannot re-bless old checkpoints. Prepare a new project.')
    write_json(work / 'evidence/doctor.json', record)
    print(json.dumps(record, indent=2))


def verify_libraries(work):
    path = work / 'evidence/doctor.json'
    if not path.exists():
        raise ValueError('Run doctor first; library identity must be recorded')
    for name, expected in json.loads(path.read_text())['libraries_sha256'].items():
        p = Path(name)
        if not p.is_file() or sha(p) != expected:
            raise ValueError('Library changed; use a new project: ' + name)


def logged(command, cwd, log, env=None):
    log.parent.mkdir(parents=True, exist_ok=True)
    print('Running: ' + ' '.join(str(x) for x in command), flush=True)
    print('Console log: ' + str(log), flush=True)
    with log.open('w', encoding='utf-8') as out:
        proc = subprocess.Popen([str(x) for x in command], cwd=str(cwd), stdout=out, stderr=subprocess.STDOUT, env=env, start_new_session=(os.name == 'posix'))
        process_record = {'pid': proc.pid, 'host': socket.gethostname(), 'command': [str(x) for x in command], 'completed': False}
        record_path = log.parent / 'tool_process.json'
        write_json(record_path, process_record)
        lock = log.parent / 'flow.lock'
        if lock.is_file():
            value = json.loads(lock.read_text()); value['tool_pid'] = proc.pid
            write_json(lock, value)
        try:
            code = proc.wait()
        except BaseException:
            if proc.poll() is None:
                if os.name == 'posix':
                    os.killpg(proc.pid, signal.SIGTERM)
                else:
                    proc.terminate()
                try:
                    proc.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    if os.name == 'posix':
                        os.killpg(proc.pid, signal.SIGKILL)
                    else:
                        proc.kill()
                    proc.wait()
            raise
        finally:
            process_record.update(completed=proc.poll() is not None, exit_code=proc.poll())
            write_json(record_path, process_record)
    if code:
        raise RuntimeError('Tool exited %d; inspect %s' % (code, log))
    return load_text(log)


def synth(work, elaborate_only=False):
    verify_inputs(work)
    verify_libraries(work)
    target = work / 'syn/my_soc_top/my_soc_top_postsyn.v'
    if target.exists() and not elaborate_only:
        raise ValueError('Synthesis output already exists; prepare a new project for a new run')
    if elaborate_only:
        script = work / 'syn/scripts/eda_elaborate.tcl'
        script.write_text('source ../../config/user_define.tcl\nsource ../../config/global_define.tcl\nsource ../scripts/init_syn_standard_opt.tcl\ncheck_design -all > ../../evidence/elaborate_check.rpt\nputs "EDA_ELABORATE_COMPLETE"\nexit\n', encoding='utf-8')
    else:
        script = work / 'syn/scripts/eda_synthesis.tcl'
        script.write_text('source ../scripts/genus_synthesis.tcl\nputs "EDA_SYNTHESIS_COMPLETE"\nexit\n', encoding='utf-8')
    text = logged(['genus', '-abort_on_error', '-f', script, '-log', 'eda_elaborate' if elaborate_only else 'eda_synthesis', '-overwrite'], work / 'syn/logs', work / 'evidence' / ('genus_elaborate.log' if elaborate_only else 'genus_synthesis.log'))
    marker = 'EDA_ELABORATE_COMPLETE' if elaborate_only else 'EDA_SYNTHESIS_COMPLETE'
    if marker not in text or re.search(r'^\s*(Error|Fatal)\s*:', text, re.M | re.I):
        raise RuntimeError('Genus did not complete cleanly; inspect the console and check_design reports')
    if not elaborate_only:
        if not target.is_file() or 'RA1SHD_2048x32M8' not in load_text(target):
            raise ValueError('Missing mapped netlist/native SRAM')
        for name in ['har_npu_core', 'i_npu_subsystem', 'i_dma']:
            if name in ['i_npu_subsystem', 'i_dma'] and name not in load_text(target):
                print('NOTE: hierarchy name absent after optimization; inspect hierarchy/area report: ' + name)
        write_json(work / 'evidence/synthesis.json', dict(area_summary(work / 'syn/my_soc_top/reports/area/area.rpt'), mapped_design=mapped_netlist_check(work)))
    write_json(work / 'evidence' / ('elaboration_status.json' if elaborate_only else 'synthesis_status.json'), {'commands_completed': True, 'check_design_review_required': True, 'scope': 'Fresh tool execution, not functional equivalence or physical signoff'})


def sizing(work):
    c = read_config(work / 'config/design.json')
    area = area_summary(work / 'syn/my_soc_top/reports/area/area.rpt')
    # Cell area already includes the native main SRAM. Subtract it once and
    # reserve macro+halo separately; never include net area as cell area.
    macro_area = 554.595 * 723.85
    logic_area = max(0, area['cell_area_um2'] - macro_area)
    reserved_macro = (554.595 + 52) * (723.85 + 52)
    wanted = logic_area / c['target_utilization'] + reserved_macro
    side = c['core_size_um'] or max(c['min_core_size_um'], math.ceil(math.sqrt(wanted) / 10) * 10)
    # Preserve measured inputs and an explicit failed planning result too.
    # The existence of this report is not a pass marker; sizing must return.
    preliminary=dict(area, standard_cell_area_estimate_um2=logic_area,
        reserved_macro_halo_um2=reserved_macro, requested_core_size_um=side,
        required_core_area_um2=wanted, target_utilization=c['target_utilization'],
        planned_whole_die_area_mm2=(side+2*c['core_margin_um'])**2/1e6,
        max_whole_die_area_mm2=c['max_die_area_mm2'],
        planning_pass=False, planning_only_not_timing_or_IR_proof=True)
    write_json(work / 'evidence/floorplan_plan.json', preliminary)
    if side * side < wanted:
        raise ValueError('Core planning failed: %.0f um2 required, %.0f um2 available; standard cells %.0f um2 at utilization %.2f. See floorplan_plan.json; use a NEW configuration/project.' % (wanted,side*side,logic_area,c['target_utilization']))
    x, y = c['macro_xy_um']
    if x < c['core_margin_um'] + 50 or y < c['core_margin_um'] + 50 or x + 554.595 + 30 > side + c['core_margin_um'] or y + 723.85 + 30 > side + c['core_margin_um']:
        raise ValueError('Macro + halo does not fit the planned core')
    planned_die_area=(side+2*c['core_margin_um'])**2/1e6
    if planned_die_area>c['max_die_area_mm2']:
        raise ValueError('Whole die including PAD exceeds area limit: %.6f mm2' % planned_die_area)
    record = dict(area, planning_pass=True, required_core_area_um2=wanted, planned_whole_die_area_mm2=planned_die_area, max_whole_die_area_mm2=c['max_die_area_mm2'], standard_cell_area_estimate_um2=logic_area, reserved_macro_halo_um2=reserved_macro, target_utilization=c['target_utilization'], core_size_um=side, planning_only_not_timing_or_IR_proof=True)
    write_json(work / 'evidence/floorplan_plan.json', record)
    return record


@contextmanager
def display_environment(work, headless):
    env = os.environ.copy()
    proc = None
    out = None
    try:
        if not headless and not env.get('DISPLAY'):
            xvfb = shutil.which('Xvfb')
            if not xvfb:
                raise ValueError('No DISPLAY or Xvfb; install/use Xvfb or pass --headless (no screenshots)')
            import time
            for number in range(100, 200):
                if Path('/tmp/.X%d-lock' % number).exists() or Path('/tmp/.X11-unix/X%d' % number).exists():
                    continue
                out = (work / 'evidence/xvfb.log').open('a')
                proc = subprocess.Popen([xvfb, ':%d' % number, '-screen', '0', '1800x1200x24', '-nolisten', 'tcp'], stdout=out, stderr=subprocess.STDOUT)
                for _ in range(30):
                    if proc.poll() is not None:
                        break
                    if Path('/tmp/.X11-unix/X%d' % number).exists():
                        env['DISPLAY'] = ':%d' % number
                        break
                    time.sleep(0.1)
                if env.get('DISPLAY'):
                    break
                if proc.poll() is None:
                    proc.terminate()
                    proc.wait(timeout=5)
                out.close()
                out = None
                proc = None
            if not env.get('DISPLAY'):
                raise RuntimeError('Could not allocate a private Xvfb display')
        if headless:
            env.pop('DISPLAY', None)
        yield env
    finally:
        if proc is not None and proc.poll() is None:
            proc.terminate()
            proc.wait(timeout=10)
        if out is not None:
            out.close()


def pnr(work, until, headless=False):
    verify_inputs(work)
    verify_libraries(work)
    if (work / 'evidence/unexpected_tool_errors.json').exists():
        raise ValueError('Previous request reported unexpected tool errors; inspect evidence and prepare a corrected NEW run')
    if not (work / 'evidence/synthesis_status.json').exists():
        raise ValueError('Complete fresh Genus synthesis first')
    plan = sizing(work)
    last_file = work / 'evidence/last_step.txt'
    last = int(last_file.read_text()) if last_file.exists() else 0
    if until <= last:
        raise ValueError('Requested step already completed; use a later --until or a new project')
    driver = work / 'pnr/generated/driver.tcl'
    source = 'set eda_work ' + tcl(work) + '\nset eda_python ' + tcl(sys.executable) + '\n'
    source += 'set eda_last %d\nset eda_until %d\nset eda_core_size %s\nset eda_headless %d\n' % (last, until, plan['core_size_um'], headless)
    source += 'source ' + tcl(work / 'flow/tcl/driver.tcl') + '\n'
    driver.write_text(source, encoding='utf-8')
    log = work / 'evidence' / ('innovus_%02d_to_%02d.log' % (last + 1, until))
    with display_environment(work, headless) as env:
        command = ['innovus', '-batch', '-files', driver, '-log', 'eda_%02d_to_%02d' % (last + 1, until)]
        if headless:
            command.insert(1, '-no_gui')
        text = logged(command, work / 'pnr/logs', log, env)
    reached = int(last_file.read_text()) if last_file.exists() else 0
    if reached != until or 'EDA_REQUEST_COMPLETE' not in text:
        raise RuntimeError('Implementation stopped before requested step; inspect ' + str(log))
    unexpected, classified = classify_tool_errors(work, text)
    if classified:
        write_json(work / 'evidence/classified_placement_messages.json', classified)
    if unexpected:
        write_json(work / 'evidence/unexpected_tool_errors.json', unexpected)
        raise RuntimeError('Tool reported errors despite Tcl return status; inspect unexpected_tool_errors.json')
    verify_libraries(work)


def classify_tool_errors(work, text):
    step = None
    unexpected, classified = [], []
    for line in text.splitlines():
        marker = re.search(r'\bEDA_BEGIN_STEP\s+(\d\d)\b', line)
        if marker:
            step = int(marker.group(1))
        if not re.search(r'^\s*\*+ERROR:', line):
            continue
        proof = work / 'evidence/step_24.json'
        permitted = False
        if step == 24 and '(IMPSP-9099)' in line and proof.is_file():
            record = json.loads(proof.read_text())
            placement_check = record.get('automatic_checks', {}).get('placement', {})
            permitted = placement_check.get('unplaced') == 0 and placement_check.get('no_other_listed_placement_violations') is True
        (classified if permitted else unexpected).append(line)
    return unexpected, classified


def report(work):
    preparation = json.loads((work / 'evidence/preparation.json').read_text())
    lines = ['# 本轮EDA运行记录', '', '工程：`' + str(work) + '`', '', '配置与源身份：见input_manifest.json、source.json和preparation.json。', '', '本流程不运行功能仿真；EDA结果与独立工艺签核的范围分别说明。', '']
    current_identity = sha(work / 'evidence/input_manifest.json')
    if (work / 'evidence/unexpected_tool_errors.json').exists():
        lines.extend(['**存在未解决的工具错误，不能按阶段进度宣布整轮通过。** 见unexpected_tool_errors.json。', ''])
    lines.extend(['## Genus输入、展开、综合与交接', '', '输入清单有%d份RTL；主存选择与源身份见preparation.json。' % preparation['rtl_files'], ''])
    for title, filename in [('G1 展开检查', 'elaboration_status.json'), ('G2 综合执行', 'synthesis_status.json'), ('G3 综合面积与映射结果', 'synthesis.json'), ('G4 新面积与后端规划', 'floorplan_plan.json')]:
        p = work / 'evidence' / filename
        if p.exists():
            lines.extend(['**' + title + '：**', '', '```json', p.read_text(encoding='utf-8').rstrip(), '```', ''])
        else:
            if filename == 'elaboration_status.json' and (work / 'evidence/synthesis_status.json').exists():
                lines.extend(['**G1：完整综合已包含展开，未另跑独立展开检查。**', ''])
            else:
                lines.extend(['**' + title + '：未单独完成或没有对应记录。**', ''])
    stages = {int(p.stem.split('_')[-1]): json.loads(p.read_text()) for p in (work / 'evidence').glob('step_*.json')}
    descriptions = json.loads((work / 'flow/config/steps.json').read_text(encoding='utf-8'))
    for n in range(1, 35):
        d = descriptions[str(n)]
        lines.extend(['## %02d %s' % (n, d['title']), '', '**做什么：** ' + d['what'], '', '**为什么：** ' + d['why'], '', '**预期效果：** ' + d['effect'], ''])
        if d.get('parameters'):
            lines.extend(['**关键参数：** ' + d['parameters'], ''])
        commands = sorted((work / 'evidence/commands' / ('%02d' % n)).glob('*.tcl'))
        if commands:
            lines.extend(['**本轮实际执行片段：** 下列是运行时保存的Tcl正文；宏路径已解析，其他变量结合配置与日志阅读。', ''])
            for command in commands:
                lines.extend(['`' + command.name + '`', '', '```tcl', command.read_text(encoding='utf-8').rstrip(), '```', ''])
        if n in stages:
            if stages[n]['input_manifest_sha256'] != current_identity:
                raise ValueError('Stage evidence belongs to another project input: %d' % n)
            message = '**本轮结果：** 步骤命令与对应自动检查已通过；详见`step_%02d.json`，独立验收范围以该JSON为准。' % n
            lines.extend([message, '', '```json', json.dumps(stages[n], ensure_ascii=False, indent=2), '```', ''])
        else:
            lines.extend(['**本轮结果：未完成。**', ''])
    output = work / 'evidence/运行报告.md'
    output.write_text('\n'.join(lines), encoding='utf-8')
    print(output)


def package(work):
    verify_libraries(work)
    progress = work / 'evidence/last_step.txt'
    if not progress.exists() or int(progress.read_text()) != 34 or (work / 'evidence/unexpected_tool_errors.json').exists():
        raise ValueError('Delivery requires all 34 steps completed without unexpected tool errors')
    audit_step(work, 34)
    destinations = ['config', 'src/filelist_syn.f', 'src/chip_design/rtl', 'flow', 'syn/my_soc_top/reports', 'syn/my_soc_top/my_soc_top_postsyn.v', 'pnr/generated', 'pnr/my_soc_top/reports', 'pnr/my_soc_top/outputs/manual_final', 'evidence']
    selected = {}
    skipped_large = {}
    for name in destinations:
        path = work / name
        for p in ([path] if path.is_file() else path.rglob('*')):
            if p.is_file() and not p.is_symlink() and p.name != 'flow.lock' and '__pycache__' not in p.parts:
                if p.stat().st_size > 50 * 1024 * 1024:
                    skipped_large[p.relative_to(work).as_posix()] = p.stat().st_size
                else:
                    selected[p.relative_to(work).as_posix()] = p
    for p in (work / 'syn/my_soc_top').glob('*'):
        if p.is_file() and p.suffix in ['.v', '.sdc', '.sdf']:
            if p.stat().st_size <= 50 * 1024 * 1024:
                selected[p.relative_to(work).as_posix()] = p
            else:
                skipped_large[p.relative_to(work).as_posix()] = p.stat().st_size
    for p in (work / 'syn/my_soc_top/backup').glob('*.sdc'):
        selected[p.relative_to(work).as_posix()] = p
    for p in (work / 'pnr/my_soc_top').glob('*.rpt'):
        selected[p.relative_to(work).as_posix()] = p
    for name, p in list(selected.items()):
        if p.stat().st_size > 50 * 1024 * 1024:
            skipped_large[name] = p.stat().st_size
            del selected[name]
    manifest = {'files': {name: {'bytes': p.stat().st_size, 'sha256': sha(p)} for name, p in selected.items()}, 'skipped_over_50_MiB_bytes': skipped_large, 'kept_remote': ['src/macro (licensed)', 'PDK', 'pnr/my_soc_top/backup'], 'scope': 'Lab4 teaching implementation; independent foundry signoff not performed'}
    write_json(work / 'delivery_manifest.json', manifest)
    archive = generated_path(work, 'core_delivery.tar.gz')
    partial = generated_path(work, 'core_delivery.tar.gz.part')
    try:
        with tarfile.open(str(partial), 'w:gz') as tar:
            for name, p in sorted(selected.items()):
                tar.add(str(p), arcname=name, recursive=False)
            tar.add(str(work / 'delivery_manifest.json'), arcname='delivery_manifest.json')
        os.replace(str(partial), str(archive))
    finally:
        remove_generated(work, ('core_delivery.tar.gz.part',))
    print(archive)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    for name in ['prepare', 'doctor', 'elaborate', 'synth', 'size', 'pnr', 'all', 'status', 'report', 'package', 'clean', 'unlock', 'geometry', 'begin-step', 'audit-step']:
        p = sub.add_parser(name)
        p.add_argument('--work', required=True)
        if name == 'clean':
            p.add_argument('--dry-run', action='store_true')
        if name in ['prepare', 'all']:
            p.add_argument('--config')
        if name in ['pnr', 'all']:
            p.add_argument('--until', type=int, choices=range(1, 35), default=34)
            p.add_argument('--headless', action='store_true')
        if name in ['audit-step', 'begin-step']:
            p.add_argument('--step', type=int, required=True)
        if name == 'geometry':
            p.add_argument('--die', type=float, nargs=4, required=True)
    args = parser.parse_args()
    work = Path(args.work).expanduser().resolve()
    # Packaging cleanup also works on older frozen projects. It does not
    # change their inputs or use their old command parser.
    if args.command == 'clean':
        clean_work(Path(args.work), project_lock, args.dry_run)
        return 0
    if args.command == 'prepare':
        prepare(args)
        return 0
    if args.command == 'geometry':
        generate_steps(work, args.die)
        return 0
    if args.command == 'audit-step':
        audit_step(work, args.step)
        report(work)
        return 0
    if args.command == 'begin-step':
        clear_step_outputs(work, args.step)
        return 0
    freshly_prepared = args.command == 'all' and not work.exists()
    if freshly_prepared:
        prepare(args)
    elif args.command == 'all' and args.config:
        raise ValueError('--config is for a NEW project only. Resume without it, or choose a new work directory.')
    if not work.is_dir():
        raise ValueError('Missing work directory; prepare it first')
    # Always execute the immutable control-program snapshot captured during
    # prepare. Updating the deployment directory must not change an old run.
    snapshot = work / 'flow/bin/flow.py'
    if snapshot.is_file() and snapshot.resolve() != Path(__file__).resolve():
        forwarded = sys.argv[1:]
        if freshly_prepared:
            # prepare consumed the external configuration and froze it in work.
            # The snapshot must resume that prepared project without --config.
            forwarded = ['all', '--work', str(work), '--until', str(args.until)]
            if args.headless:
                forwarded.append('--headless')
        os.execv(sys.executable, [sys.executable, str(snapshot)] + forwarded)
    if args.command == 'unlock':
        p = work / 'evidence/flow.lock'
        value = json.loads(p.read_text())
        if value['host'] != socket.gethostname():
            raise ValueError('Lock belongs to another host')
        try:
            os.kill(value['pid'], 0)
        except ProcessLookupError:
            if value.get('tool_pid'):
                try:
                    os.kill(value['tool_pid'], 0)
                except ProcessLookupError:
                    pass
                else:
                    raise ValueError('Child EDA process still exists; inspect tool_process.json before unlocking')
            p.unlink()
        else:
            raise ValueError('Owning process still exists; do not clear the lock')
        return 0
    if args.command == 'status':
        verify_inputs(work)
        for name in ['preparation.json', 'synthesis_status.json', 'floorplan_plan.json']:
            p = work / 'evidence' / name
            if p.exists():
                print(name + ': ' + p.read_text())
        p = work / 'evidence/last_step.txt'
        print('Last completed step: ' + (p.read_text().strip() if p.exists() else '0'))
        return 0
    with project_lock(work):
        verify_inputs(work)
        if args.command == 'doctor':
            doctor(work)
        elif args.command == 'elaborate':
            try:
                synth(work, True)
            finally:
                report(work)
        elif args.command == 'synth':
            try:
                synth(work)
            finally:
                report(work)
        elif args.command == 'size':
            print(json.dumps(sizing(work), indent=2))
        elif args.command == 'pnr':
            try:
                pnr(work, args.until, args.headless)
            finally:
                report(work)
        elif args.command == 'all':
            try:
                doctor(work)
                if not (work / 'evidence/synthesis_status.json').exists():
                    synth(work)
                last = work / 'evidence/last_step.txt'
                if not last.exists() or int(last.read_text()) < args.until:
                    pnr(work, args.until, args.headless)
            finally:
                report(work)
        elif args.command == 'report':
            report(work)
        elif args.command == 'package':
            package(work)
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as error:
        print('EDA STOP: ' + str(error), file=sys.stderr)
        sys.exit(1)
