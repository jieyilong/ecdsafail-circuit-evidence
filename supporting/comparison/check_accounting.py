"""Audit source accounting, or run standalone arithmetic with --math-only.

The default audit writes audit_checks.json beside this script. Math-only mode
prints JSON without reading workspace inputs or writing files. Either mode
accepts --output PATH. Only the Python standard library is required.
"""

import argparse
import hashlib
import json
from collections import Counter
from decimal import Decimal, getcontext
from fractions import Fraction
from pathlib import Path


HERE = Path(__file__).resolve().parent
getcontext().prec = 100


def decimal(value):
    return str(Decimal(value.numerator) / Decimal(value.denominator))


def rational(value):
    return {
        "numerator": str(value.numerator),
        "denominator": str(value.denominator),
        "decimal": decimal(value),
    }


def tv_formula(n, r):
    d = n - r
    assert 0 < d < r
    return Fraction(d * (r - d), n * r)


def check_small_cases():
    checked = 0
    for bits in range(2, 9):
        n = 2**bits
        for r in range(n // 2 + 1, n):
            counts = Counter(x % r for x in range(n))
            direct = sum(abs(Fraction(counts[a], n) - Fraction(1, r)) for a in range(r)) / 2
            assert direct == tv_formula(n, r)
            nonzero = sum(abs(Fraction(counts[a], n - 2) - Fraction(1, r - 1)) for a in range(1, r)) / 2
            assert nonzero == Fraction((n - r - 1) * (2 * r - n), (n - 2) * (r - 1))
            checked += 1
    return checked


def math_report():
    n = 2**256
    r = int("FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141", 16)
    d = n - r
    tv = tv_formula(n, r)
    w = 2**16
    # For fixed nonzero table base, the uniform proposal excludes a=0 and,
    # at each nonzero address, the two distinct scalars for R=+/-A.
    uniform_reject = Fraction(3 * w - 2, w * r)
    biased_reject_bound = Fraction(2 * (3 * w - 2), w * n)
    conditional_bound = 2 * tv / (1 - biased_reject_bound)
    return {
        "small_exact_enumeration_cases": check_small_cases(),
        "scalar": {
            "N": str(n), "r": str(r), "d": str(d), "d_hex": hex(d),
            "prefilter_tv": rational(tv),
            "log2_prefilter_tv": str((Decimal(tv.numerator) / Decimal(tv.denominator)).ln() / Decimal(2).ln()),
            "wrap_probability": rational(Fraction(d, n)),
            "nonidentity_only_tv": rational(Fraction((d - 1) * (r - d), (n - 2) * (r - 1))),
            "uniform_joint_rejection_probability": rational(uniform_reject),
            "biased_joint_rejection_upper_bound": rational(biased_reject_bound),
            "conditioned_tv_conservative_upper_bound": rational(conditional_bound),
            "prefilter_100000_trial_tv_upper_bound": rational(100000 * tv),
            "conditioned_100000_trial_tv_upper_bound": rational(100000 * conditional_bound),
        },
        "window_allowance": {
            "w": 16, "qubits": 16, "lookup_toffolis": 3 * 2**16,
            "google_low_q": {"Q_model_cap": 1175 + 16, "work_model_cap": 2700000 + 3 * 2**16},
            "google_low_gate": {"Q_model_cap": 1425 + 16, "work_model_cap": 2100000 + 3 * 2**16},
            "schrottenloher_low_q_work_from_rounded_log": str(Decimal(2) ** Decimal("21.19") + 3 * 2**16),
            "schrottenloher_low_gate_work_from_rounded_log": str(Decimal(2) ** Decimal("20.83") + 3 * 2**16),
            "warning": "Model allowances, not complete measured lookup/unlookup or full-Shor costs; source log counts are rounded",
        },
        "zero_failure_math": {
            "n10000_one_sided_95_upper": str(1 - Decimal("0.05") ** (Decimal(1) / 10000)),
            "n100000_one_sided_95_upper": str(1 - Decimal("0.05") ** (Decimal(1) / 100000)),
            "two_to_minus_13_3": str(Decimal(2) ** Decimal("-13.3")),
            "warning": "Illustrative independent-trial calculations, not confidence bounds assigned to selected external tests",
        },
    }


def audit_report(math):
    root = HERE.parents[2]
    sources = [
        "ECDSAFAIL_PAPER_NOTATION.md",
        "CRAIG_GIDNEY_FEEDBACK_ANALYSIS.md",
        "outputs/ECDSA_Fail_QIP2027_github_linked/sections/06a-resource-evaluation.tex",
        "outputs/ECDSA_Fail_QIP2027_github_linked/sections/06b-bounded-validation.tex",
        "outputs/ECDSA_Fail_QIP2027_github_linked/evidence/fresh-macros.tex",
        "research/technique_novelty/papers/2603.28846.pdf",
        "readings/Schrottenloher_EC_point_addition.pdf",
        "ecdsafail-circuit-evidence/experiments/02-fresh-windowed/analysis.json",
        "ecdsafail-circuit-evidence/experiments/02-fresh-windowed/corpus-spec.json",
        "ecdsafail-circuit-evidence/provenance/freeze.json",
        "ecdsafail-circuit-evidence/sources/trees/conservative-pingpong/src/bin/eval_bounded.rs",
        "trailmix-clean-analysis/README.md",
        "trailmix-clean-analysis/kmx_circuit_summaries.md",
    ]
    hashes = {p: hashlib.sha256((root / p).read_bytes()).hexdigest() for p in sources}
    fresh = json.loads((root / sources[7]).read_text())
    fresh_summary = {
        name: {key: row[key] for key in ("Q", "mean_T", "static_toffoli", "n", "any_failure", "identity_rows")}
        for name, row in fresh["circuits"].items()
    }
    return {
        "scope": "Exact scalar-distribution arithmetic and source-ledger checks only; no circuit execution or corpus rewriting",
        **math,
        "fresh_summary": fresh_summary,
        "source_sha256": hashes,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--math-only", action="store_true",
                        help="Run exact arithmetic and small checks without workspace inputs; print JSON")
    parser.add_argument("--output", type=Path,
                        help="Write JSON to PATH instead of the default audit file (math-only: no file by default)")
    args = parser.parse_args()
    math = math_report()
    if args.math_only:
        data = {
            "scope": "Standalone arithmetic and small exact checks only; no source files, hash verification, circuit execution, or corpus evaluation",
            **math,
        }
        text = json.dumps(data, indent=2) + "\n"
        if args.output is not None:
            args.output.write_text(text)
        print(text, end="")
        return

    data = audit_report(math)
    out = args.output if args.output is not None else HERE / "audit_checks.json"
    out.write_text(json.dumps(data, indent=2) + "\n")
    scalar = data["scalar"]
    print(json.dumps({"output": str(out), "toy_cases": data["small_exact_enumeration_cases"], "d": scalar["d"], "tv": scalar["prefilter_tv"]["decimal"], "conditional_bound": scalar["conditioned_tv_conservative_upper_bound"]["decimal"], "fresh": data["fresh_summary"]}, indent=2))


if __name__ == "__main__":
    main()
