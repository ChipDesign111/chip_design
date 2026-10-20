"""Compare HAR PTQ precisions; calibrate on train only, evaluate all test rows.

This is a numerical design study, not a low-bit RTL or DMA overlap test.
No checkpoint loading, retraining, or modifications to model/export are needed.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path
import sys
import zipfile

import numpy as np

ROOT = Path(__file__).resolve().parents[2]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def extract_train(data: Path, archive: Path) -> None:
    """Read only explicitly named training files from the existing official ZIP."""
    if all((data / "train" / name).exists() for name in
           ("X_train.txt", "y_train.txt", "subject_train.txt")):
        return
    with zipfile.ZipFile(archive) as outer:
        nested = [n for n in outer.namelist() if n.endswith("UCI HAR Dataset.zip")]
        payload = io.BytesIO(outer.read(nested[0])) if nested else archive
        with zipfile.ZipFile(payload) as dataset:
            for name in ("X_train.txt", "y_train.txt", "subject_train.txt"):
                target = data / "train" / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(dataset.read("UCI HAR Dataset/train/" + name))


def pack_nibbles(values) -> list[int]:
    values = np.asarray(values, dtype=np.int64).reshape(-1)
    if len(values) % 8 or np.any(values < -8) or np.any(values > 15):
        raise ValueError("Need groups of eight valid signed/unsigned nibbles")
    return [sum((int(v) & 15) << (4 * k) for k, v in enumerate(values[i:i+8]))
            for i in range(0, len(values), 8)]


def unpack_nibbles(words, signed: bool) -> list[int]:
    values = [(int(word) >> (4 * k)) & 15 for word in words for k in range(8)]
    return [v - 16 if signed and v >= 8 else v for v in values]


def evaluate(data: Path, output: Path) -> dict:
    export = ROOT / "model/export"
    with np.load(export / "weights_float32.npz", allow_pickle=False) as z:
        f = {key: z[key].astype(np.float64) for key in z.files}
    with np.load(export / "weights_int8.npz", allow_pickle=False) as z:
        old = {key: z[key].copy() for key in z.files}
    params = json.loads((export / "quant_params.json").read_text(encoding="utf-8"))
    indices = old["feat_idx"].astype(int)
    train = np.loadtxt(data / "train/X_train.txt", usecols=indices, dtype=np.float64)
    test = np.loadtxt(data / "test/X_test.txt", usecols=indices, dtype=np.float64)
    labels = np.loadtxt(data / "test/y_test.txt", dtype=int) - 1
    assert train.shape == (7352, 64) and test.shape == (2947, 64)
    assert np.isfinite(train).all() and np.isfinite(test).all()
    output.mkdir(parents=True, exist_ok=True)

    # Reproduce the deployed integer baseline independently of candidate calibration.
    w1_old = old["fc1_weight_int8"].astype(np.int64)
    w2_old = old["fc2_weight_int8"].astype(np.int64)
    x_old = np.clip(np.rint(test / params["input"]["scale"]), -128, 127).astype(np.int64)
    a_old = x_old @ w1_old.T + np.array(params["fc1"]["bias_int32"])
    rq = params["hidden_requant"]
    h_old = np.minimum(127, (np.maximum(a_old, 0) * rq["mul"] + rq["round_add"]) >> rq["shift"])
    p_old = np.argmax(h_old @ w2_old.T + np.array(params["fc2"]["bias_int32"]), axis=1)
    baseline = {"name": "deployed_W8_I8_H7", "correct": int((p_old == labels).sum()),
                "samples": len(labels), "accuracy": float((p_old == labels).mean())}
    assert baseline["correct"] == 2504, "Deployed baseline changed"

    # Use one scale per weight tensor. All FC2 scores therefore share a scale.
    # I4/I2 use symmetric narrow ranges [-7,7]/[-1,1], stored as two's complement.
    # H4/H2 exploit ReLU and use all unsigned codes [0,15]/[0,3]. H8 uses [0,127]
    # for compatibility with the existing signed INT8 second-layer activation.
    candidates = []
    selected = None
    for wb, ib, hb in ((8, 8, 8), (8, 4, 8), (8, 4, 4), (4, 8, 8),
                       (4, 4, 4), (2, 4, 4), (8, 2, 2), (2, 2, 2)):
        wmax = (1 << (wb - 1)) - 1
        imax = (1 << (ib - 1)) - 1
        hmax = 127 if hb == 8 else (1 << hb) - 1
        sx = float(np.max(np.abs(train))) / imax
        if wb == 8:
            w1, w2 = w1_old, w2_old
            sw1 = float(old["fc1_weight_scale"][0])
            sw2 = float(old["fc2_weight_scale"][0])
        else:
            sw1 = float(np.max(np.abs(f["fc1_weight"]))) / wmax
            sw2 = float(np.max(np.abs(f["fc2_weight"]))) / wmax
            w1 = np.clip(np.rint(f["fc1_weight"] / sw1), -wmax, wmax).astype(np.int64)
            w2 = np.clip(np.rint(f["fc2_weight"] / sw2), -wmax, wmax).astype(np.int64)
        b1 = np.rint(f["fc1_bias"] / (sx * sw1)).astype(np.int64)

        def inputs(x):
            return np.clip(np.rint(x / sx), -imax, imax).astype(np.int64)

        def accum(x):
            return np.maximum(0, inputs(x) @ w1.T + b1)

        real_hidden = accum(train) * (sx * sw1)
        # Calibration objective is hidden reconstruction MSE on training rows only.
        # Neither test labels nor test activations choose clipping or integer scales.
        options = []
        for percentile in (95, 97, 98, 99, 99.5, 99.9, 99.99, 100):
            cap = float(np.percentile(real_hidden, percentile))
            sh = cap / hmax
            restored = np.clip(np.floor(real_hidden / sh + .5), 0, hmax) * sh
            options.append((float(np.mean((real_hidden - restored) ** 2)), sh, percentile))
        mse, sh, percentile = min(options)
        ratio = sx * sw1 / sh
        shift = 31
        while int(np.floor(ratio * (1 << shift) + .5)) > 65535:
            shift -= 1
        assert shift > 0
        multiplier = int(np.floor(ratio * (1 << shift) + .5))
        assert 0 < multiplier <= 65535
        b2 = np.rint(f["fc2_bias"] / (sh * sw2)).astype(np.int64)
        a1 = accum(test)
        hidden = np.clip((a1 * multiplier + (1 << (shift - 1))) >> shift, 0, hmax)
        scores = hidden @ w2.T + b2
        predicted = np.argmax(scores, axis=1)
        bound1 = np.abs(b1) + imax * np.abs(w1).sum(axis=1)
        bound2 = np.abs(b2) + hmax * np.abs(w2).sum(axis=1)
        assert max(bound1.max(), bound2.max()) < (1 << 31)
        confusion = np.zeros((6, 6), dtype=int)
        np.add.at(confusion, (labels, predicted), 1)
        result = {"name": f"W{wb}_I{ib}_H{hb}", "weight_bits": wb,
                  "input_bits": ib, "hidden_storage_bits": hb,
                  "input_range": [-imax, imax], "weight_range": [-wmax, wmax],
                  "hidden_range": [0, hmax], "input_bytes": 64 * ib // 8,
                  "correct": int((predicted == labels).sum()), "samples": len(labels),
                  "accuracy": float((predicted == labels).mean()),
                  "difference_from_deployed_pp": 100 * float((predicted == labels).mean() - baseline["accuracy"]),
                  "input_scale": sx, "fc1_weight_scale": sw1, "fc2_weight_scale": sw2,
                  "hidden_scale": sh, "calibration_percentile": percentile,
                  "calibration_hidden_mse": mse, "requant_multiplier": multiplier,
                  "requant_shift": shift, "bias1_int32": b1.tolist(), "bias2_int32": b2.tolist(),
                  "fc1_accumulator_bound": int(bound1.max()),
                  "fc2_accumulator_bound": int(bound2.max()),
                  "confusion_matrix": confusion.tolist()}
        candidates.append(result)
        if (wb, ib, hb) == (8, 4, 4):
            selected = result
            # Exhaustive nibble packing, then 24 scalar matvec/round/argmax checks.
            for signed in (False, True):
                domain = list(range(-8, 8)) if signed else list(range(16))
                assert unpack_nibbles(pack_nibbles(domain), signed) == domain
            fixture = json.loads((ROOT / "test/2026-10-15/fixtures/har_uci24.json").read_text(encoding="utf-8"))
            cases = []
            for row in fixture["row_ids"]:
                x = inputs(test[row]).tolist()
                packed = pack_nibbles(x)
                assert unpack_nibbles(packed, True) == x
                a = [int(b1[j]) + sum(int(w1[j, i]) * x[i] for i in range(64)) for j in range(32)]
                h = [min(hmax, (max(v, 0) * multiplier + (1 << (shift-1))) >> shift) for v in a]
                assert unpack_nibbles(pack_nibbles(h), False) == h
                s = [int(b2[k]) + sum(int(w2[k, j]) * h[j] for j in range(32)) for k in range(6)]
                c = max(range(6), key=lambda k: s[k])
                assert h == hidden[row].tolist() and s == scores[row].tolist() and c == int(predicted[row])
                cases.append({"row_id": row, "input_words_u32": packed, "hidden_u4": h,
                              "scores_int32": s, "class_id": c, "label": int(labels[row])})
            (output / "w8a4_soc24_gold.json").write_text(json.dumps(cases, indent=2) + "\n", encoding="utf-8")
        print(f"{result['name']}: {result['correct']}/{len(labels)} = {100*result['accuracy']:.4f}%", flush=True)

    report = {"schema_version": 1, "scope": "Numerical PTQ study; low-bit RTL/DMA overlap not implemented or measured",
              "calibration": "7352 official train rows, hidden reconstruction MSE; test split excluded from calibration",
              "evaluation": "2947 official test rows; existing checkpoint was historically selected using this split, not a new blind test",
              "method": "No QAT; per-tensor symmetric narrow-range weights/inputs; unsigned low-bit ReLU; INT32 bias/accum; shared FC2 score scale",
              "python": sys.version.split()[0], "numpy": np.__version__, "baseline": baseline,
              "candidates": candidates, "recommended": selected["name"],
              "recommendation_status": "Architecture proposal; <=1 percentage-point loss versus deployed INT8 used as an engineering target",
              "packing_checks": {"all_signed_unsigned_nibbles": True, "scalar_gold_rows": 24},
              "source_sha256": {str(p.relative_to(ROOT)).replace('\\', '/'): sha(p) for p in
                  [Path(__file__).resolve(), export / "weights_float32.npz", export / "weights_int8.npz", export / "quant_params.json"]},
              "dataset_sha256": {rel: sha(data / rel) for rel in
                  ("train/X_train.txt", "train/y_train.txt", "test/X_test.txt", "test/y_test.txt")}}
    (output / "results.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, default=ROOT / "model/data/UCI HAR Dataset")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--extract-train", action="store_true", help="Extract train files from existing official ZIP in model/data")
    args = parser.parse_args()
    if args.extract_train:
        extract_train(args.data_root, ROOT / "model/data/uci_har_official.zip")
    evaluate(args.data_root, args.output)


if __name__ == "__main__":
    main()
