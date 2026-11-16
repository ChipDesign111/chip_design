"""Single-FC integer reference and software tiling for the shared HAR datapath.

Tiles retain the FC1 order: input pair, padded output, input lane.
Jobs for one output block must execute consecutively to retain INT22 partial sums.
"""
from model.reference.mlp_int import wrap_accumulator


def plan_fc(xs, weights, bias, base=0x80000000):
    b, n = len(xs), len(weights)
    if not 1 <= b <= 4 or not n or len(bias) != n:
        raise ValueError("Invalid batch/output shape")
    k = len(xs[0])
    if not k or any(len(x) != k for x in xs) or any(len(w) != k for w in weights):
        raise ValueError("Invalid input shape")
    if any(not -128 <= v <= 127 for row in xs + weights for v in row):
        raise ValueError("INT8 operand out of range")
    if any(not -(1 << 21) <= v < (1 << 21) for v in bias):
        raise ValueError("INT22 bias out of range")
    jobs, image = [], bytearray()
    for no in range(0, n, 32):
        nn = min(32, n-no)
        padded_n = (nn+7)//8*8
        for ko in range(0, k, 64):
            kk = min(64, k-ko)
            payload = bytes((weights[no+o][ko+2*t+lane] & 255)
                            if o < nn and 2*t+lane < kk else 0
                            for t in range((kk+1)//2)
                            for o in range(padded_n) for lane in range(2))
            jobs.append(dict(k=kk, n=nn, batch=b, accumulate=ko != 0,
                             source=base+len(image), output_offset=no,
                             inputs=[row[ko:ko+kk] for row in xs], bias=bias[no:no+nn]))
            image.extend(payload)
    if base % 4 or base < 0x80000000 or base + len(image) > 0x80002000:
        raise ValueError("Packed weights do not fit physical SRAM")
    return jobs, bytes(image)


def reference_fc(xs, weights, bias):
    # Exact modulo arithmetic; callers must separately prove no overflow when
    # mathematical rather than wrapping integer results are required.
    return [[wrap_accumulator(bias[o] + sum(a*w for a, w in zip(x, row)))
             for o, row in enumerate(weights)] for x in xs]
