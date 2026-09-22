"""Exact scalar specification, NOT a gate simulator or quantum cost model."""

from dataclasses import dataclass

SECP256K1_P = 2**256 - 2**32 - 977


def iterations(n):
    """Bernstein-Yang (2019), Figure 11.1 / Theorem 11.2."""
    return (49 * n + (80 if n < 46 else 57)) // 17


@dataclass(frozen=True)
class Value:
    delta: int
    f: int
    g: int


def decisions(v):
    e = v.g & 1
    return e, int(v.delta > 0 and e == 1)


def forward(v):
    assert v.f & 1
    e, s = decisions(v)
    if s:
        out = Value(1 - v.delta, v.g, (v.g - v.f) // 2)
    else:
        out = Value(1 + v.delta, v.f, (v.g + e * v.f) // 2)
    return out, (e, s)


def predecessor(v, record):
    e, s = record
    assert e in (0, 1) and s in (0, 1) and s <= e
    if s:
        old = Value(1 - v.delta, v.f - 2 * v.g, v.f)
    else:
        old = Value(v.delta - 1, v.f, 2 * v.g - e * v.f)
    assert old.f & 1
    assert decisions(old) == record, "record inconsistent with predecessor"
    return old


def inverse_and_clear(v, record):
    old = predecessor(v, record)
    e, s = decisions(old)
    # This is the scalar meaning of recomputation-XOR, not a discard/reset.
    return old, (record[0] ^ e, record[1] ^ s)


def half(x, p):
    x %= p
    return (x + (x & 1) * p) // 2


def coefficient_forward(pair, record, p):
    a, b = pair
    e, s = record
    if s:
        return b, half(b - a, p)
    return a, half(b + e * a, p)


def coefficient_inverse(pair, record, p):
    a, b = pair
    e, s = record
    if s:
        return (a - 2 * b) % p, a
    return a, (2 * b - e * a) % p


def matrix(record):
    """Integer M = 2 L; det(M)=2, so det(L)=1/2."""
    e, s = record
    return ((0, 2), (-1, 1)) if s else ((2, 0), (e, 1))


def walk(p, z):
    assert p > 2 and p & 1 and 0 < z < p
    v = Value(1, p, z)
    tape = []
    for _ in range(iterations(p.bit_length())):
        v, record = forward(v)
        tape.append(record)
    assert v.g == 0 and abs(v.f) == 1, "requires invertible denominator"
    return v, tape


def restore(v, tape):
    for j in range(len(tape) - 1, -1, -1):
        v, tape[j] = inverse_and_clear(v, tape[j])
    assert all(record == (0, 0) for record in tape)
    return v


def payload_map(p, z, c, divide=True):
    """ABI (z,c,0_scratch) -> (z,c/z or z*c,0_scratch), modulo p.

    Value.g borrows the denominator's wires; pair[1] is the payload ABI bank.
    The first pair bank starts/ends zero. All branches here are scalar oracles
    for future coherent gates, never free classical circuit routing.
    """
    assert 0 <= c < p
    terminal, tape = walk(p, z)
    if divide:
        pair = (0, c)
        for record in tape:
            pair = coefficient_forward(pair, record, p)
        assert pair[1] == 0
        pair = ((terminal.f * pair[0]) % p, pair[1])
        pair = (pair[1], pair[0])
    else:
        pair = (0, c)
        pair = (pair[1], pair[0])
        pair = ((terminal.f * pair[0]) % p, pair[1])
        for record in reversed(tape):
            pair = coefficient_inverse(pair, record, p)
    assert pair[0] == 0
    initial = restore(terminal, tape)
    assert initial == Value(1, p, z)
    # Constant unloads XOR p and 1 into f and delta; extension wires are zero.
    scratch = (initial.f ^ p, initial.delta ^ 1, pair[0], tuple(tape))
    assert scratch[:3] == (0, 0, 0)
    return initial.g, pair[1], scratch
