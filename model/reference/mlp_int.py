"""Exact V1 integer contract, independent of RTL implementation."""
def infer(x, w1, w2, b1, b2, multiplier=1, shift=0):
    if not 0 <= multiplier <= 65535 or not 0 <= shift <= 31:
        raise ValueError('Invalid requantization configuration')
    if len(x) != 64 or len(w1) != 32 or any(len(row) != 64 for row in w1):
        raise ValueError('Invalid first-layer shape')
    if len(w2) != 6 or any(len(row) != 32 for row in w2) or len(b1) != 32 or len(b2) != 6:
        raise ValueError('Invalid second-layer shape')
    if any(not -128 <= value <= 127 for value in x + sum(w1, []) + sum(w2, [])):
        raise ValueError('INT8 operand out of range')
    def checked(value):
        if not -(1 << 31) <= value < (1 << 31):
            raise ValueError('Accumulator overflow is outside the V1 contract')
        return value
    hidden = []
    for row, bias in zip(w1, b1):
        acc = checked(bias)
        for weight, value in zip(row, x):
            acc = checked(acc + weight * value)
        scaled = max(acc, 0) * multiplier
        rounded = (scaled + (1 << (shift-1))) >> shift if shift else scaled
        hidden.append(min(127, rounded))
    scores = []
    for row, bias in zip(w2, b2):
        acc = checked(bias)
        for weight, value in zip(row, hidden):
            acc = checked(acc + weight * value)
        scores.append(acc)
    category = max(range(6), key=lambda index: scores[index])
    return hidden, scores, category
