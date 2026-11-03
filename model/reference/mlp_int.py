"""Exact current INT8/INT22 integer contract, independent of RTL implementation."""
ACCUMULATOR_BITS = 22

def wrap_accumulator(value):
    extrema = 1 << (ACCUMULATOR_BITS - 1)
    return ((value + extrema) % (1 << ACCUMULATOR_BITS)) - extrema

def infer(x, w1, w2, b1, b2, multiplier=1, shift=0):
    if not 0 <= multiplier <= 65535 or not 0 <= shift <= 31:
        raise ValueError('Invalid requantization configuration')
    if len(x) != 64 or len(w1) != 32 or any(len(row) != 64 for row in w1):
        raise ValueError('Invalid first-layer shape')
    if len(w2) != 6 or any(len(row) != 32 for row in w2) or len(b1) != 32 or len(b2) != 6:
        raise ValueError('Invalid second-layer shape')
    if any(not -128 <= value <= 127 for value in x + sum(w1, []) + sum(w2, [])):
        raise ValueError('INT8 operand out of range')
    hidden = []
    for row, bias in zip(w1, b1):
        acc = wrap_accumulator(bias)
        for weight, value in zip(row, x):
            acc = wrap_accumulator(acc + weight * value)
        scaled = max(acc, 0) * multiplier
        rounded = (scaled + (1 << (shift-1))) >> shift if shift else scaled
        hidden.append(min(127, rounded))
    scores = []
    for row, bias in zip(w2, b2):
        acc = wrap_accumulator(bias)
        for weight, value in zip(row, hidden):
            acc = wrap_accumulator(acc + weight * value)
        scores.append(acc)
    category = max(range(6), key=lambda index: scores[index])
    return hidden, scores, category
