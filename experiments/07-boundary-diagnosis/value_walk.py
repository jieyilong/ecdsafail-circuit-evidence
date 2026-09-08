#!/usr/bin/env python3
"""Exact-integer schedule precheck only, not a substitute for gate simulation."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
P = 2**256 - 2**32 - 977


def width(k):
    if k < 40:
        w = 276 - 17 * k // 100
    elif k < 304:
        w = 270 - 33 * (k - 40) // 100
    else:
        w = 183 - 40 * (k - 304) // 100
    return min(259, max(8, w))


def check(d):
    u, v = P, d
    first_bad = None
    convergence = None
    tape = []
    for k in range(736):
        w = width(k)
        fits = lambda x: -(1 << (w - 1)) <= x < (1 << (w - 1))
        if not fits(u) or not fits(v):
            first_bad = first_bad or {"round": k, "kind": "input_width", "width": w, "u": str(u), "v": str(v)}
        if k == 0:
            a0, a1 = d & 1, (d >> 1) & 1
            v = d // 2 - P + a1 * P + a0 * ((P + 1) // 2)
            tape.append(a0)
        else:
            source, target = (u, v) if k % 2 == 0 else (v, u)
            sign = ((source >> 1) ^ (target >> 1)) & 1
            total = target + (-source if sign else source)
            assert total % 2 == 0
            if not fits(total):
                first_bad = first_bad or {"round": k, "kind": "pre_halving_sum", "width": w, "sum": str(total)}
            if k % 2 == 0:
                v = total // 2
            else:
                u = total // 2
            tape.append(sign)
        if max(abs(u), abs(v)) == 1 and convergence is None:
            convergence = k + 1
    return {"denominator": hex(d), "convergence": convergence, "first_bad": first_bad,
            "terminal_u": u, "terminal_v": v, "first_8_tape_bits": tape[:8]}


def main():
    fixtures = json.loads((ROOT / "source/selection.json").read_text())["selected"]
    checked = [check(int(r["denominator"], 16)) for r in fixtures]
    assert all(r["first_bad"] is None and r["convergence"] is not None for r in checked)
    assert [r["convergence"] for r in checked] == [r["rounds"] for r in fixtures]
    small = [check(d) for d in range(1, 257)] + [check(P - 1)]
    result = {"scope": "Exact signed value schedule only, including pre-halving sums.",
              "fixtures": checked, "small_integer_and_p_minus_one_prechecks": small}
    (ROOT / "value-walk.json").write_text(json.dumps(result, indent=2) + "\n")
    print("Fixture prechecks:", len(checked), "passed; max convergence", max(r["convergence"] for r in checked))
    valid = [r for r in small if r["first_bad"] is None and r["convergence"]]
    print("Valid small denominators:", len(valid), "first:", valid[:2])
    print("d=1:", small[0])


if __name__ == "__main__":
    main()
