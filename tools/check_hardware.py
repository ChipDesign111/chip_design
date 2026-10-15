"""Verify byte identity of the retained fixed hardware perimeter."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]
def check():
    manifest = json.loads((ROOT / 'rtl/manifest.json').read_text(encoding='utf-8'))
    for record in manifest['files']:
        path = ROOT / record['path']
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != record['sha256']:
            raise AssertionError('Retained hardware changed: ' + record['path'])
    print(f"PASS: {len(manifest['files'])} retained hardware files match source SHA-256")

if __name__ == '__main__':
    check()
