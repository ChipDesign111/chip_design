"""Rebuild the frozen classifier for PC-only arithmetic, without hardware IO."""
import hashlib
import json
from pathlib import Path
import sys
import numpy as np
import torch
from torch import nn

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from compiler import compiler
from fpga.demo.firmware import make_resident

BASE=ROOT/'tools/local/camera_demo'
DEFAULT_MODEL=BASE/'static_candidate_frozen_20261121/model'
DEFAULT_DATASET=BASE/'final_hip_static_calibration_20261121/selected_features.npz'

def load_reference(model_dir=DEFAULT_MODEL, dataset=DEFAULT_DATASET):
    model_dir, dataset = Path(model_dir), Path(dataset)
    metadata=json.loads((model_dir/'camera_demo.json').read_text(encoding='utf-8'))
    if metadata.get('network') != [64,32,6] or not metadata.get('trained'):
        raise ValueError('Expected a trained 64-to-32-to-6 camera model')
    assert hashlib.sha256(dataset.read_bytes()).hexdigest()==metadata['dataset_sha256']
    assert hashlib.sha256((model_dir/'weights.pth').read_bytes()).hexdigest()==metadata['weights_sha256']
    with np.load(dataset,allow_pickle=False) as data:
        x=data['features'].copy();selected=np.flatnonzero(data['splits']=='train')
    calibration=selected[np.linspace(0,len(selected)-1,min(256,len(selected))).astype(int)]
    torch.set_num_threads(4)
    network=nn.Sequential(nn.Linear(64,32),nn.ReLU(),nn.Linear(32,6))
    network.load_state_dict(torch.load(model_dir/'weights.pth',map_location='cpu',weights_only=True));network.eval()
    examples=[torch.from_numpy(x[i:i+1]) for i in calibration]
    package=compiler.compile_model(network,examples[0],calibration_inputs=examples)
    image=make_resident(package)
    assert image.image==(model_dir/'resident/firmware.bin').read_bytes()
    assert image.metadata['live_demo']['package_tag']==metadata['package_tag']
    return package,metadata

