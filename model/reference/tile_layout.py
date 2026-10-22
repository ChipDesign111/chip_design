"""Exact on-SRAM layout for the current 2x32 / 1x6 INT8 engines."""
import ast,json,struct,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def weights():
    result=[]
    with zipfile.ZipFile(ROOT/'model/export/weights_int8.npz') as archive:
        for name,shape in [('fc1_weight_int8.npy',(32,64)),('fc2_weight_int8.npy',(6,32))]:
            raw=archive.read(name)
            if raw[:8]!=b'\x93NUMPY\x01\x00':raise ValueError('Expected checked NPY v1 weight export')
            header_bytes=struct.unpack('<H',raw[8:10])[0]
            header=ast.literal_eval(raw[10:10+header_bytes].decode('ascii'))
            data=raw[10+header_bytes:]
            if header['descr']!='|i1' or header['fortran_order'] or header['shape']!=shape or len(data)!=shape[0]*shape[1]:
                raise ValueError('Weight type/order/shape differs from INT8 contract')
            values=struct.unpack('%db'%len(data),data)
            result.append([list(values[o*shape[1]:(o+1)*shape[1]]) for o in range(shape[0])])
    return result
def encode(w1,w2):
    first=bytes(w1[o][2*t+k]&255 for t in range(32) for o in range(32) for k in range(2))
    second=bytes((w2[o][t]&255) if o<6 else 0 for t in range(32) for o in range(8))
    return first,second
def parameters():return json.loads((ROOT/'model/export/quant_params.json').read_text())
