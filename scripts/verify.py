#!/usr/bin/env python3
"""Verify original bytes, reconstructed outcomes, readable summaries, and sources."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import time

from common import ROOT, FRESH, FREEZE_SHA256, atomic_write, ensure_checks_enabled, legacy_layout, read_json, safe_path, sha, verify_original, verify_sources, work_path
from verify_mechanism import verify_mechanism
from verify_followup import verify_followup
from verify_reference import verify_reference


def publication_check():
    path = ROOT / "provenance/publication-manifest.json"
    if not path.exists():
        raise RuntimeError("Missing publication manifest. This is not a complete published checkout.")
    for name, digest in read_json(path)["files"].items():
        assert sha(safe_path(ROOT, name)) == digest, name


def verify(oracle=False):
    ensure_checks_enabled()
    started = time.monotonic()
    publication_check()
    count = verify_original()
    trees = verify_sources()
    print(f"Original bundle: {count} files match byte for byte. Source trees: {trees} verified.", flush=True)
    with legacy_layout() as legacy:
        command = [sys.executable, str(legacy/"package_evidence.py"), "verify", str(legacy)]
        if oracle:
            command.append("--oracle")
        subprocess.run(command, check=True)
    subprocess.run([sys.executable, str(ROOT/"scripts/results.py"), "--check"], check=True)
    mechanisms = verify_mechanism()
    followup = verify_followup()
    reference = verify_reference()
    report = read_json(FRESH/"analysis.json")
    receipt = dict(verified_utc=datetime.now(timezone.utc).isoformat(), elapsed_seconds=round(time.monotonic()-started, 3), freeze_sha256=FREEZE_SHA256,
                   original_files=count, source_trees=trees, final_outcomes=300000, development_outcomes=5*16384,
                   evaluator_equivalence_cases=8192, independent_oracle_rerun=oracle,
                   any_channel_failures={k:v["any_failure"] for k,v in report["circuits"].items()},
                   mechanism_studies=mechanisms,
                   followup_diagnostics=followup,
                   canonical_reference=reference,
                   scope="Evidence reconstruction and optional classical-reference check, not new circuit simulation or all-input correctness")
    print(json.dumps(receipt, indent=2))
    return receipt


if __name__ == "__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--oracle", action="store_true", help="Repeat OpenSSL reference construction (requires cryptography; several minutes)")
    p.add_argument("--output", type=Path, help="Optional receipt, restricted to .work/")
    args=p.parse_args()
    if args.output:
        try:
            args.output=work_path(args.output)
        except ValueError as exc:
            p.error(str(exc))
    result=verify(args.oracle)
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        atomic_write(work_path(args.output),json.dumps(result,indent=2)+"\n")
