"""Check ideal value and field-replay identities, not emitted circuit correctness."""
import argparse
import json
from pathlib import Path


def check():
    cases = 0
    for p in (3, 5, 7, 11, 19, 31, 61, 127):
        for x in range(1, p):
            values = [p, x if x % 2 else x - p]
            initial = values[:]
            path = []
            target = 1
            while max(map(abs, values)) > 1:
                source = 1 - target
                s, t = values[source], values[target]
                e = ((s >> 1) ^ (t >> 1)) & 1
                values[target] = (t + (-1 if e else 1) * s) // 2
                assert values[target] % 2
                path.append((target, e))
                target = source
                assert len(path) <= 3 * p.bit_length() * (p.bit_length() + 1)
            signs = values[:]
            for y in sorted({0, 1, p - 1, x}):
                coeff = [0, y]
                for target, e in path:
                    coeff[target] = ((coeff[target] + (-1 if e else 1) * coeff[1 - target]) * pow(2, -1, p)) % p
                quotient = y * pow(x, -1, p) % p
                assert coeff == [s * quotient % p for s in signs]
                assert [s * c % p for s, c in zip(signs, coeff)] == [quotient, quotient]
                for target, e in reversed(path):
                    coeff[target] = (2 * coeff[target] - (-1 if e else 1) * coeff[1 - target]) % p
                assert coeff == [0, y]
                product = [s * y % p for s in signs]
                for target, e in reversed(path):
                    product[target] = (2 * product[target] - (-1 if e else 1) * product[1 - target]) % p
                assert product == [0, x * y % p]
                cases += 1
            for target, e in reversed(path):
                values[target] = 2 * values[target] - (-1 if e else 1) * values[1 - target]
            assert values == initial
    for s in (-1, 1):
        for t in (-1, 1):
            e = ((s >> 1) ^ (t >> 1)) & 1
            assert (t + (-1 if e else 1) * s) // 2 == t
            assert (s + (-1 if e else 1) * t) // 2 == s
    return {
        "scope": "Ideal exact signed integers and canonical field arithmetic only. No circuit gates, measurements, truncations, or large-input error probabilities are tested.",
        "primes": [3, 5, 7, 11, 19, 31, 61, 127],
        "denominator_payload_cases": cases,
        "terminal_signed_pairs": 4,
        "value_inverse": "pass",
        "division_and_multiplication_identities": "pass",
        "zero_payload_field_arithmetic": "pass; does not certify circuit encodings or phases",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    text = json.dumps(check(), indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text)
    print(text, end="")
