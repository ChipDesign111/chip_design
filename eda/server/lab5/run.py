#!/usr/bin/env python3
"""Lab5 input/CDL validation, with explicit blockers for unavailable final checks.

Original physical work is read-only. Never mark unimplemented geometry/final
checks passed. A review bundle is generated even on blocked/failed validation.
"""
import argparse
from datetime import datetime, timezone
import fcntl
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile


def sha(p):
    h = hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda: f.read(1048576), b''):
            h.update(b)
    return h.hexdigest()


def save(p, data):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def bundle(root, report):
    evidence = root/'lab5/evidence'
    save(root/'results/lab5.json', report)
    save(evidence/'result.json', report)
    text = '# Lab5 本次运行\n\n状态：%s；最终检查通过：%s\n\n' % (report['status'], report['lab5_pass'])
    text += '\n'.join('- %s：%s' % (s, r['status']) for s, r in report['stages'].items())
    text += '\n\n' + '\n'.join('- ' + x for x in report['blockers'])
    text += '\n\nCDL转换与输入核验不代表DRC/LVS通过。大型/授权资料留在服务器。\n'
    if report.get('documented_exceptions'):
        erc=report['documented_exceptions']['erc']
        text+='\n课程例外单列，原始ERC %d层次/%d展开；ERC Clean=%s，逐对象识别=%s。不代表代工厂完整签核。\n'%(erc['native_erc_hierarchical'],erc['native_erc_expanded'],erc['erc_clean'],erc['accepted_course_residuals'])
    (root/'README_lab5.md').write_text(text, encoding='utf-8')
    import html
    (root/'README_lab5.html').write_text('<meta charset="utf-8"><pre>'+html.escape(text)+'</pre>', encoding='utf-8')
    (root/'README.md').write_text(text, encoding='utf-8')
    (root/'README.html').write_text('<meta charset="utf-8"><pre>'+html.escape(text)+'</pre>', encoding='utf-8')
    files = [p for p in evidence.rglob('*') if p.is_file()]
    files += [root/'README_lab5.md', root/'README_lab5.html']
    archive = root/'results/lab5_review.tar.gz'
    with tarfile.open(str(archive), 'w:gz') as t:
        for p in sorted(files):
            t.add(str(p), arcname=p.relative_to(root).as_posix(), recursive=False)
    save(root/'results/lab5_review_manifest.json', {
        'archive_sha256': sha(archive),
        'files': {p.relative_to(root).as_posix(): {'sha256': sha(p), 'bytes': p.stat().st_size} for p in files}})


def execute(root, physical):
    deploy = root/'deploy'
    config = json.loads((deploy/'server/config/lab5.json').read_text())
    report = {'schema': 1, 'status': 'running', 'lab5_pass': False,
              'started_utc': datetime.now(timezone.utc).isoformat(),
              'physical_upload': str(physical), 'script_source': json.loads((deploy/'source.json').read_text())['git_commit'],
              'stages': {s: {'status': 'not_run'} for s in config['stages']}, 'blockers': []}
    work = root/'lab5'
    try:
        if work.exists():
            raise ValueError('Lab5 work already exists: create a new upload; no blind reruns')
        (work/'evidence').mkdir(parents=True)
        (work/'inputs').mkdir()
        save(work/'config.json', config)
        soc = root/'soc-stu'
        soc.mkdir()
        layout = soc/'layout'
        shutil.copytree(config['layout_source'], str(layout))
        save(work/'evidence/layout_source_manifest.json', {
            'source': config['layout_source'], 'private_copy': str(layout),
            'files': {p.relative_to(layout).as_posix(): sha(p) for p in layout.rglob('*') if p.is_file()}})
        original = physical/'work'
        for n in ['environment_exit_code.txt', 'eda_exit_code.txt', 'collect_exit_code.txt', 'run_exit_code.txt']:
            p = physical/'logs'/n
            if not p.is_file() or p.read_text().strip() != '0':
                raise ValueError('Physical stage not complete: '+str(p))
        if (original/'evidence/last_step.txt').read_text().strip() != '34':
            raise ValueError('Physical step34 incomplete')
        home_bytes = int(subprocess.check_output(['du', '-sx', '-B1', str(Path.home())]).split()[0])
        if home_bytes + config['peak_additional_budget_bytes'] > config['home_limit_bytes']:
            raise ValueError('Projected home storage exceeds 20GB')
        save(work/'evidence/storage.json', {'home_allocated_bytes': home_bytes,
             'additional_budget_bytes': config['peak_additional_budget_bytes'], 'limit_bytes': config['home_limit_bytes']})
        source = json.loads((deploy/'source.json').read_text())
        for name, spec in source['files'].items():
            if sha(deploy/name) != spec['sha256']:
                raise ValueError('Deployment SHA mismatch: '+name)
        for stage, names in source['workflow']['required_payload'].items():
            if any(not (deploy/name).is_file() for name in names):
                raise ValueError('Incomplete deployment: '+stage)
        old_source = json.loads((physical/'deploy/source.json').read_text())
        rtl_difference = [n for n, s in old_source['files'].items() if n.startswith('rtl/') and source['files'].get(n) != s]
        rtl_difference += [n for n in source['files'] if n.startswith('rtl/') and n not in old_source['files']]
        if rtl_difference:
            raise ValueError('Current RTL differs from bound physical input: '+str(rtl_difference))
        final = original/'pnr/my_soc_top/outputs/manual_final'
        names = ['my_soc_top.gds.gz', 'my_soc_top_flat_lvs.v', 'my_soc_top.def']
        inputs = {}
        for name in names:
            p = final/name
            if not p.is_file() or p.stat().st_size == 0:
                raise ValueError('Missing physical output: '+name)
            d = work/'inputs'/name
            shutil.copyfile(str(p), str(d))
            inputs[name] = {'source': str(p), 'sha256': sha(p), 'copy_sha256': sha(d), 'bytes': p.stat().st_size}
            if inputs[name]['sha256'] != inputs[name]['copy_sha256']:
                raise ValueError('Physical input changed during copy')
        save(work/'evidence/input_manifest.json', {'physical_commit': old_source['git_commit'], 'inputs': inputs,
             'current_rtl_matches_physical': True, 'workflow': source['workflow'], 'config_sha256': sha(work/'config.json')})
        sys.path.insert(0, str(deploy/'server/tools'))
        from gds_audit import audit
        gds = audit(work/'inputs/my_soc_top.gds.gz', set())
        save(work/'evidence/original_gds_audit.json', gds)
        if gds['undefined_references'] or config['top'] not in gds['structures']:
            raise ValueError('Incomplete original GDS hierarchy')
        report['stages']['input_audit'] = {'status': 'passed', 'gds_structures': gds['structure_count']}
        pdk = Path(config['pdk_root'])
        std, io = [pdk/config[k] for k in ['std_spi', 'io_spi']]
        macro = original/'src/macro/RA1SHD_2048x32M8/RA1SHD_2048x32M8.cdl'
        for p in [std, io, macro]:
            if not p.is_file():
                raise ValueError('Missing CDL reference: '+str(p))
        ports = work/'inputs/RA1SHD_2048x32M8_lvs_ports.v'
        ports.write_text('module RA1SHD_2048x32M8(Q,CLK,CEN,WEN,A,D,OEN,VDD,VSS);\noutput [31:0] Q; input CLK,CEN,OEN; input [3:0] WEN; input [10:0] A; input [31:0] D; inout VDD,VSS; endmodule\n')
        cdl = work/'my_soc_top.cdl'
        command = ['v2lvs', '-v', str(work/'inputs/my_soc_top_flat_lvs.v'), '-lsr', str(std), '-lsr', str(io),
                   '-l', str(ports), '-s', str(std), '-s', str(io), '-s', str(macro), '-s0', 'VSS', '-s1', 'VDD', '-o', str(cdl)]
        save(work/'evidence/cdl_command.json', {'argv': command, 'references': {str(p): sha(p) for p in [std, io, macro]}})
        log = work/'evidence/v2lvs.log'
        with log.open('w') as f:
            result = subprocess.run(command, stdout=f, stderr=subprocess.STDOUT, cwd=str(work), timeout=1800)
        text = log.read_text(errors='replace')
        if result.returncode or not cdl.is_file() or not cdl.stat().st_size or re.search(r'(?im)^\s*(?:ERROR\b|FATAL\b)', text):
            report['stages']['cdl'] = {'status': 'failed', 'exit_code': result.returncode}
            raise ValueError('V2LVS failed: inspect original v2lvs.log')
        cdltxt = cdl.read_text(errors='replace')
        includes = re.findall(r'(?im)^\s*\.include\s+[\"\x27]?([^\s\"\x27]+)', cdltxt)
        if len(includes) != 3 or any(not Path(p).is_file() for p in includes):
            raise ValueError('CDL reference INCLUDE missing or incomplete')
        top = re.search(r'(?im)^\.subckt\s+my_soc_top\b([^\n]*(?:\n\+[^\n]*)*)', cdltxt)
        if not top or any(n not in top.group(1).split() for n in ['VDD', 'VSS', 'VDDPST', 'VSSPST']):
            raise ValueError('CDL top or four distinct supply interfaces missing')
        save(work/'evidence/cdl.json', {'exit_code': result.returncode, 'cdl_sha256': sha(cdl),
             'includes': includes, 'top_declaration': top.group(0), 'lvs_pass_claimed': False})
        report['stages']['cdl'] = {'status': 'converted', 'note': 'Circuit equivalence awaits LVS; conversion is not LVS.'}
        resources = {}
        for key in ['dummy_metal', 'dummy_od_po']:
            value = config[key]
            resources[key] = {'path': value, 'exists': bool(value and Path(value).is_file())}
            if not resources[key]['exists']:
                report['blockers'].append('Missing matched original '+key+' rule; server path required')
        process = pdk/config['process_pdk']
        for key, name in [('drc', 'Calibre/drc/calibre.drc'), ('lvs', 'Calibre/lvs/calibre.lvs'), ('antenna', 'Calibre/drc/ant.drc')]:
            p = process/name
            resources[key] = {'path': str(p), 'exists': p.is_file(), 'sha256': sha(p) if p.is_file() else None}
        save(work/'evidence/resource_inventory.json', resources)
        if report['blockers']:
            report['status'] = 'blocked'
            return 2
        from backend import execute as execute_backend
        return execute_backend(root, physical, config, report, save, sha)
    except Exception as e:
        report['status'] = 'failed'
        report['blockers'].append(str(e))
        return 1
    finally:
        # Check original inputs again; never modify original physical work.
        if 'inputs' in locals():
            changed = [n for n, s in inputs.items() if sha(Path(s['source'])) != s['sha256']]
            report['original_inputs_unchanged'] = not changed
            if changed:
                report['status'] = 'failed'
                report['blockers'].append('Original physical inputs changed: '+str(changed))
        report['finished_utc'] = datetime.now(timezone.utc).isoformat()
        bundle(root, report)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, required=True)
    p.add_argument('--physical', type=Path, required=True)
    args = p.parse_args()
    args.root = args.root.resolve()
    if args.root.parent.name != 'uploads' or args.physical.resolve().parent != args.root.parent:
        raise ValueError('Use isolated uploads in the same server project')
    if (args.root/'lab5').exists():
        raise ValueError('Existing Lab5 work is frozen; use a new upload')
    with (args.root/'logs/lab5.lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        rc = execute(args.root, args.physical.resolve())
    (args.root/'logs/lab5_exit_code.txt').write_text(str(rc)+'\n')
    sys.exit(rc)
