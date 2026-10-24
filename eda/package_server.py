#!/usr/bin/env python3
"""Build the deployment-only archive; never include PDK, models or run results."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[1]
EDA = ROOT / 'eda'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=EDA / 'dist/chip_design_eda.tar.gz')
    args = parser.parse_args()
    branch = subprocess.check_output(
        ['git', 'branch', '--show-current'], cwd=str(ROOT), text=True
    ).strip() or None
    selected = {}
    for folder in ['eda/server', 'rtl', 'eda/docs']:
        for p in (ROOT / folder).rglob('*'):
            if not p.is_file() or p.is_symlink() or '__pycache__' in p.parts or p.suffix == '.pyc':
                continue
            if any(s.lower() in ['.lib', '.lef', '.vclef', '.gds', '.gds2', '.cdl', '.spi', '.db'] for s in p.suffixes) or p.stat().st_size > 10 * 1024 * 1024:
                raise ValueError('Unexpected library/large content in public deployment input: ' + str(p))
            name = p.relative_to(ROOT / 'eda').as_posix() if folder.startswith('eda/') else p.relative_to(ROOT).as_posix()
            selected[name] = p
    manifest = {'repository': 'https://github.com/ChipDesign111/chip_design', 'branch': branch, 'git_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=str(ROOT), text=True).strip(), 'files': {n: {'bytes': p.stat().st_size, 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()} for n, p in sorted(selected.items())}, 'excluded': ['PDK', 'licensed SRAM models', 'datasets', 'EDA databases', 'development tests and temporary utilities', 'other branch working tree'], 'scope': 'Deployment source package; does not claim functional verification or EDA completion'}
    manifest['working_tree_dirty'] = bool(subprocess.check_output(['git', 'status', '--porcelain'], cwd=str(ROOT), text=True).strip())
    target = args.output.expanduser().resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    source_json = json.dumps(manifest, ensure_ascii=False, indent=2).encode('utf-8') + b'\n'
    import io
    with tarfile.open(str(target), 'w:gz') as tar:
        for name, p in sorted(selected.items()):
            tar.add(str(p), arcname=name, recursive=False)
        info = tarfile.TarInfo('source.json')
        info.size = len(source_json)
        tar.addfile(info, io.BytesIO(source_json))
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    with target.with_name(target.name + '.sha256').open('w', encoding='utf-8', newline='\n') as f:
        f.write(digest + '  ' + target.name + '\n')
    print(json.dumps({'archive': str(target), 'bytes': target.stat().st_size, 'sha256': digest, 'files': len(selected) + 1, 'licensed_models_included': False}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
