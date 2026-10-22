"""Remove only named packaging products; preserve all implementation data."""
import json
from pathlib import Path


ARCHIVES = (
    'core_delivery.tar.gz', 'core_delivery.tar.gz.sha256',
    'review_delivery.tar.gz', 'review_delivery.tar.gz.sha256',
)
PARTS = tuple(name + '.part' for name in ARCHIVES)
STAGING = ('review_staging/my_soc_top_hier_postpnr.v.gz',)
GENERATED = ARCHIVES + PARTS + STAGING


def generated_path(work, name):
    if name not in GENERATED:
        raise ValueError('Not a disposable packaging file: ' + name)
    root = work.resolve()
    path = root / name
    path.resolve().relative_to(root)
    for item in [path] + list(path.parents):
        if item == root:
            break
        if item.is_symlink():
            raise ValueError('Refusing packaging symlink: ' + str(item))
    if path.exists() and (not path.is_file() or path.stat().st_nlink != 1):
        raise ValueError('Expected an ordinary packaging file: ' + str(path))
    return path


def remove_generated(work, names, dry_run=False):
    # Validate the complete plan before removing anything.
    paths = [generated_path(work, name) for name in names]
    selected = [{'file': p.relative_to(work.resolve()).as_posix(),
                 'bytes': p.stat().st_size} for p in paths if p.is_file()]
    if not dry_run:
        for path in paths:
            if path.is_file():
                path.unlink()
        if any(name.startswith('review_staging/') for name in names):
            staging = work.resolve() / 'review_staging'
            if staging.is_dir() and not any(staging.iterdir()):
                staging.rmdir()
    return selected


def clean_work(work, lock_factory, dry_run=False):
    work = work.expanduser()
    if work.is_symlink():
        raise ValueError('Use the actual project directory, not a symlink')
    root = work.resolve()
    for name in ['config/design.json', 'evidence/preparation.json', 'flow/bin/flow.py']:
        path = root / name
        for item in [path] + list(path.parents):
            if item == root:
                break
            if item.is_symlink():
                raise ValueError('Project marker is a symlink: ' + str(item))
        if not path.is_file():
            raise ValueError('Not a prepared EDA project: missing ' + name)
    config = json.loads((root / 'config/design.json').read_text(encoding='utf-8'))
    preparation = json.loads((root / 'evidence/preparation.json').read_text(encoding='utf-8'))
    if (config.get('profile') != 'xzx_rtl_tsmc180_lab4'
            or config.get('top') != 'my_soc_top'
            or Path(preparation.get('work', '')).resolve() != root):
        raise ValueError('Project identity does not match the requested work directory')
    with lock_factory(root):
        files = remove_generated(root, GENERATED, dry_run)
    result = {'work': str(root), 'dry_run': dry_run, 'files': files,
              'bytes': sum(item['bytes'] for item in files),
              'scope': 'Packaging archives and known staging files only; manifests, logs, reports, checkpoints and final views preserved'}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result
