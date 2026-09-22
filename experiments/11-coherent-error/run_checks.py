"""Run checks and write evidence only beside this script, inside coherence/."""

import csv
import hashlib
import json
from pathlib import Path
import platform
import sys

import numpy as np

import matrix_checks
import prefix_support


ROOT = Path(__file__).resolve().parent
WORKSPACE = ROOT.parents[2]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def current_evidence_paths():
    paths = ["research/qip-oral-20260922/schedule/structured_witnesses.json",
             "research/qip-oral-20260922/fresh-zero-mask-100k/freeze.json",
             "research/qip-oral-20260922/fresh-zero-mask-100k/plan.json"]
    for width in [4, 16]:
        for fixture in ["zero-slope", "smoke"]:
            prefix = f"research/qip-oral-20260922/repair-results/masked_chunk_coords-w{width}/{fixture}"
            paths.extend([prefix + ".stdout", prefix + ".json"])
    return paths


def check_current_evidence():
    result = {"targeted_repairs": []}
    for width in [4, 16]:
        for fixture in ["zero-slope", "smoke"]:
            base = WORKSPACE / f"research/qip-oral-20260922/repair-results/masked_chunk_coords-w{width}"
            with (base / f"{fixture}.stdout").open() as stream:
                rows = list(csv.DictReader(stream, delimiter="\t"))
            receipt = json.loads((base / f"{fixture}.json").read_text())
            assert receipt["exit_code"] == 0
            assert receipt["environment"]["QIP_PINGPONG_PROFILE"] == "guarded768"
            for flag in ["QIP_ZERO_PAYLOAD_MASK", "QIP_EXACT_CHUNK_CARRY", "QIP_CANONICAL_COORDS"]:
                assert receipt["environment"][flag] == "1"
            assert len(rows) == 64 and len({row["label"] for row in rows}) == 64
            assert all(row["interface_ok"] == "true" for row in rows)
            assert all(int(row[column]) == 0 for row in rows for column in ["classical", "phase", "ancilla"])
            if fixture == "zero-slope":
                assert sum(row["label"].startswith("zero-1-") for row in rows) == 32
                assert sum(row["label"].startswith("zero-2-") for row in rows) == 32
            result["targeted_repairs"].append({"width": width, "fixture": fixture,
                                              "records": len(rows), "flags": [0, 0, 0],
                                              "interfaces_valid": True})
    witness_path = WORKSPACE / "research/qip-oral-20260922/schedule/structured_witnesses.json"
    witnesses = json.loads(witness_path.read_text())
    assert witnesses["all_models_agree"]
    cases = {int(case["d"], 16): case for case in witnesses["cases"]}
    assert cases[3]["first_terminal_round"] == 1135
    assert cases[2**255]["first_terminal_round"] == 1239
    width_miss = cases[1]["misses"]["candidate768"]
    assert cases[1]["first_terminal_round"] == 512
    assert (width_miss["kind"], width_miss["k"], width_miss["width"]) == ("sum_width", 177, 225)
    result["schedule_audit_records"] = {
        "d3_terminal_round": 1135, "d2pow255_terminal_round": 1239,
        "d1_terminal_round": 512, "d1_width_miss_round_index": 177,
        "d1_width_miss_width": 225,
        "scope": "Checks the schedule agent's retained records; does not rerun its recurrence models.",
    }
    plan_path = WORKSPACE / "research/qip-oral-20260922/fresh-zero-mask-100k/plan.json"
    plan = json.loads(plan_path.read_text())
    assert len(plan["strata"]) == 9 and sum(row["n"] for row in plan["strata"]) == 100000
    verified = json.loads((WORKSPACE / "research/qip-oral-20260922/fresh-zero-mask-100k/verified-results.json").read_text())
    assert verified["counts"]["n"] == 100000
    result["frozen_study"] = {
        "planned_inputs": 100000, "planned_strata": 9,
        "status": "Completed; this check reads the independently reconciled summary, not a circuit rerun.",
        "reported_any_failures": verified["counts"]["any_failure"],
    }
    return result


def main():
    source_paths = [
        "ECDSAFAIL_PAPER_NOTATION.md",
        "outputs/ECDSAFAIL_QIP2027_eval_rewrite/sections/02-preliminaries.tex",
        "outputs/ECDSAFAIL_QIP2027_eval_rewrite/sections/05-window-selected-addition.tex",
        "outputs/ECDSAFAIL_QIP2027_eval_rewrite/sections/07-limitations.tex",
        "outputs/ECDSAFAIL_QIP2027_eval_rewrite/sections/12-technical-details.tex",
        "ecdsafail-circuit-evidence/sources/trees/original-pingpong/src/windowed_table.rs",
    ]
    # Private editorial context is not needed by the mathematical checks.
    context = "CRAIG_GIDNEY_FEEDBACK_ANALYSIS.md"
    if (WORKSPACE / context).is_file():
        source_paths.append(context)
    source_paths += current_evidence_paths()
    before = {name: digest(WORKSPACE / name) for name in source_paths}
    result = {
        "status": "PASS",
        "python_version": platform.python_version(),
        "python_executable": sys.executable,
        "numpy_version": np.__version__,
        "matrix_checks": matrix_checks.run(),
        "prefix_support": prefix_support.run(),
        "current_parent_evidence": check_current_evidence(),
        "input_sha256": before,
        "script_sha256": {name: digest(ROOT / name) for name in
                          ["matrix_checks.py", "prefix_support.py", "run_checks.py"]},
    }
    after = {name: digest(WORKSPACE / name) for name in source_paths}
    assert before == after, "An input file changed during the checks"
    result["inputs_unchanged_during_checks"] = True
    (ROOT / "check_results.json").write_text(json.dumps(result, indent=2) + "\n", encoding="ascii")
    compact = {
        "status": result["status"],
        "random_isometry_trials": result["matrix_checks"]["random_reference_entangled_isometries"]["trials"],
        "small_curve_pairs": result["prefix_support"]["small_curve_exhaustive"]["all_curve_pair_checks"],
        "secp_first_post_init_geometry": result["prefix_support"]["secp256k1_prefixes"]["rows"][0],
        "counterexamples": result["matrix_checks"]["counterexamples"],
        "current_parent_evidence": result["current_parent_evidence"],
        "result": str(ROOT / "check_results.json"),
    }
    print(json.dumps(compact, indent=2))


if __name__ == "__main__":
    main()
