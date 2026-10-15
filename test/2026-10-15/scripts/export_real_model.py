"""Validate selected trained weights; export exact gold from real HAR inputs.
No checkpoint unpickling or training is needed. NPZ loads disable pickle.
"""
import argparse,hashlib,json,sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from tools.workspace import WORK, TEST_ROOT
sys.path.insert(0,str(ROOT))
from model.reference.mlp_int import infer
from build_har_firmware import pack

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def export(data_root=None,write_fixture=False):
    out=WORK/"real_model";out.mkdir(parents=True,exist_ok=True)
    directory=ROOT/"model/export"
    meta=json.loads((directory/"meta.json").read_text())
    params=json.loads((directory/"quant_params.json").read_text())
    with np.load(directory/"weights_int8.npz",allow_pickle=False) as z:
        arrays={k:z[k].copy() for k in z.files}
    with np.load(directory/"weights_float32.npz",allow_pickle=False) as z:
        floats={k:z[k].copy() for k in z.files}
    w1=arrays["fc1_weight_int8"];w2=arrays["fc2_weight_int8"]
    b1=np.array(params["fc1"]["bias_int32"],dtype=np.int64)
    b2=np.array(params["fc2"]["bias_int32"],dtype=np.int64)
    mult=params["hidden_requant"]["mul"];shift=params["hidden_requant"]["shift"]
    indices=np.array(meta["selected_feature_indices"],dtype=int)
    labels=params["label_order"]
    assert (w1.shape,w2.shape,b1.shape,b2.shape)==((32,64),(6,32),(32,),(6,))
    assert w1.dtype==np.int8 and w2.dtype==np.int8 and len(indices)==64
    assert len(set(indices.tolist()))==64 and np.all((indices>=0)&(indices<561))
    assert np.array_equal(indices,arrays["feat_idx"]) and np.array_equal(indices,floats["feat_idx"])
    assert labels==meta["activity_names"] and labels[3:5]==["SITTING","STANDING"]
    assert 0<=mult<=65535 and 0<=shift<=31
    assert params["hidden_requant"]["round_add"]==1<<(shift-1)
    assert params["argmax_tie"]=="smallest index"
    scale=np.float32(params["input"]["scale"])
    assert scale==arrays["input_scale"][0] and scale==floats["input_scale"][0]
    for layer,weight in [("fc1",w1),("fc2",w2)]:
        f=floats[layer+"_weight"]
        exported_scale=arrays[layer+"_weight_scale"][0]
        original_scale=float(np.max(np.abs(f)))/127.0
        assert np.isclose(exported_scale,original_scale,rtol=1e-7)
        assert np.array_equal(np.clip(np.rint(f/original_scale),-128,127).astype(np.int8),weight)
        assert np.array_equal(floats[layer+"_bias"],arrays[layer+"_bias_float32"])
    bias1_scale=float(scale)*float(arrays["fc1_weight_scale"][0])
    assert np.array_equal(np.rint(floats["fc1_bias"].astype(np.float64)/bias1_scale).astype(np.int64),b1)
    bias2_scale=bias1_scale*params["hidden_requant"]["approximates_divisor"]*float(arrays["fc2_weight_scale"][0])
    assert np.array_equal(np.rint(floats["fc2_bias"].astype(np.float64)/bias2_scale).astype(np.int64),b2)
    # Conservative bounds for every possible INT8 input, not just observed data.
    bounds1=np.abs(b1)+128*np.abs(w1.astype(np.int64)).sum(axis=1)
    bounds2=np.abs(b2)+127*np.abs(w2.astype(np.int64)).sum(axis=1)
    assert max(bounds1.max(),bounds2.max())<2**31
    fixture_path=ROOT/"test/2026-10-15/fixtures/har_uci24.json"
    accuracy=None;source={}
    if data_root:
        data_root=Path(data_root)
        raw=np.loadtxt(data_root/"test/X_test.txt",dtype=np.float32)
        y=np.loadtxt(data_root/"test/y_test.txt",dtype=int)-1
        assert raw.shape==(2947,561) and y.shape==(2947,) and set(y)==set(range(6))
        x=np.clip(np.rint(raw[:,indices]/scale),-128,127).astype(np.int8)
        assert np.array_equal(x[:16],arrays["sample_x_int8"])
        assert np.array_equal(y[:16],arrays["sample_y"])
        row_ids=np.arange(len(x),dtype=int)
        source={"X_test_sha256":sha(data_root/"test/X_test.txt"),"y_test_sha256":sha(data_root/"test/y_test.txt")}
        # Four deterministic, evenly spaced rows within each true class.
        chosen=np.array([ids[j] for c in range(6) for ids in [np.flatnonzero(y==c)] for j in np.linspace(0,len(ids)-1,4,dtype=int)],dtype=int)
        if write_fixture:
            fixture={"dataset":"UCI HAR official test split","source":"https://archive.ics.uci.edu/dataset/240/human+activity+recognition+using+smartphones",
                "citation":"Reyes-Ortiz et al. (2013), DOI 10.24432/C54S4K","license":"CC BY 4.0",
                "sampling":"4 evenly spaced test rows per true class; 0-based dataset row IDs; no use of predictions for selection",
                "selected_feature_indices":indices.tolist(),"input_scale":float(scale),"dataset_files":source,
                "row_ids":chosen.tolist(),"labels":y[chosen].tolist(),"x_int8":x[chosen].tolist()}
            fixture_path.write_text(json.dumps(fixture,indent=2)+"\n",encoding="utf-8")
    else:
        fixture=json.loads(fixture_path.read_text())
        assert fixture["selected_feature_indices"]==indices.tolist() and np.float32(fixture["input_scale"])==scale
        x=np.array(fixture["x_int8"],dtype=np.int8)
        y=np.array(fixture["labels"],dtype=int)
        row_ids=np.array(fixture["row_ids"],dtype=int)
        chosen=np.arange(len(x),dtype=int)
        source=fixture["dataset_files"]
    # Vectorized INT64 implementation is independent of Python scalar infer/RTL.
    acc=x.astype(np.int64)@w1.astype(np.int64).T+b1
    hidden=np.minimum(127,(np.maximum(acc,0)*mult+(1<<(shift-1)))>>shift).astype(np.int8)
    scores=hidden.astype(np.int64)@w2.astype(np.int64).T+b2
    pred=np.argmax(scores,axis=1)
    w1_list,w2_list=w1.tolist(),w2.tolist()
    for n in range(len(x)):
        h,s,c=infer(x[n].tolist(),w1_list,w2_list,b1.tolist(),b2.tolist(),mult,shift)
        assert h==hidden[n].tolist() and s==scores[n].tolist() and c==int(pred[n])
    if data_root:
        xf=x.astype(np.float32)*scale
        hf=np.maximum(0,xf@floats["fc1_weight"].T+floats["fc1_bias"])
        pf=np.argmax(hf@floats["fc2_weight"].T+floats["fc2_bias"],axis=1)
        hq=np.maximum(0,xf@(w1.astype(np.float32)*arrays["fc1_weight_scale"][0]).T+arrays["fc1_bias_float32"])
        pq=np.argmax(hq@(w2.astype(np.float32)*arrays["fc2_weight_scale"][0]).T+arrays["fc2_bias_float32"],axis=1)
        confusion=np.zeros((6,6),dtype=int)
        np.add.at(confusion,(y,pred),1)
        accuracy={"count":len(x),"float_correct":int((pf==y).sum()),"float_accuracy":float((pf==y).mean()),
            "weight_ptq_correct":int((pq==y).sum()),"weight_ptq_accuracy":float((pq==y).mean()),
            "integer_correct":int((pred==y).sum()),"integer_accuracy":float((pred==y).mean()),
            "confusion_matrix":confusion.tolist(),"label_order":labels,
            "scope":"Supplied checkpoint evaluated on its original UCI test split; checkpoint was selected using that split, not a fresh held-out evaluation"}
    words=pack(w1.ravel().tolist()+w2.ravel().tolist())+b1.tolist()+b2.tolist()+[mult,shift]
    assert len(words)==600
    (out/"weights.hex").write_text("".join(f"{v & 0xffffffff:08x}\n" for v in words),encoding="ascii")
    def write_vectors(path,selection):
        with path.open("w",encoding="ascii") as f:
            for n in selection:
                record=x[n].tolist()+hidden[n].tolist()+scores[n].tolist()+[int(pred[n]),int(y[n]),int(row_ids[n])]
                assert len(record)==105
                f.write("".join(f"{v & 0xffffffff:08x}\n" for v in record))
    write_vectors(out/"samples.hex",range(len(x)))
    write_vectors(out/"soc24.hex",chosen)
    metadata={"model_version":params["model_version"],"sample_count":len(x),"soc_count":len(chosen),
        "multiplier":mult,"shift":shift,"words_per_sample":105,"label_order":labels,
        "samples_kind":"full UCI test split" if data_root else "24 stratified real test fixtures",
        "integer_correct":int((pred==y).sum()),"accuracy":accuracy,"dataset":source,
        "soc_integer_correct":int((pred[chosen]==y[chosen]).sum()),
        "soc_true_label_counts":np.bincount(y[chosen],minlength=6).tolist(),
        "accumulator_bound_fc1":int(bounds1.max()),"accumulator_bound_fc2":int(bounds2.max()),
        "source_sha256":{n:sha(directory/n) for n in ["meta.json","quant_params.json","weights_int8.npz","weights_float32.npz"]},
        "vectors_sha256":{n:sha(out/n) for n in ["weights.hex","samples.hex","soc24.hex"]},
        "exported_npz16_labels":np.bincount(arrays["sample_y"],minlength=6).tolist()}
    (out/"manifest.json").write_text(json.dumps(metadata,indent=2)+"\n")
    print(json.dumps(metadata,ensure_ascii=False),flush=True)
    return metadata

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--data-root",type=Path)
    p.add_argument("--write-fixture",action="store_true")
    args=p.parse_args()
    if args.write_fixture and not args.data_root:p.error("--write-fixture requires --data-root")
    export(args.data_root,args.write_fixture)
