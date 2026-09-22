"""Deterministic, dependency-free scalar tests; writes only beside this file."""

import hashlib
import json
from pathlib import Path
import random
import time

from scalar import (SECP256K1_P, Value, coefficient_forward,
                    coefficient_inverse, decisions, forward, half,
                    inverse_and_clear, iterations, matrix, payload_map)


def main():
    start = time.monotonic()
    rng = random.Random(20260922)
    counts = {"local_signed_states": 0, "coefficient_pairs": 0,
              "small_field_payloads": 0, "secp_denominators": 0,
              "secp_payloads": 0, "checked_trajectory_rounds": 0}
    coverage = {"negative_g": 0, "delta_zero": 0, "padded_rounds": 0,
                "branch_00": 0, "branch_10": 0, "branch_11": 0}
    max_abs_delta = 0
    max_first_zero = 0
    corpus = hashlib.sha256()

    for delta in range(-8, 9):
        for f in range(-15, 16, 2):
            for g in range(-16, 17):
                old = Value(delta, f, g)
                new, record = forward(old)
                back, cleared = inverse_and_clear(new, record)
                assert (back, cleared) == (old, (0, 0))
                assert forward(back) == (new, record)
                counts["local_signed_states"] += 1

    # Adversarial collision proves successor-only parity erasure is invalid.
    x, rx = forward(Value(0, 3, 2))
    y, ry = forward(Value(0, 3, -1))
    assert x == y == Value(1, 3, 1) and rx != ry
    for p in (3, 5, 7, 11, 13, 17, 31):
        for record in ((0, 0), (1, 0), (1, 1)):
            m = matrix(record)
            assert m[0][0] * m[1][1] - m[0][1] * m[1][0] == 2
            for a in range(p):
                assert half(2 * a, p) == a
                for b in range(p):
                    pair = a, b
                    new = coefficient_forward(pair, record, p)
                    assert coefficient_inverse(new, record, p) == pair
                    assert coefficient_forward(coefficient_inverse(pair, record, p), record, p) == pair
                    assert new == tuple(half(row[0] * a + row[1] * b, p) for row in m)
                    counts["coefficient_pairs"] += 1

    def check_payload(p, z, c):
        zd, out, scratch = payload_map(p, z, c)
        assert zd == z and out == c * pow(z, -1, p) % p
        zm, product, _ = payload_map(p, z, c, divide=False)
        assert zm == z and product == z * c % p
        assert payload_map(p, z, out, divide=False)[1] == c
        assert payload_map(p, z, product)[1] == c
        assert scratch[:3] == (0, 0, 0)

    primes = [p for p in range(3, 128, 2)
              if all(p % d for d in range(2, int(p**0.5) + 1))]
    for p in primes:
        for z in range(1, p):
            for c in range(p):
                check_payload(p, z, c)
                counts["small_field_payloads"] += 1

    p = SECP256K1_P
    denominators = {1, 2, 3, p - 1, p - 2, (p - 1) // 2, (p + 1) // 2}
    denominators.update(1 << k for k in range(256))
    denominators.update(p - (1 << k) for k in range(256))
    denominators.update(rng.randrange(1, p) for _ in range(256))
    for z in sorted(denominators):
        corpus.update(z.to_bytes(32, "big"))
        v, pair = Value(1, p, z), (0, 1)
        seen_zero = False
        delta_width = 1 + (iterations(256) + 1).bit_length()
        for j in range(iterations(256)):
            if v.g == 0:
                if not seen_zero:
                    max_first_zero = max(max_first_zero, j)
                seen_zero = True
                coverage["padded_rounds"] += 1
            coverage["negative_g"] += int(v.g < 0)
            coverage["delta_zero"] += int(v.delta == 0)
            record = decisions(v)
            coverage["branch_" + "".join(map(str, record))] += 1
            m = matrix(record)
            numerator = tuple(row[0] * v.f + row[1] * v.g for row in m)
            assert all(x % 2 == 0 for x in numerator)
            assert all(-(1 << 257) < x < (1 << 257) for x in numerator)
            new, saved = forward(v)
            assert (new.f, new.g) == tuple(x // 2 for x in numerator)
            assert all(-(1 << 256) < x < (1 << 256) for x in (new.f, new.g))
            assert -(1 << (delta_width - 1)) <= new.delta < (1 << (delta_width - 1))
            assert inverse_and_clear(new, saved) == (v, (0, 0))
            new_pair = coefficient_forward(pair, record, p)
            assert coefficient_inverse(new_pair, record, p) == pair
            assert new.f % p == new_pair[0] * z % p
            assert new.g % p == new_pair[1] * z % p
            v, pair = new, new_pair
            max_abs_delta = max(max_abs_delta, abs(v.delta))
            counts["checked_trajectory_rounds"] += 1
        assert v.g == 0 and abs(v.f) == 1 and pair[1] == 0
        assert v.f * pair[0] % p == pow(z, -1, p)
        for c in (0, 1, p - 1, rng.randrange(p)):
            corpus.update(c.to_bytes(32, "big"))
            check_payload(p, z, c)
            counts["secp_payloads"] += 1
        counts["secp_denominators"] += 1

    # The stated interface excludes zero denominator; do not silently divide it.
    try:
        payload_map(p, 0, 1)
    except AssertionError:
        pass
    else:
        raise AssertionError("zero denominator accepted")
    assert all(coverage.values())
    result = {"status": "PASS", "scope": "scalar only, no measured gate cost",
              "seed": 20260922, "rounds": iterations(256), "counts": counts,
              "coverage": coverage, "small_primes": primes,
              "max_abs_delta_observed": max_abs_delta,
              "max_first_zero_round_observed": max_first_zero,
              "corpus_sha256": corpus.hexdigest(),
              "elapsed_seconds": round(time.monotonic() - start, 3)}
    result["source_sha256"] = {name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
                               for name in ("scalar.py", "verify.py")}
    Path(__file__).with_name("scalar-results.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
