"""Small-field full-circuit tests and explicit sparse coherent-state tests."""

import cmath
import json
import os
from pathlib import Path
import subprocess
import sys

from full import Full, ROOT


def coherent(p):
    c = Full(p)
    ops = [op for _, block in c.blocks() for op in block]
    def word(z, payload):
        return sum(((z >> j) & 1) << q for j, q in enumerate(c.z)) | sum(
            ((payload >> j) & 1) << q for j, q in enumerate(c.b))
    domain = [(z, x) for z in range(1, p) for x in range(p)]
    amplitudes = [cmath.exp(0.173j * (j*j + 3*j)) / len(domain)**0.5
                  for j in range(len(domain))]
    initial = {word(z, x): a for (z, x), a in zip(domain, amplitudes)}
    def run(state, gates):
        for op in gates:
            target = 1 << op[-1]
            controls = sum(1 << q for q in op[1:-1])
            state = {basis ^ target if basis & controls == controls else basis: amplitude
                     for basis, amplitude in state.items()}
        return state
    divided = run(initial, ops)
    expected = {word(z, pow(z, -1, p) * x % p): a for (z, x), a in zip(domain, amplitudes)}
    assert divided == expected
    assert run(divided, reversed(ops)) == initial
    multiplied = run(initial, reversed(ops))
    expected = {word(z, z * x % p): a for (z, x), a in zip(domain, amplitudes)}
    assert multiplied == expected
    assert run(multiplied, ops) == initial
    return {"p": p, "basis_amplitudes": len(domain), "status": "PASS",
            "scratch_zero_and_relative_phases_preserved": True}


def main():
    here = Path(__file__).resolve().parent
    binary = here.parent / "target/release/safegcd_round_verify"
    reports = []
    for p in (3, 5, 7, 11, 13, 17, 31, 61):
        out = here / ("full-p" + str(p))
        subprocess.run([sys.executable, "-B", str(here / "full.py"), "--prime", str(p),
                        "--output", str(out)], check=True, stdout=subprocess.DEVNULL)
        for mode in ("div", "mul"):
            env = dict(os.environ, VERIFY_SCOPE="complete_canonical_" + mode.upper())
            env.pop("VERIFY_REVERSE", None)
            if mode == "mul":
                env["VERIFY_REVERSE"] = "1"
            dest = out / (mode + "-results.json")
            subprocess.run([str(binary), str(out / "div.kmx"), str(out / (mode + "-vectors.txt")),
                            str(dest)], check=True, env=env, stdout=subprocess.DEVNULL)
            report = json.loads(dest.read_text())
            report["p"] = p
            reports.append(report)
        print("complete DIV/MUL exhaustive PASS p=" + str(p), flush=True)
    coherent_reports = [coherent(p) for p in (3, 5, 7, 11)]
    result = {"status": "PASS", "original_simulator_exhaustive": reports,
              "cases_each_direction": sum(r["forward_inverse_cases"] for r in reports[::2]),
              "sparse_coherent_tests": coherent_reports,
              "coherent_test_scope": "arbitrary relative phases on the entire valid small-field input subspace; all scratch wires included"}
    dest = ROOT / "research/qip-oral-20260922/safegcd/full-small-results.json"
    dest.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"status": result["status"], "cases_each_direction": result["cases_each_direction"],
                      "coherent_primes": [r["p"] for r in coherent_reports]}, indent=2))


if __name__ == "__main__":
    main()
