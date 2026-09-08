"""Scalar checks for the written lemmas, not circuit or held-out accuracy tests."""
import argparse
import json
import math
from pathlib import Path


def step(s, t):
    assert s % 2 and t % 2
    e = ((s >> 1) ^ (t >> 1)) & 1
    u = (t + (-1 if e else 1) * s) // 2
    assert u % 2 and math.gcd(s, u) == math.gcd(s, t)
    a, b = abs(s), abs(t)
    average = (a - b) % 4 == 0
    expected = (a + b) // 2 if average else abs(a - b) // 2
    assert abs(u) == expected
    return u, average


def check_walk(s, t):
    assert math.gcd(s, t) == 1
    n = max(abs(s), abs(t)).bit_length()
    rounds = 0
    while max(abs(s), abs(t)) > 1:
        initial_max = max(abs(s), abs(t))
        length = 0
        while True:
            u, average = step(s, t)
            s, t = u, s
            rounds += 1
            length += 1
            if max(abs(s), abs(t)) == 1:
                break
            if not average:
                u, _ = step(s, t)
                s, t = u, s
                rounds += 1
                length += 1
                assert 4 * max(abs(s), abs(t)) <= 3 * initial_max
                break
        assert length <= n + 1
        assert rounds <= 3 * n * (n + 1)
    return rounds


def generate():
    walks = 0
    longest = 0
    for s in range(-255, 256, 2):
        for t in range(-255, 256, 2):
            if math.gcd(s, t) != 1:
                continue
            longest = max(longest, check_walk(s, t))
            walks += 1
    checked = outside = 0
    for n, f in ((4, 3), (5, 3), (6, 5), (7, 5), (8, 17)):
        radix = 1 << n
        p = radix - f
        for z in range(p):
            for y in range(p):
                for sign in (0, 1):
                    d, z0 = divmod(2 * z, radix)
                    frame = z0 if sign == 0 else radix - 1 - z0
                    o, omega = divmod(frame + y, radix)
                    kappa = o + (-1 if sign else 1) * d
                    routed = d & (sign ^ o)
                    minus = routed & sign
                    plus2 = routed ^ minus
                    plus = d ^ o ^ minus
                    assert plus + plus2 + minus <= 1
                    assert kappa == plus + 2 * plus2 - minus
                    folded = omega + kappa * f
                    if not 0 <= folded < radix:
                        outside += 1
                        continue
                    result = folded if sign == 0 else radix - 1 - folded
                    assert result % p == (2 * z + (-1 if sign else 1) * y) % p
                    assert (folded & 1) ^ sign ^ (y & 1) ^ o == d
                    checked += 1
    return {
        "scope": "Exhaustive small signed recurrence and guarded scalar replay checks. Not gate-level simulation, a 256-bit error estimate, or a replacement for the written proof.",
        "signed_coprime_pairs": walks,
        "maximum_small_rounds": longest,
        "guarded_fusion_cases": checked,
        "outside_fold_guard_cases": outside,
        "conservative_256_bit_bound": 3 * 256 * 257,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    result = json.dumps(generate(), indent=2) + "\n"
    target = Path(__file__).resolve().parents[1] / "evidence" / "replay-algebra-checks.json"
    if args.check:
        assert target.read_text() == result
    else:
        target.write_text(result)
    print(result, end="")
