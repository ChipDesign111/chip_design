"""Compile a PyTorch factory for the current RAW ABI and optional SoC simulation."""
import argparse
import importlib.util
import json
from pathlib import Path

import numpy as np
import torch

from .compiler import compile_model


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', type=Path, required=True)
    parser.add_argument('--factory', default='build_model')
    parser.add_argument('--weights', type=Path)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--calibration', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--force-cpu', action='store_true')
    parser.add_argument('--no-batch-reuse', action='store_true', help='Use the original per-sample RAW schedule')
    parser.add_argument('--simulate', action='store_true')
    parser.add_argument('--vsim', default='vsim')
    args = parser.parse_args()
    spec = importlib.util.spec_from_file_location('user_network', args.model)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    model = getattr(module, args.factory)().cpu().eval()
    if args.weights:
        model.load_state_dict(torch.load(args.weights, map_location='cpu', weights_only=True))
    x = torch.from_numpy(np.load(args.input).astype(np.float32))
    calibration = [torch.from_numpy(v.astype(np.float32)) for v in np.load(args.calibration)] if args.calibration else None
    package = compile_model(model, x, calibration, force_cpu=args.force_cpu, reuse_batch_weights=not args.no_batch_reuse)
    package.write(args.out, x.numpy())
    result = dict(output=str(args.out), target=package.metadata['target'],
                  code_bytes=package.metadata['code_bytes'], free_bytes=package.metadata['free_bytes'],
                  schedule=[(n['name'], n['backend']) for n in package.nodes])
    if args.simulate:
        from .sim import simulate
        result['simulation'] = simulate(args.out, args.vsim)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
