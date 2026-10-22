#!/usr/bin/env python3
"""Verify every RTL/include input against a fixed source archive, Python 3.8+."""
import argparse
from datetime import datetime,timezone
import hashlib,json
from pathlib import Path
import tarfile

ROOT=Path(__file__).resolve().parents[1]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--archive',type=Path,required=True)
    ap.add_argument('--revision',required=True)
    ap.add_argument('--out',type=Path,required=True)
    args=ap.parse_args()
    values={}
    with tarfile.open(str(args.archive),'r:*') as archive:
        for item in archive.getmembers():
            if item.isfile() and item.name.startswith('rtl/'):
                expected=sha(archive.extractfile(item).read())
                path=ROOT/item.name
                if not path.is_file() or sha(path.read_bytes())!=expected:
                    raise RuntimeError('Source/archive mismatch: '+item.name)
                values[item.name]=expected
    present={p.relative_to(ROOT).as_posix() for p in (ROOT/'rtl').rglob('*') if p.is_file()}
    if not values or present!=set(values):
        raise RuntimeError('RTL tree differs from archive member set')
    result={'captured_utc':datetime.now(timezone.utc).isoformat(),'source_revision':args.revision,
            'archive_sha256':sha(args.archive.read_bytes()),'source_sha256':values,'status':'PASS'}
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(result,indent=2))
    print('PASS complete RTL source archive identity: '+str(len(values))+' files')


if __name__=='__main__':
    main()
