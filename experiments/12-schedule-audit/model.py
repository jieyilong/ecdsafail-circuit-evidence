"""Exact denominator model only: no gate, payload, phase, or qubit simulation."""
from math import gcd

P = 2**256 - 2**32 - 977
BUDGETS = (704, 736, 768, 800)


def width(k, margin=20):
    if k < 40:
        raw = 256 + margin - 17 * k // 100
    elif k < 304:
        raw = 250 + margin - 33 * (k - 40) // 100
    else:
        raw = 163 + margin - 40 * (k - 304) // 100
    return min(259, max(8, raw))


def fits(x, w):
    return -(1 << (w - 1)) <= x < (1 << (w - 1))


def ordinary(source, target):
    # Select the numerator congruent to 2 modulo 4, including negative words.
    sign = int(source % 4 != target % 4)
    total = target - source if sign else target + source
    assert total % 4 == 2
    result = total // 2
    assert 2 * result - (-source if sign else source) == target
    return result, total, sign


def initial(d, p=P):
    if not 0 < d < p:
        raise ValueError("require a nonzero canonical denominator")
    if p % 4 != 3:
        raise ValueError("this specialized initialization requires p = 3 mod 4")
    lifted = d if d % 2 else d - p
    value, _, _ = ordinary(p, lifted)
    fused = d // 2 - p + ((d // 2) % 2) * p + (d % 2) * ((p + 1) // 2)
    assert value == fused
    assert abs(value) < p and value % 2 == 1
    assert (2 * value - d) % p == 0
    return value


def walk(d, limit=800, trace=False):
    """Stop at first signed-unit pair; None means censored, never limit+1 rounds."""
    u, v = P, d
    misses = {"base704": None, "guarded736": None, "candidate768": None}
    schedules = (("base704", 704, 4), ("guarded736", 736, 20),
                 ("candidate768", 768, 20))
    history = []
    terminal = None
    for k in range(limit):
        before_u, before_v = u, v
        if k == 0:
            v = initial(d)
            total, sign = None, d % 2  # Fused source tape bit, not ordinary sign.
        else:
            if k % 2:
                u, total, sign = ordinary(v, u)
            else:
                v, total, sign = ordinary(u, v)
            assert max(abs(u), abs(v)) <= max(abs(before_u), abs(before_v))
        assert abs(u) <= P and abs(v) <= P
        assert fits(u, 257) and fits(v, 257)
        if total is not None:
            assert abs(total) <= 2 * P and fits(total, 258)
        for name, budget, margin in schedules:
            if k >= budget or misses[name] is not None:
                continue
            w = width(k, margin)
            kind = ("input_width" if not (fits(before_u, w) and fits(before_v, w))
                    else "sum_width" if total is not None and not fits(total, w) else None)
            if kind:
                misses[name] = {"k": k, "kind": kind, "width": w,
                                "u": str(before_u), "v": str(before_v),
                                "pre_halving_sum": str(total) if total is not None else None}
        if trace:
            history.append({"k": k, "u_before": str(before_u), "v_before": str(before_v),
                            "tape_bit": sign, "sum": str(total) if total is not None else "",
                            "u_after": str(u), "v_after": str(v)})
        if abs(u) == abs(v) == 1:
            terminal = k + 1
            break
    return {"first_terminal_round": terminal, "limit": limit,
            "u": str(u), "v": str(v), "misses": misses, "trace": history}


def magnitude_walk(d, limit=4096):
    """Independent unsigned average/difference formulation of ordinary steps."""
    a = P
    b = abs(d // 2 - P * (1 - ((d >> 1) & 1)) + (d & 1) * ((P + 1) // 2))
    for count in range(1, limit + 1):
        if a == b == 1:
            return count
        if count == limit:
            return None
        new = (a + b) // 2 if a % 4 == b % 4 else abs(a - b) // 2
        if count % 2:
            a = new
        else:
            b = new
    raise AssertionError("unreachable")


def small_pair_check(bound=63):
    cases, maximum = 0, 0
    for a in range(-bound, bound + 1, 2):
        for b in range(-bound, bound + 1, 2):
            if gcd(a, b) != 1:
                continue
            u, v = a, b
            n = max(abs(a), abs(b)).bit_length()
            budget = 3 * n * (n + 1)
            for k in range(budget + 1):
                if abs(u) == abs(v) == 1:
                    maximum = max(maximum, k)
                    break
                assert k < budget
                old_max = max(abs(u), abs(v))
                if k % 2:
                    u, _, _ = ordinary(v, u)
                else:
                    v, _, _ = ordinary(u, v)
                assert gcd(u, v) == 1
                assert max(abs(u), abs(v)) <= old_max
            cases += 1
    return {"signed_coprime_pairs": cases, "max_abs_input": bound, "max_rounds": maximum}
