"""Bounded development runs; fresh final runs are added only after artifact freeze."""
import argparse
import csv
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "experiments/windowed_pingpong"))
from run_cases import clean_environment, run_logged

DEV_SEED = "ecdsafail-qip-bounded-development-20260908-v1"
PROFILES = ("base", "rounds", "widths", "guarded")


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def summary(case):
    checkpoint = case / "checkpoint"
    manifest = dict(line.split("\t", 1) for line in (checkpoint / "manifest.tsv").read_text().splitlines())
    with (checkpoint / "batches.tsv").open() as f:
        batches = list(csv.DictReader(f, delimiter="\t"))
    with (checkpoint / "inputs.tsv").open() as f:
        rows = list(csv.DictReader(f, delimiter="\t"))
    n = int(manifest["target_shots"])
    assert len(rows) == len({r["index"] for r in rows}) == n
    assert sum(int(b["shots"]) for b in batches) == n
    flags = ("classical_failure", "phase_failure", "ancilla_failure", "any_failure")
    for row in rows:
        assert int(row["any_failure"]) == int(any(int(row[k]) for k in flags[:3]))
    counts = {k: sum(int(r[k]) for r in rows) for k in flags}
    identity = [r for r in rows if int(r["address"]) == 0]
    q = int(manifest["qubits"])
    t = Decimal(sum(int(b["toffoli"]) for b in batches)) / n
    result = dict(n=n, Q=q, mean_T=str(t), QT=str(q*t),
                  mean_Clifford=str(Decimal(sum(int(b["clifford"]) for b in batches))/n),
                  **counts, identity_rows=len(identity), identity_failures=sum(int(r["any_failure"]) for r in identity),
                  nonidentity_failures=counts["any_failure"]-sum(int(r["any_failure"]) for r in identity),
                  ops_fingerprint=manifest["ops_fingerprint"], manifest=manifest)
    (case / "summary.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k:v for k,v in result.items() if k != "manifest"}), flush=True)
    return result


def run_case(out, profile, tests, threads, seed=DEV_SEED, windowed=False, beta="1", tag=None, reuse=None, coordinate_bits=None):
    assert tests > 0 and 2 <= threads <= 8, "checkpointed research runs require positive tests and 2..8 requested workers"
    case = out / (tag or profile)
    case.mkdir(parents=True, exist_ok=True)
    env = clean_environment()
    for k in list(env):
        if k.startswith(("QIP_", "KAL_", "ROUND84_", "SQUARE_")):
            del env[k]
    env.update(QIP_PINGPONG_PROFILE=profile, QIP_TABLE_BETA=beta,
               EVAL_SHARED_SEED=seed, EVAL_THREADS=str(threads),
               EVAL_CHECKPOINT_DIR=str(case / "checkpoint"), SINGLE_CCX_FANOUT_DISABLE="1")
    if coordinate_bits is not None:
        assert 19 <= coordinate_bits <= 64
        env["TLM_MSBS"] = str(coordinate_bits)
    if windowed:
        env.update(WINDOWED_MODE="1", WINDOW_BITS="16", WINDOWED_QROM_UNLOAD="split",
                   WINDOWED_TESTS=str(tests), WINDOWED_SEQUENCE_CALLS="1", WINDOWED_MAX_ERROR_RATE="1")
    else:
        env.update(MIXED_WINDOW_BITS="16", EVAL_TESTS=str(tests), EVAL_MAX_ERROR_RATE="1")
    config = {k:v for k,v in env.items() if k.startswith(("QIP_", "EVAL_", "WINDOW", "MIXED_", "SINGLE_CCX_", "TLM_"))}
    config["source_base"] = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip()
    config["builder_sha256"] = sha(REPO / "target/release/build_circuit")
    config["evaluator_sha256"] = sha(REPO / "target/release/eval_bounded")
    config_path = case / "configuration.json"
    if config_path.exists():
        assert json.loads(config_path.read_text()) == config, "configuration changed: choose a new case directory"
    else:
        config_path.write_text(json.dumps(config, indent=2, sort_keys=True) + "\n")
    if reuse:
        if not (case / "ops.bin").exists():
            (case / "ops.bin").symlink_to(reuse.resolve())
    elif not (case / "ops.bin").exists():
        run_logged([str(REPO / "target/release/build_circuit")], case, env, case / "build.log")
    elapsed = run_logged([str(REPO / "target/release/eval_bounded"), "--note", tag or profile], case, env, case / "eval.log")
    (case / "timing.json").write_text(json.dumps({"evaluation_seconds":elapsed}) + "\n")
    return summary(case)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("task", choices=["development", "case", "summary"])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--profile", choices=PROFILES, default="base")
    parser.add_argument("--tests", type=int, default=16384)
    parser.add_argument("--threads", type=int, default=8)
    parser.add_argument("--seed", default=DEV_SEED)
    parser.add_argument("--windowed", action="store_true")
    parser.add_argument("--beta", default="1")
    parser.add_argument("--tag")
    parser.add_argument("--reuse", type=Path)
    parser.add_argument("--coordinate-bits", type=int)
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    if args.task == "development":
        results = {}
        for profile in PROFILES:
            results[profile] = run_case(out, profile, args.tests, args.threads, args.seed)
            (out / "development-summary.json").write_text(json.dumps(results, indent=2) + "\n")
    elif args.task == "case":
        run_case(out, args.profile, args.tests, args.threads, args.seed, args.windowed, args.beta, args.tag, args.reuse, args.coordinate_bits)
    else:
        summary(out)
