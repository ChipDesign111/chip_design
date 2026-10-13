#!/usr/bin/env python3
"""Train a chip-friendly HAR MLP: 64 -> 32 -> 6 (~2.28K params), INT8 export.

Pipeline:
  UCI HAR (561-d) -> SelectKBest(f_classif, k=64) -> MLP(64,32,6) -> INT8 PTQ export
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from sklearn.feature_selection import SelectKBest, f_classif
from sklearn.metrics import classification_report, confusion_matrix
from torch.utils.data import DataLoader, TensorDataset


ACTIVITY_NAMES = [
    "WALKING",
    "WALKING_UPSTAIRS",
    "WALKING_DOWNSTAIRS",
    "SITTING",
    "STANDING",
    "LAYING",
]


class HarMLP(nn.Module):
    """Exact target topology: 64 -> 32 -> 6 with ReLU then logits for Argmax."""

    def __init__(self) -> None:
        super().__init__()
        self.fc1 = nn.Linear(64, 32)
        self.fc2 = nn.Linear(32, 6)
        self.relu = nn.ReLU(inplace=True)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.relu(self.fc1(x))
        return self.fc2(x)


def count_params(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters())


def load_uci_har(root: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    train_x = np.loadtxt(root / "train" / "X_train.txt")
    train_y = np.loadtxt(root / "train" / "y_train.txt", dtype=np.int64) - 1
    test_x = np.loadtxt(root / "test" / "X_test.txt")
    test_y = np.loadtxt(root / "test" / "y_test.txt", dtype=np.int64) - 1
    return train_x.astype(np.float32), train_y, test_x.astype(np.float32), test_y


def select_features(
    x_train: np.ndarray,
    y_train: np.ndarray,
    x_test: np.ndarray,
    k: int = 64,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    selector = SelectKBest(score_func=f_classif, k=k)
    x_train_64 = selector.fit_transform(x_train, y_train).astype(np.float32)
    x_test_64 = selector.transform(x_test).astype(np.float32)
    selected_idx = selector.get_support(indices=True).astype(np.int64)
    return x_train_64, x_test_64, selected_idx


def to_int8_symmetric(x: np.ndarray, eps: float = 1e-8) -> tuple[np.ndarray, float]:
    """Symmetric INT8 quantization scale: q = round(x / scale), scale = max(|x|) / 127."""
    abs_max = float(np.max(np.abs(x)))
    scale = abs_max / 127.0 if abs_max > eps else 1.0
    q = np.clip(np.round(x / scale), -128, 127).astype(np.int8)
    return q, scale


def quantize_linear_weights(
    weight: np.ndarray, bias: np.ndarray
) -> dict:
    """Per-tensor symmetric INT8 for weights; bias kept float32 (chip may use INT32 accum)."""
    w_q, w_scale = to_int8_symmetric(weight)
    return {
        "weight_int8": w_q,
        "weight_scale": w_scale,
        "bias_float32": bias.astype(np.float32),
    }


@torch.no_grad()
def evaluate(model: nn.Module, loader: DataLoader, device: torch.device) -> tuple[float, np.ndarray, np.ndarray]:
    model.eval()
    preds, labels = [], []
    for xb, yb in loader:
        xb = xb.to(device)
        logits = model(xb)
        pred = logits.argmax(dim=1).cpu().numpy()
        preds.append(pred)
        labels.append(yb.numpy())
    y_true = np.concatenate(labels)
    y_pred = np.concatenate(preds)
    acc = float((y_true == y_pred).mean())
    return acc, y_true, y_pred


def train(args: argparse.Namespace) -> None:
    # Honor single-GPU isolation set by caller via CUDA_VISIBLE_DEVICES.
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    if device.type == "cuda":
        print(f"Using device: {device} | physical CUDA_VISIBLE_DEVICES={os.environ.get('CUDA_VISIBLE_DEVICES')}")
        print(f"GPU name: {torch.cuda.get_device_name(0)}")
    else:
        print("Using device: CPU")

    data_root = Path(args.data_root)
    out_dir = Path(args.out_dir)
    ckpt_dir = Path(args.ckpt_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    ckpt_dir.mkdir(parents=True, exist_ok=True)

    print("Loading UCI HAR ...")
    x_train, y_train, x_test, y_test = load_uci_har(data_root)
    print(f"Raw shapes: train={x_train.shape}, test={x_test.shape}")

    print("Selecting top-64 features (ANOVA F) ...")
    x_train, x_test, feat_idx = select_features(x_train, y_train, x_test, k=64)
    print(f"Selected feature indices (first 10): {feat_idx[:10].tolist()}")

    # Optional: map features into a chip-friendly INT8 input range for training awareness.
    # Keep float training; export also provides INT8 inputs.
    x_train_q, in_scale = to_int8_symmetric(x_train)
    x_test_q, _ = to_int8_symmetric(x_test)
    # Dequantize for float training so scale matches deployment (q * scale ≈ x)
    x_train_f = (x_train_q.astype(np.float32) * in_scale)
    x_test_f = (x_test_q.astype(np.float32) * in_scale)

    train_ds = TensorDataset(torch.from_numpy(x_train_f), torch.from_numpy(y_train))
    test_ds = TensorDataset(torch.from_numpy(x_test_f), torch.from_numpy(y_test))
    train_loader = DataLoader(train_ds, batch_size=args.batch_size, shuffle=True, drop_last=False)
    test_loader = DataLoader(test_ds, batch_size=args.batch_size, shuffle=False)

    model = HarMLP().to(device)
    n_params = count_params(model)
    print(f"Model: 64 -> 32 -> 6 | params={n_params} ({n_params/1000:.2f}K)")
    assert n_params == 2278, f"Expected 2278 params, got {n_params}"

    optim = torch.optim.Adam(model.parameters(), lr=args.lr, weight_decay=1e-4)
    criterion = nn.CrossEntropyLoss()
    best_acc = -1.0
    history = []

    for epoch in range(1, args.epochs + 1):
        model.train()
        total_loss, n = 0.0, 0
        for xb, yb in train_loader:
            xb, yb = xb.to(device), yb.to(device)
            optim.zero_grad(set_to_none=True)
            logits = model(xb)
            loss = criterion(logits, yb)
            loss.backward()
            optim.step()
            total_loss += loss.item() * xb.size(0)
            n += xb.size(0)

        train_acc, _, _ = evaluate(model, train_loader, device)
        test_acc, _, _ = evaluate(model, test_loader, device)
        avg_loss = total_loss / max(n, 1)
        history.append({"epoch": epoch, "loss": avg_loss, "train_acc": train_acc, "test_acc": test_acc})
        print(
            f"Epoch {epoch:03d}/{args.epochs} | loss={avg_loss:.4f} "
            f"| train_acc={train_acc*100:.2f}% | test_acc={test_acc*100:.2f}%"
        )

        if test_acc > best_acc:
            best_acc = test_acc
            torch.save(
                {
                    "model_state": model.state_dict(),
                    "feat_idx": feat_idx,
                    "input_scale": in_scale,
                    "best_acc": best_acc,
                    "epoch": epoch,
                },
                ckpt_dir / "best.pt",
            )

    # Reload best and report
    ckpt = torch.load(ckpt_dir / "best.pt", map_location=device, weights_only=False)
    model.load_state_dict(ckpt["model_state"])
    test_acc, y_true, y_pred = evaluate(model, test_loader, device)
    report = classification_report(
        y_true, y_pred, target_names=ACTIVITY_NAMES, digits=4, output_dict=True
    )
    cm = confusion_matrix(y_true, y_pred)

    print("\n=== Best Test Accuracy: {:.2f}% ===".format(test_acc * 100))
    print(classification_report(y_true, y_pred, target_names=ACTIVITY_NAMES, digits=4))
    print("Confusion matrix:\n", cm)

    # Export float + INT8 weights for chip
    sd = model.state_dict()
    w1 = sd["fc1.weight"].detach().cpu().numpy()
    b1 = sd["fc1.bias"].detach().cpu().numpy()
    w2 = sd["fc2.weight"].detach().cpu().numpy()
    b2 = sd["fc2.bias"].detach().cpu().numpy()

    q1 = quantize_linear_weights(w1, b1)
    q2 = quantize_linear_weights(w2, b2)

    export = {
        "architecture": "64->32->6",
        "params": n_params,
        "best_test_acc": test_acc,
        "input_scale": float(in_scale),
        "selected_feature_indices": feat_idx.tolist(),
        "activity_names": ACTIVITY_NAMES,
        "ops": ["MatVec", "BiasAdd", "ReLU", "MatVec", "BiasAdd", "Argmax"],
    }
    with open(out_dir / "meta.json", "w", encoding="utf-8") as f:
        json.dump(export, f, indent=2)

    np.savez(
        out_dir / "weights_float32.npz",
        fc1_weight=w1,
        fc1_bias=b1,
        fc2_weight=w2,
        fc2_bias=b2,
        feat_idx=feat_idx,
        input_scale=np.array([in_scale], dtype=np.float32),
    )
    np.savez(
        out_dir / "weights_int8.npz",
        fc1_weight_int8=q1["weight_int8"],
        fc1_weight_scale=np.array([q1["weight_scale"]], dtype=np.float32),
        fc1_bias_float32=q1["bias_float32"],
        fc2_weight_int8=q2["weight_int8"],
        fc2_weight_scale=np.array([q2["weight_scale"]], dtype=np.float32),
        fc2_bias_float32=q2["bias_float32"],
        feat_idx=feat_idx,
        input_scale=np.array([in_scale], dtype=np.float32),
        # Sample INT8 inputs for hardware bring-up
        sample_x_int8=x_test_q[:16],
        sample_y=y_test[:16],
    )

    with open(out_dir / "metrics.json", "w", encoding="utf-8") as f:
        json.dump(
            {
                "best_test_acc": test_acc,
                "params": n_params,
                "history": history,
                "classification_report": report,
                "confusion_matrix": cm.tolist(),
            },
            f,
            indent=2,
        )

    # Quick INT8 weight reconstructed accuracy (dequant weights, float act)
    with torch.no_grad():
        w1_dq = torch.from_numpy(q1["weight_int8"].astype(np.float32) * q1["weight_scale"]).to(device)
        b1_t = torch.from_numpy(q1["bias_float32"]).to(device)
        w2_dq = torch.from_numpy(q2["weight_int8"].astype(np.float32) * q2["weight_scale"]).to(device)
        b2_t = torch.from_numpy(q2["bias_float32"]).to(device)

        preds = []
        for xb, _ in test_loader:
            xb = xb.to(device)
            h = torch.relu(xb @ w1_dq.T + b1_t)
            logits = h @ w2_dq.T + b2_t
            preds.append(logits.argmax(dim=1).cpu().numpy())
        y_pred_q = np.concatenate(preds)
        int8_acc = float((y_pred_q == y_true).mean())
        print(f"INT8 weight (PTQ) test accuracy: {int8_acc*100:.2f}%")

    print(f"\nExported to: {out_dir}")
    print(f"Checkpoint: {ckpt_dir / 'best.pt'}")


def parse_args() -> argparse.Namespace:
    root = Path(__file__).resolve().parents[2]
    p = argparse.ArgumentParser()
    p.add_argument(
        "--data-root",
        default=str(root / "data" / "UCI HAR Dataset"),
    )
    p.add_argument(
        "--out-dir",
        default=str(root / "model" / "export"),
    )
    p.add_argument(
        "--ckpt-dir",
        default=str(root / "model" / "training" / "checkpoints"),
    )
    p.add_argument("--epochs", type=int, default=80)
    p.add_argument("--batch-size", type=int, default=128)
    p.add_argument("--lr", type=float, default=1e-3)
    return p.parse_args()


if __name__ == "__main__":
    train(parse_args())
