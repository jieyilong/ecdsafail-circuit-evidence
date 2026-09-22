"""Bounded runs of the private frozen-shell copy; never writes to a parent."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("emit", "count", "eval"))
    parser.add_argument("--baseline", action="store_true")
    parser.add_argument("--w", type=int, default=4)
    parser.add_argument("--samples", type=int, default=64)
    args = parser.parse_args()
    label = "canonical-pingpong" if args.baseline else "canonical-safegcd"
    out = ROOT / "safegcd_probe" / (label + "-w" + str(args.w))
    out.mkdir(exist_ok=True)
    env = {k: v for k, v in os.environ.items() if not k.startswith(
        ("QIP_", "TLM_", "SUB4_", "DIALOG_", "KAL_", "WINDOW", "EVAL_", "CONSTPROP_", "SINGLE_CCX_", "TRACE_"))}
    env.update(QIP_PINGPONG_PROFILE="guarded", TLM_MSBS="40", CONSTPROP_DISABLE="1",
               SINGLE_CCX_FANOUT_DISABLE="1", QIP_CANONICAL_REPLAY="1", QIP_CANONICAL_COORDS="1",
               WINDOWED_MODE="1", WINDOW_BITS=str(args.w), WINDOWED_QROM_UNLOAD="split")
    if not args.baseline:
        env["QIP_SAFEGCD_KMX"] = str(ROOT / "safegcd_probe/full-secp256k1/div.kmx")
    binary = ROOT / "target/matched/release" / ("eval_bounded" if args.mode == "eval" else "build_circuit")
    if args.mode == "count":
        env["QIP_COUNT_REFERENCE"] = "1"
    if args.mode == "eval":
        checkpoint = out / ("fresh-" + str(args.samples))
        assert not checkpoint.exists(), "fresh checkpoint already exists"
        env.update(WINDOWED_TESTS=str(args.samples), WINDOWED_MAX_ERROR_RATE="1",
                   EVAL_SHARED_SEED="qip-safegcd-matched-fresh-20260922-v1",
                   EVAL_THREADS="1", EVAL_CHECKPOINT_DIR=str(checkpoint))
    start = time.monotonic()
    with (out / (args.mode + ".log")).open("w") as log:
        result = subprocess.run([str(binary)], cwd=out, env=env, stdout=log,
                                stderr=subprocess.STDOUT, timeout=300)
    record = {"mode": args.mode, "label": label, "window_bits": args.w,
              "exit_code": result.returncode, "elapsed_seconds": time.monotonic() - start,
              "env": {k: v for k, v in env.items() if k.startswith(("QIP_", "TLM_", "WINDOW", "EVAL_", "CONSTPROP_", "SINGLE_CCX_"))},
              "binary_sha256": hashlib.sha256(binary.read_bytes()).hexdigest()}
    if args.mode == "emit" and result.returncode == 0:
        stats = subprocess.run([str(ROOT / "target/matched/release/stats_stream"), str(out / "ops.bin")],
                               check=True, capture_output=True, text=True, timeout=90)
        record["serialized_counts"] = json.loads(stats.stdout)
        h = hashlib.sha256()
        with (out / "ops.bin").open("rb") as stream:
            for data in iter(lambda: stream.read(1048576), b""):
                h.update(data)
        record["ops_sha256"] = h.hexdigest()
    (out / (args.mode + "-run.json")).write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps(record, indent=2))
    assert result.returncode == 0


if __name__ == "__main__":
    main()
