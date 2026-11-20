"""Reproducible training for the six-class HOF64 camera head.

Only original training rows determine scales, balanced batches and augmentation.
Validation chooses a checkpoint. Callers must retain entire recording sessions
in one split; augmented rows are never new independent sessions.
"""
import copy
import random

import cv2
import numpy as np


FLOW_TRAINING_LABELS = ('standing', 'left_arm', 'right_arm', 'both_arms', 'squat', 'lean')


def _raw_features(values):
    raw = np.asarray(values)
    if (raw.dtype.kind not in 'fiu' or raw.ndim != 2 or raw.shape[1] != 64 or
            len(raw) == 0):
        raise ValueError('Expected nonempty raw HOF features with shape[N,64]')
    raw = raw.astype(np.float32, copy=False)
    if not np.isfinite(raw).all() or np.any(raw < 0) or np.any(raw > 1):
        raise ValueError('Raw HOF features must be finite values in[0,1]')
    return raw


def _class_labels(values, count):
    labels = np.asarray(values)
    if (labels.shape != (count,) or labels.dtype.kind not in 'iu' or
            np.any(labels < 0) or np.any(labels >= 6)):
        raise ValueError('Labels must use indices0..5 in FLOW_TRAINING_LABELS order')
    return labels.astype(np.int64, copy=False)


def train_feature_scale(raw_train):
    """Return the selected scale-only normalization fitted on TRAIN rows only."""
    raw = _raw_features(raw_train)
    std = raw.std(0)
    floor = max(.001, float(np.median(std))*.1)
    return np.maximum(std, floor).astype(np.float32)


def augment_flow(raw_features, labels, rng):
    """Augment TRAIN HOF grids; left/right class indices are1 and2.

    A horizontal mirror reverses cell columns and X-direction bins, swapping
    left/right labels. Time reversal swaps both direction signs and keeps the
    action label. Small spatial/contrast changes retain the original session.
    """
    raw_features = _raw_features(raw_features)
    labels = _class_labels(labels, len(raw_features))
    result, targets = [], labels.copy()
    for index, value in enumerate(raw_features):
        grid = value.reshape(4, 4, 4).copy()
        if rng.random() < .5:
            grid = grid[:, ::-1, :][:, :, [1, 0, 2, 3]]
            if targets[index] in (1, 2):
                targets[index] = 3-targets[index]
        if rng.random() < .5:
            grid = grid[:, :, [1, 0, 3, 2]]
        matrix = cv2.getRotationMatrix2D((1.5, 1.5), 0, float(rng.uniform(.85, 1.15)))
        matrix[:, 2] += rng.uniform(-.35, .35, size=2)
        grid = cv2.warpAffine(grid, matrix, (4, 4), flags=cv2.INTER_LINEAR,
                              borderMode=cv2.BORDER_CONSTANT, borderValue=0)
        result.append(np.clip(grid*rng.uniform(.8, 1.2), 0, 1).ravel())
    return np.array(result, dtype=np.float32), targets


def _metrics(actual, predicted):
    confusion = np.zeros((6, 6), dtype=int)
    for truth, guess in zip(actual, predicted):
        confusion[int(truth), int(guess)] += 1
    count = confusion.sum(1)
    present = count > 0
    recall = np.divide(np.diag(confusion), count, out=np.full(6, np.nan), where=present)
    return {
        'accuracy': float(np.mean(actual == predicted)),
        'balanced_accuracy_present_classes': float(recall[present].mean()),
        'recall_by_class': [None if not p else float(r) for p, r in zip(present, recall)],
        'class_counts': count.tolist(), 'confusion_actual_by_predicted': confusion.tolist(),
    }


def fit_flow_head(train_raw, train_labels, validation_raw, validation_labels, *,
                  seed=42, learning_rate=.003, max_epochs=1000, patience=120):
    """Fit the selected64->32->6 head without reading or accepting test rows.

    Returns CPU ``state_dict``, ``train_feature_scale``, loss ``history``, best
    epoch and metrics. Defaults reproduce the selected balanced-batch training
    recipe; recording-session separation is the caller's responsibility.
    """
    import torch
    from torch import nn

    train_raw, validation_raw = _raw_features(train_raw), _raw_features(validation_raw)
    train_labels = _class_labels(train_labels, len(train_raw))
    validation_labels = _class_labels(validation_labels, len(validation_raw))
    counts = np.bincount(train_labels, minlength=6)
    if np.any(counts == 0):
        raise ValueError('Training requires original samples from all six classes')
    if (not isinstance(max_epochs, int) or isinstance(max_epochs, bool) or max_epochs < 1 or
            not isinstance(patience, int) or isinstance(patience, bool) or patience < 1 or
            not np.isfinite(learning_rate) or learning_rate <= 0):
        raise ValueError('Invalid flow training options')
    scale = train_feature_scale(train_raw)
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.set_num_threads(4)
    rng = np.random.default_rng(seed)
    model = nn.Sequential(nn.Linear(64, 32), nn.ReLU(), nn.Linear(32, 6))
    optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)
    train_loss_fn = nn.CrossEntropyLoss()
    weights = torch.tensor(len(train_labels)/(6*counts), dtype=torch.float32)
    selection_loss_fn = nn.CrossEntropyLoss(weight=weights)
    vx = torch.from_numpy((validation_raw/scale).astype(np.float32))
    vy = torch.from_numpy(validation_labels)
    best_loss, best_epoch, best_state, history = float('inf'), 0, None, []
    for epoch in range(1, max_epochs+1):
        model.train()
        indices = np.concatenate([
            rng.choice(np.flatnonzero(train_labels == label), 25, replace=True)
            for label in range(6)
        ])
        rng.shuffle(indices)
        batch_x, batch_y = augment_flow(train_raw[indices], train_labels[indices].copy(), rng)
        bx = torch.from_numpy((batch_x/scale).astype(np.float32))
        by = torch.from_numpy(batch_y.astype(np.int64))
        optimizer.zero_grad()
        loss = train_loss_fn(model(bx), by)
        loss.backward()
        optimizer.step()
        model.eval()
        with torch.no_grad():
            validation_loss = float(selection_loss_fn(model(vx), vy))
        history.append({'epoch': epoch, 'training_loss': float(loss.detach()),
                        'validation_loss': validation_loss})
        if validation_loss < best_loss-1e-6:
            best_loss, best_epoch, best_state = validation_loss, epoch, copy.deepcopy(model.state_dict())
        if epoch-best_epoch >= patience:
            break
    model.load_state_dict(best_state)
    model.eval()
    metrics = {}
    for split, raw, labels in [('train', train_raw, train_labels),
                                ('validation', validation_raw, validation_labels)]:
        with torch.no_grad():
            predicted = model(torch.from_numpy((raw/scale).astype(np.float32))).argmax(1).numpy()
        metrics[split] = _metrics(labels, predicted)
    return {
        'state_dict': best_state, 'train_feature_scale': scale, 'history': history,
        'best_epoch': best_epoch, 'epochs': epoch, 'weighted_validation_loss': best_loss,
        'metrics': metrics, 'labels': list(FLOW_TRAINING_LABELS),
        'training_options': {'seed': seed, 'learning_rate': learning_rate,
                             'max_epochs': max_epochs, 'patience': patience,
                             'batch_class_counts': [25]*6, 'torch_threads': 4},
    }
