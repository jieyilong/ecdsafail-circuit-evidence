#!/usr/bin/env python3
"""Verify additive mechanism records without rerunning circuits or editing data."""
import json
import subprocess
import sys

from common import ROOT, ensure_checks_enabled, read_json, safe_path, sha


def verify_preserved_v1_science():
    previous = read_json(ROOT / "provenance/v1.0.0-publication-manifest.json")["files"]
    preserved = {name: digest for name, digest in previous.items()
                 if name.startswith(("experiments/", "sources/", "provenance/"))
                 and name != "provenance/publication-manifest.json"}
    for name, digest in preserved.items():
        assert sha(safe_path(ROOT, name)) == digest, name
    return len(preserved)


def run_json(path, *args):
    result = subprocess.run([sys.executable, "-B", str(path), *args], cwd=path.parent,
                            text=True, capture_output=True, check=True)
    return json.loads(result.stdout)


def verify_mechanism():
    ensure_checks_enabled()
    if sys.version_info < (3, 11):
        raise RuntimeError("The v1.1 mechanism packages require Python 3.11 or later.")
    preserved = verify_preserved_v1_science()
    reports = {}
    for name in ("06-resource-accounting", "07-boundary-diagnosis"):
        result = run_json(ROOT / "experiments" / name / "verify.py")
        if result.get("status") != "PASS" and result.get("successful") is not True:
            raise RuntimeError(f"Mechanism verification did not pass: {name}")
        reports[name] = result
    algebra = run_json(ROOT / "supporting/algebra/check_value_replay.py")
    assert algebra == read_json(ROOT / "supporting/algebra/value-replay-checks.json")
    replay = run_json(ROOT / "supporting/replay-analysis/scripts/check_replay_algebra.py", "--check")
    math = run_json(ROOT / "supporting/comparison/check_accounting.py", "--math-only")
    original = read_json(ROOT / "supporting/comparison/audit_checks.json")
    for key in ("small_exact_enumeration_cases", "scalar", "window_allowance", "zero_failure_math"):
        assert math[key] == original[key], key
    return dict(status="PASS", preserved_v1_scientific_files=preserved,
                algebra_cases=algebra["denominator_payload_cases"],
                accounting_math_checks=math["small_exact_enumeration_cases"],
                replay_algebra_cases=replay["guarded_fusion_cases"],
                experiments=reports,
                scope="Offline record/source verification and scalar arithmetic, not new circuit execution or a general repair")


if __name__ == "__main__":
    print(json.dumps(verify_mechanism(), indent=2))
