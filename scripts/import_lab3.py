"""Import the fixed Lab 3 perimeter and immutable release fixtures."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil

ROOT = Path(__file__).resolve().parents[1]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('source', type=Path)
    args = parser.parse_args()
    source = args.source.resolve()
    if not (source / 'soc/sim/filelists/my_soc_tb.f').is_file():
        raise SystemExit('Expected the Lab 3 SoC_cv32e40p directory')
    paths = []
    for folder in ('cpu_cv32e40p/include', 'cpu_cv32e40p/rtl', 'soc/rtl'):
        paths += [(path, Path('platform/course_soc') / path.relative_to(source))
                  for path in (source / folder).rglob('*')
                  if path.is_file() and path.suffix.lower() in ('.sv', '.svh', '.v', '.vh')]
    paths += [(source / 'soc/sim/filelists/my_soc_tb.f', Path('filelists/lab3_original.f'))]
    for filename in ('tb_npu_check.sv', 'tb_simple_npu.sv'):
        paths.append((source / 'simple_npu/tb' / filename, Path('verification/lab3') / filename))
    for filename in ('my_soc_tb.sv', 'lab3_test1.c', 'lab3_test2.c', 'lab3_test3.c',
                     'lab3_test1.hex', 'lab3_test2.hex', 'lab3_test3.hex', 'lab3_hand.hex'):
        paths.append((source / 'soc/sim/tb' / filename, Path('verification/lab3/soc') / filename))
    for filename in ('startup.S', 'linker.ld'):
        paths.append((source / 'soc/sim/sw' / filename, Path('sw/startup/lab3') / filename))
    records = []
    for original, relative in sorted(paths, key=lambda item: str(item[1])):
        target = ROOT / relative
        if target.exists():
            if target.read_bytes() != original.read_bytes():
                raise SystemExit(f'Refusing to overwrite different file: {relative}')
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(original, target)
        records.append({'source': original.relative_to(source).as_posix(),
                        'path': relative.as_posix(),
                        'sha256': hashlib.sha256(target.read_bytes()).hexdigest()})
    manifest = {'source': 'Provided Lab 3 SoC_cv32e40p, completed 4-port NPU integration',
                'perimeter_policy': 'Fixed; only NPU build profile is replaceable',
                'files': records}
    (ROOT / 'platform/course_soc/manifest.json').write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(f'Imported and hashed {len(records)} perimeter/fixture files')

if __name__ == '__main__':
    main()
