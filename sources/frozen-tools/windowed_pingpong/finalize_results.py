#!/usr/bin/env python3
"""Package this experiment after the complete evaluation has exited successfully."""
import argparse
import json
from pathlib import Path
import shutil
import time

from analyze_results import analyze, sha256
from static_resources import NAMES


def finalize(workspace, wait):
    root = workspace / "outputs/ecdsafail-pingpong-windowed-100k-20260907"
    exp1 = workspace / "outputs/ecdsafail-pingpong-independent-100k-20260907"
    end = time.monotonic() + 7200
    while not (root / "windowed-pingpong/timing.json").exists():
        if not wait or time.monotonic() >= end:
            raise RuntimeError("Full evaluation has not completed successfully")
        time.sleep(30)
    cases = dict(
        mixed_pingpong=root / "mixed/checkpoint",
        windowed_pingpong=root / "windowed-pingpong/checkpoint",
        mixed_jump2=exp1 / "results/jump2",
        windowed_jump2=workspace / "experiments/8e9c9a2-windowed-paired-100k-v1/final",
    )
    release = Path(__file__).resolve().parent / "results"
    result = analyze(cases, export=release)
    result["static_resources"] = {
        "windowed_pingpong": json.loads((root / "windowed-pingpong/static_resources.json").read_text()),
        "windowed_jump2": json.loads((root / "windowed-jump2-static.json").read_text()),
    }
    older = json.loads((exp1 / "analysis.json").read_text())["circuits"]
    for name, key in (("mixed_pingpong", "pingpong"), ("mixed_jump2", "jump2")):
        d = older[key]
        counts = {NAMES[int(k)]: v for k, v in d["operation_kind_counts"].items()}
        result["static_resources"][name] = dict(
            ops_sha256=d["ops_sha256"], static_operations=d["static_operations"],
            static_toffoli=d["static_toffoli"], operation_kind_counts=counts,
            static_hmr=counts.get("Hmr", 0), static_reset=counts.get("R", 0),
            toffoli_depth=None, feed_forward_rounds=None,
        )
    for name, d in result["static_resources"].items():
        assert d["static_operations"] == result["circuits"][name]["static_operations"]
    diagnostics = __import__("csv").DictReader((exp1 / "results/pingpong/gcd_diagnostics.tsv").open(), delimiter="\t")
    from analyze_results import read_case
    window_rows, _, _ = read_case(cases["windowed_pingpong"])
    flagged, failed_flagged = [], []
    for row in diagnostics:
        flag = int(row["division_rounds"]) > 704 or int(row["multiplication_rounds"]) > 704 or bool(row["division_first_width_violation"]) or bool(row["multiplication_first_width_violation"])
        if flag:
            index = int(row["index"])
            flagged.append(index)
            if int(window_rows[index]["any_failure"]):
                failed_flagged.append(index)
    result["inherited_exact_recurrence_diagnostics"] = dict(
        flagged_indices=flagged, flagged_and_windowed_failure_indices=failed_flagged,
        note="Reuses Experiment 1's intended-denominator diagnostics, not first-divergent-gate tracing.",
    )
    original_hashes = {}
    for name, case in cases.items():
        original_hashes[name] = {f: sha256(case / f) for f in ("inputs.tsv", "batches.tsv", "manifest.tsv")}
    result["original_ledger_sha256"] = original_hashes
    serialized = json.dumps(result, indent=2, sort_keys=True) + "\n"
    for path in (root / "analysis.json", release / "analysis.json"):
        path.write_text(serialized)

    table = ["# Experiment 2 results", "", "All means use the complete shared 100,000-input corpus, including failed inputs.", "",
             "| Circuit | Q | Mean T | Static T | Mean counted Clifford | QT | Any failures | Pass fraction | QT / pass fraction |",
             "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for name, d in result["circuits"].items():
        table.append(f"| {name} | {d['qubits']:,} | {d['mean_toffoli']:,.5f} | {result['static_resources'][name]['static_toffoli']:,} | {d['mean_clifford']:,.5f} | {d['raw_qxt']:,.5f} | {d['any_failure']} | {d['pass_rate']:.5f} | {d['retry_adjusted_qxt']:,.5f} |")
    table.extend(["", "The retry-adjusted value is a per-call sensitivity proxy, not the cost or success probability of a coherent Shor computation.", ""])
    (release / "SUMMARY.md").write_text("\n".join(table))
    for tag in ("windowed-pingpong", "mixed"):
        dest = release / tag.replace("-", "_")
        dest.mkdir(exist_ok=True)
        for f in ("build.log", "eval.log", "timing.json", "configuration.json"):
            source = root / tag / f
            if source.exists():
                if f == "configuration.json":
                    config = json.loads(source.read_text())
                    config["EVAL_CHECKPOINT_DIR"] = "<experiment-output>/" + tag + "/checkpoint"
                    (dest / f).write_text(json.dumps(config, indent=2) + "\n")
                else:
                    # Only the local checkpoint path is redacted in released logs.
                    (dest / f).write_text(source.read_text().replace(str(workspace), "<paper-workspace>"))
    shutil.copy2(root / "logs/routing-checks.log", release / "routing-checks.log")
    for width in range(6):
        tag = f"pilot-w{width}-four-call"
        for f in ("build.log", "eval.log"):
            dest = release / "pilots" / tag
            dest.mkdir(parents=True, exist_ok=True)
            shutil.copy2(root / tag / f, dest / f)
    print("Complete four-circuit analysis and lossless release verified.")
    print("\n".join(table))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--workspace", type=Path, required=True)
    p.add_argument("--wait", action="store_true")
    args = p.parse_args()
    finalize(args.workspace.resolve(), args.wait)
