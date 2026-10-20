"""Scalar W8A4 golden inference, independent of the vectorized test exporter."""
from pathlib import Path
from functools import lru_cache
import json
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
@lru_cache(maxsize=1)
def parameters():
    q=json.loads((ROOT/'model/quantization/w8a4.json').read_text())
    with np.load(ROOT/'model/weights.npz',allow_pickle=False) as z:
        return z['fc1_weight_int8'].tolist(),z['fc2_weight_int8'].tolist(),q
def infer(x):
    w1,w2,q=parameters()
    if len(x)!=64 or any(not -7<=int(v)<=7 for v in x):raise ValueError('Expected 64 signed INT4 values in -7..7')
    acc=[sum(int(a)*int(b) for a,b in zip(x,row))+bias for row,bias in zip(w1,q['bias1_int32'])]
    h=[min(15,(max(v,0)*q['requant_multiplier']+(1<<(q['requant_shift']-1)))>>q['requant_shift']) for v in acc]
    scores=[sum(a*int(b) for a,b in zip(h,row))+bias for row,bias in zip(w2,q['bias2_int32'])]
    return h,scores,max(range(6),key=lambda i:scores[i])
