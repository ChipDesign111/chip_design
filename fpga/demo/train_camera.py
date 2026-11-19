"""Train a camera-specific 64→32→6 network, then compile resident FPGA code.

Only features and labels recorded locally are used. No UCI sensor weights are
relabelled as camera weights. Session-separated validation/test are mandatory.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import random

import numpy as np

from .features import DEFAULT_LABELS, load_dataset


def split_sessions(labels, sessions, classes, seed=42):
    """Separate entire sessions to prevent overlapping-frame train/test leakage."""
    rng = random.Random(seed)
    result = {'train': [], 'validation': [], 'test': []}
    assignment = {}
    for session in set(sessions):
        if len(set(labels[sessions == session])) != 1:
            raise ValueError('A session contains multiple labels: ' + str(session))
    for name in classes:
        choices = sorted(set(sessions[labels == name]))
        if len(choices) < 3:
            raise ValueError(f'{name}: record at least three independent sessions (train, validation, test)')
        rng.shuffle(choices)
        holdout = max(1, len(choices)//5)
        for i, session in enumerate(choices):
            split = 'test' if i < holdout else 'validation' if i < 2*holdout else 'train'
            assignment[str(session)] = split
            result[split].extend(np.flatnonzero((labels == name) & (sessions == session)).tolist())
    return {name: np.array(sorted(indices), dtype=np.int64) for name, indices in result.items()}, assignment


def train(dataset, out, classes=DEFAULT_LABELS, epochs=300, patience=35,
          learning_rate=0.003, seed=42, min_samples=12):
    # Recording/replay do not require a PyTorch installation.
    import torch
    from torch import nn
    from compiler import compiler
    from fpga.demo.firmware import write_resident

    if len(classes) != 6 or len(set(classes)) != 6:
        raise ValueError('The camera demo requires six distinct class labels')
    if epochs < 1 or patience < 1 or min_samples < 1 or learning_rate <= 0:
        raise ValueError('Invalid training options')
    data, metadata = load_dataset(dataset)
    unknown = set(data['labels']) - set(classes)
    if unknown:
        raise ValueError('Dataset labels not present in --labels: ' + ', '.join(sorted(unknown)))
    for label in classes:
        if np.count_nonzero(data['labels'] == label) < min_samples:
            raise ValueError(f'{label}: need at least {min_samples} samples')
    indices, assignment = split_sessions(data['labels'], data['sessions'], classes, seed)
    np.random.seed(seed); random.seed(seed); torch.manual_seed(seed)
    torch.set_num_threads(1)
    model = nn.Sequential(nn.Linear(64, 32), nn.ReLU(), nn.Linear(32, 6))
    x = torch.from_numpy(data['features'].astype(np.float32))
    y = torch.tensor([classes.index(str(label)) for label in data['labels']], dtype=torch.long)
    tx, ty = x[indices['train']], y[indices['train']]
    vx, vy = x[indices['validation']], y[indices['validation']]
    weights = len(ty) / (6*torch.bincount(ty, minlength=6).float())
    loss_fn = nn.CrossEntropyLoss(weight=weights)
    optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)
    best_loss, best_state, best_epoch, history = float('inf'), None, 0, []
    for epoch in range(1, epochs+1):
        model.train(); optimizer.zero_grad(); loss = loss_fn(model(tx), ty)
        loss.backward(); optimizer.step(); model.eval()
        with torch.no_grad():
            val_loss = float(loss_fn(model(vx), vy))
        history.append({'epoch': epoch, 'train_loss': float(loss.detach()), 'validation_loss': val_loss})
        if val_loss < best_loss-1e-6:
            best_loss, best_state, best_epoch = val_loss, copy.deepcopy(model.state_dict()), epoch
        if epoch-best_epoch >= patience:
            break
    model.load_state_dict(best_state); model.eval()
    out = Path(out)
    if out.exists() and any(out.iterdir()):
        raise ValueError('Output directory must be empty to avoid mixing model versions')
    out.mkdir(parents=True, exist_ok=True)
    torch.save(model.state_dict(), out/'weights.pth')
    (out/'model.py').write_text("from torch import nn\n\ndef build_model():\n    return nn.Sequential(nn.Linear(64,32), nn.ReLU(), nn.Linear(32,6))\n", encoding='utf-8')
    # Only training sessions determine quantization calibration; no test leakage.
    selected = indices['train'][np.linspace(0, len(indices['train'])-1, min(256, len(indices['train']))).astype(int)]
    calibration = [x[int(i):int(i)+1] for i in selected]
    example = x[int(indices['train'][0]):int(indices['train'][0])+1]
    package = compiler.compile_model(model, example, calibration_inputs=calibration)
    # This fallback target accelerates only complete 32-output x 64-input
    # blocks. FC1 uses a real RAW block; FC2's 32x6 fringe is calculated by the
    # CPU inside the FPGA. Reject a wholly CPU package rather than relabelling
    # it as an NPU demonstration.
    mapping = [{key: node[key] for key in ('name','op','backend','raw_tiles','raw_macs','cpu_macs') if key in node}
               for node in package.metadata['nodes']]
    if package.metadata.get('target') != 'int22-raw-v1' or package.metadata.get('npu_core_starts',0) < 1:
        raise ValueError('Camera demo must include at least one real RAW NPU block')
    if not any(n.get('raw_tiles',0) > 0 and n['backend'] == 'RAW+CPU' for n in mapping):
        raise ValueError('No Linear layer maps to the RAW NPU')
    package.write(out/'compiled', example.numpy())
    resident_metadata = write_resident(package, out/'resident')
    metrics = {}
    for split, selected in indices.items():
        with torch.no_grad():
            logits = model(x[selected]).numpy()
        integer = np.concatenate([package.reference(data['features'][i:i+1])[package.graph['output']] for i in selected])
        actual = y[selected].numpy()
        fpred, qpred = logits.argmax(1), integer.argmax(1)
        confusion = np.zeros((6, 6), dtype=np.int64)
        for label, predicted in zip(actual, qpred):
            confusion[int(label), int(predicted)] += 1
        metrics[split] = {'samples': len(selected), 'sessions': len(set(data['sessions'][selected])),
                          'float_accuracy': float(np.mean(fpred == actual)),
                          'integer_accuracy': float(np.mean(qpred == actual)),
                          'float_integer_argmax_agreement': float(np.mean(fpred == qpred)),
                          'integer_confusion_actual_by_predicted': confusion.tolist()}
    manifest = package.metadata
    result = {'format': 1, 'trained': True, 'feature_contract': metadata, 'labels': list(classes),
              'package_tag': resident_metadata['live_demo']['package_tag'],
              'backend_target': package.metadata['target'], 'layer_mapping': mapping,
              'npu_core_starts_per_request': package.metadata['npu_core_starts'],
              'inference_location': 'FPGA RAW NPU for complete FC1 block; FPGA CPU for reductions, activation and FC2 fringe',
              'network': [64, 32, 6], 'hidden_activation': 'relu',
              'input_scale': manifest['tensors'][manifest['input']]['scale'],
              'output_scale': manifest['tensors'][manifest['output']]['scale'],
              'dataset_sha256': hashlib.sha256(Path(dataset).read_bytes()).hexdigest(),
              'dataset_source': metadata.get('capture_source', 'unspecified; verify provenance'),
              'seed': seed, 'best_epoch': best_epoch, 'training_epochs': len(history),
              'session_split': assignment, 'metrics': metrics, 'history': history,
              'accuracy_scope': 'Recorded session holdout only; not a general human-action recognition accuracy claim',
              'hardware_verified': False}
    for path in (out/'camera_demo.json', out/'resident/camera_demo.json'):
        path.write_text(json.dumps(result, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
    np.save(out/'example_input.npy', example.numpy())
    print(json.dumps({'model': str(out), 'resident': str(out/'resident'), 'best_epoch': best_epoch,
                      'metrics': metrics, 'hardware_verified': False}, indent=2))
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--dataset', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--labels', nargs=6, default=DEFAULT_LABELS)
    p.add_argument('--epochs', type=int, default=300)
    p.add_argument('--patience', type=int, default=35)
    p.add_argument('--learning-rate', type=float, default=0.003)
    p.add_argument('--seed', type=int, default=42)
    a = p.parse_args()
    try:
        train(a.dataset, a.out, tuple(a.labels), a.epochs, a.patience, a.learning_rate, a.seed)
    except (ValueError, ImportError) as e:
        p.exit(2, f'Training failed: {e}\n')


if __name__ == '__main__':
    main()
