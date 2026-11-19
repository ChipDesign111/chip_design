"""Fetch the official pose landmark frontend; not the FPGA action model."""
import argparse
import hashlib
import json
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
URL = 'https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task'
SHA256 = '59929e1d1ee95287735ddd833b19cf4ac46d29bc7afddbbf6753c459690d574a'

def download(out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    path = out / 'pose_landmarker_lite.task'
    if not path.exists():
        with urllib.request.urlopen(URL, timeout=120) as response:
            data = response.read()
        if hashlib.sha256(data).hexdigest() != SHA256:
            raise ValueError('Official pose model checksum differs')
        path.write_bytes(data)
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual != SHA256:
        raise ValueError('Existing pose model checksum differs; refusing to overwrite it')
    (out/'pose_model_source.json').write_text(json.dumps({
        'url': URL, 'sha256': actual, 'bytes': path.stat().st_size,
        'role': 'PC-only pose landmarks; action classifier must be trained separately',
    }, indent=2)+'\n', encoding='utf-8')
    print(path)
    return path

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=ROOT/'tools/local/camera_demo')
    download(parser.parse_args().out)
