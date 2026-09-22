"""Bounded audit. All generated files and compiler temporaries stay beside this script."""
import collections
import csv
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import platform
import subprocess
import sys
import time

sys.dont_write_bytecode = True
from model import BUDGETS, P, magnitude_walk, small_pair_check, walk, width

ROOT = Path(__file__).resolve().parent
WORKSPACE = ROOT.parents[2]
EVIDENCE = WORKSPACE / "ecdsafail-circuit-evidence/experiments/08-followup-diagnostics"
SOURCE = WORKSPACE / "ecdsafail-qip-bounded-validation/src/point_add/pingpong_div.rs"
FRESH_SEED = b"qip-oral-schedule-independent-20260922-v1"
OLD_SEED = b"qip-pingpong-round-tail-20260908-v1"
N = 10000


def dump(name, value):
    (ROOT / name).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_reference():
    spec = importlib.util.spec_from_file_location("frozen_replay_model", EVIDENCE / "replay_model.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sample(seed, n):
    values, block, rejected = [], 0, 0
    while len(values) < n:
        raw = hashlib.shake_256(seed + block.to_bytes(8, "little")).digest(32000)
        block += 1
        for offset in range(0, len(raw), 32):
            d = int.from_bytes(raw[offset:offset + 32], "big")
            if 0 < d < P:
                values.append(d)
                if len(values) == n:
                    break
            else:
                rejected += 1
    return values, rejected


def run_command(args, env, timeout=120):
    result = subprocess.run(args, cwd=ROOT, env=env, capture_output=True, text=True, timeout=timeout)
    if result.returncode:
        raise RuntimeError(f"{args}: {result.returncode}\n{result.stdout}\n{result.stderr}")
    return result.stdout


def native(values, name, env, binary="round_tail"):
    data = b"".join(d.to_bytes(32, "big") for d in values)
    path = ROOT / (name + ".bin")
    path.write_bytes(data)
    result = json.loads(run_command([str(ROOT / binary), str(path), str(len(values))], env))
    result["denominators_sha256"] = hashlib.sha256(data).hexdigest()
    return result


def source_schedules(env):
    text = SOURCE.read_text()
    # Extract verbatim delimited Rust declarations, not a translated schedule.
    profile = text[text.index("#[derive(Clone, Copy, Debug)]"):text.index("/// Translate the source model")]
    function = text[text.index("fn value_width("):text.index("fn fused_lift_round0_enabled()")]
    main = '''
fn main() {
    let p = bounded_profile();
    println!("{},{},{},{},{},{}", p.rounds, p.margin, p.chunk_compare,
             p.replay_fold, p.endpoint_fold, p.flag_compare);
    for k in 0..800 { println!("{},{}", k, value_width(k)); }
}
'''
    path = ROOT / "extracted_schedule.rs"
    path.write_text("const N: usize = 256;\nconst VALUE_WIDTH: usize = N + 3;\n" + profile + function + main)
    run_command(["rustc", "--edition=2021", str(path), "-o", str(ROOT / "extracted_schedule")], env)
    profiles = {}
    for name in ("base", "rounds", "widths", "guarded"):
        lines = run_command([str(ROOT / "extracted_schedule")], {**env, "QIP_PINGPONG_PROFILE": name}).splitlines()
        fields = ("rounds", "margin", "chunk_compare", "replay_fold", "endpoint_fold", "flag_compare")
        profiles[name] = dict(zip(fields, map(int, lines[0].split(","))))
        for row in lines[1:]:
            k, w = map(int, row.split(","))
            assert w == width(k, profiles[name]["margin"])
    assert profiles["guarded"] == dict(rounds=736, margin=20, chunk_compare=40,
                                       replay_fold=72, endpoint_fold=71, flag_compare=48)
    with (ROOT / "width_schedule.csv").open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["k_zero_based", "round_one_based", "base704", "rounds736",
                         "widths_guarded736", "proposed_taper768", "proposed_full259_768",
                         "proved_sufficient_ordinary_width258"])
        for k in range(768):
            writer.writerow([k, k + 1, width(k, 4) if k < 704 else "",
                             width(k, 4) if k < 736 else "", width(k, 20) if k < 736 else "",
                             width(k, 20), 259, 258])
    return {"existing_profiles": profiles, "rust_rows_compared": 3200,
            "candidate768": "NOT an existing bounded_profile option",
            "candidate_settings_if_extended": {**profiles["guarded"], "rounds": 768},
            "extracted_rust_sha256": sha(path),
            "source_selfcheck_warning": "margin20 selfcheck expects terminal width11; proposed768 ends at8"}


def frozen_audit():
    manifest = json.loads((EVIDENCE / "manifest.json").read_text())
    checked = {}
    for name in ("round_tail.c", "run_tail.py", "replay_model.py", "test_diagnostics.py",
                 "tail-10000.json", "tail-10000000.json"):
        digest = sha(EVIDENCE / name)
        assert digest == manifest[name], name
        checked[name] = digest
    record = json.loads((EVIDENCE / "tail-10000000.json").read_text())
    hist = {int(k): v for k, v in record["histogram"].items()}
    assert sum(hist.values()) == record["n"] == 10**7
    assert sum(k * v for k, v in hist.items()) == record["round_sum_censored"] == 6215332390
    assert record["censored_at_801"] == 0 and max(hist) == 743
    for b in BUDGETS:
        assert sum(v for k, v in hist.items() if k > b) == record["tail_counts"][str(b)]
    assert record["mean_rounds"] == record["round_sum_censored"] / record["n"]
    return {"status": "REUSED frozen summary, not a new ten-million execution",
            "verified_manifest_entries": checked, "manifest_sha256": sha(EVIDENCE / "manifest.json"),
            "n": record["n"], "mean_rounds": record["mean_rounds"], "max_rounds": max(hist),
            "tail_counts": record["tail_counts"], "old_denominators_sha256": record["denominators_sha256"],
            "old_data_hash_recomputed": False, "width_misses_704_margin4": 661,
            "width_misses_736_margin20": 0, "width_misses_768_margin20": None,
            "zero_event_one_sided95": -math.expm1(math.log(0.05) / record["n"]),
            "assumption": "pointwise binomial bound under independent uniform draws; fixed SHAKE seed is deterministic",
            "selection_caveat": "768 was assessed post hoc; not a pre-registered global or selected-threshold guarantee"}


def fresh_audit(values):
    hist = collections.Counter()
    counts = collections.Counter()
    first_witness = {}
    reference = load_reference()
    for i, d in enumerate(values):
        result = walk(d)
        count = result["first_terminal_round"]
        hist[str(count or 801)] += 1
        for name, miss in result["misses"].items():
            counts[name] += miss is not None
            if miss is not None and name not in first_witness:
                first_witness[name] = {"sample_index": i, "d": hex(d), **miss}
        # A small independent-formulation crosscheck, not a second population sample.
        if i < 128:
            assert magnitude_walk(d, 800) == count
            ref = reference.walk(d, 800, 20)
            assert ref[4] == count
            ref768 = reference.walk(d, 768, 20)
            miss = result["misses"]["candidate768"]
            assert (None if miss is None else (miss["k"], miss["kind"])) == ref768[3]
    n = len(values)
    return {"n": n, "seed": FRESH_SEED.decode(), "max_uncensored_rounds": max(int(k) for k in hist if k != "801"),
            "censored_at_801": hist.get("801", 0), "round_sum_censored": sum(int(k) * v for k, v in hist.items()),
            "histogram": dict(hist), "width_misses": dict(counts), "first_width_witnesses": first_witness,
            "tail_counts": {str(b): sum(v for k, v in hist.items() if int(k) > b) for b in BUDGETS},
            "zero_event_one_sided95": -math.expm1(math.log(0.05) / n),
            "scope": "exact integers, proposed768 signed taper and full-width inequalities; no circuit execution",
            "reference_and_magnitude_crosschecks": 128}


def structured_audit(env):
    ds = list(range(1, 33)) + [P - 1, P - 2, P // 2, 2**255]
    ref = load_reference()
    results = []
    for d in ds:
        result = walk(d, 4096, trace=d in (1, 3, 2**255))
        assert result["first_terminal_round"] == magnitude_walk(d, 4096)
        reference = ref.walk(d, 4096, 20)
        assert result["first_terminal_round"] == reference[4]
        for limit, name, margin in ((704, "base704", 4), (736, "guarded736", 20), (768, "candidate768", 20)):
            check = ref.walk(d, limit, margin)
            miss = result["misses"][name]
            assert (None if miss is None else (miss["k"], miss["kind"])) == check[3]
        if result["trace"]:
            label = "2pow255" if d == 2**255 else str(d)
            with (ROOT / f"trace-d{label}.csv").open("w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=result["trace"][0])
                writer.writeheader()
                writer.writerows(result["trace"])
            row768 = result["trace"][767] if len(result["trace"]) >= 768 else None
        else:
            row768 = None
        result.pop("trace")
        results.append({"d": hex(d), "state_after768": row768, **result})
    native_result = native(ds, "structured", env)
    expected = collections.Counter(str(r["first_terminal_round"] if r["first_terminal_round"] <= 800 else 801) for r in results)
    assert native_result["histogram"] == expected
    assert native_result["original_width_misses"] == sum(r["misses"]["base704"] is not None for r in results)
    assert native_result["conservative_width_misses"] == sum(r["misses"]["guarded736"] is not None for r in results)
    # Mechanical bound extension only; retain the frozen recurrence and width checks.
    original = (EVIDENCE / "round_tail.c").read_text()
    extended = original.replace("802", "4098").replace("801", "4097").replace("800", "4096")
    extended_path = ROOT / "round_tail_4096.c"
    extended_path.write_text(extended)
    run_command(["clang", "-O2", "-I/opt/homebrew/include", str(extended_path),
                 "-L/opt/homebrew/lib", "-lgmp", "-o", str(ROOT / "round_tail_4096")], env)
    native_long = native(ds, "structured", env, "round_tail_4096")
    assert native_long["histogram"] == collections.Counter(str(r["first_terminal_round"]) for r in results)
    assert native_long["censored_at_4097"] == 0
    assert results[2]["first_terminal_round"] == 1135
    assert results[-1]["first_terminal_round"] == 1239
    return {"selection": "structured adversarial regression, not random samples", "cases": results,
            "native_capped800": native_result, "native_capped4096": native_long,
            "native_extension": "only replace array bound802->4098, sentinel801->4097, loop bound800->4096",
            "native_extended_source_sha256": sha(extended_path), "all_models_agree": True}


def main():
    start = time.monotonic()
    temp = ROOT / "tmp"
    temp.mkdir(exist_ok=True)
    env = {**os.environ, "TMPDIR": str(temp), "PYTHONDONTWRITEBYTECODE": "1",
           "CLANG_MODULE_CACHE_PATH": str(temp / "clang-cache")}
    receipt = {"scope": str(ROOT), "python": sys.version, "platform": platform.platform(),
               "fresh_n_fixed_before_run": N, "no_circuit_emission": True, "no_ten_million_rerun": True}
    receipt["input_hashes_before"] = {str(SOURCE.relative_to(WORKSPACE)): sha(SOURCE)}
    frozen = frozen_audit()
    dump("frozen_audit.json", frozen)
    print("Frozen hashes and histogram verified.", flush=True)
    profiles = source_schedules(env)
    dump("profiles.json", profiles)
    run_command(["clang", "-O2", "-I/opt/homebrew/include", str(EVIDENCE / "round_tail.c"),
                 "-L/opt/homebrew/lib", "-lgmp", "-o", str(ROOT / "round_tail")], env)
    old_values, rejected = sample(OLD_SEED, N)
    pilot = native(old_values, "frozen-pilot", env)
    old_pilot = json.loads((EVIDENCE / "tail-10000.json").read_text())
    for key, value in pilot.items():
        assert old_pilot[key] == value, key
    dump("pilot_reproduction.json", {"status": "reproduced, a subset of frozen10m, not independent evidence",
                                      "rejected": rejected, **pilot})
    print("Frozen 10,000-input pilot exactly reproduced.", flush=True)
    values, rejected = sample(FRESH_SEED, N)
    native_result = native(values, "independent", env)
    fresh = fresh_audit(values)
    for key in ("histogram", "round_sum_censored", "censored_at_801"):
        assert fresh[key] == native_result[key], key
    assert fresh["width_misses"]["base704"] == native_result["original_width_misses"]
    assert fresh["width_misses"]["guarded736"] == native_result["conservative_width_misses"]
    fresh.update(denominators_sha256=native_result["denominators_sha256"], rejected=rejected,
                 gmp_crosscheck_all_10000=True)
    dump("independent_sample.json", fresh)
    print("Independent 10,000-input exact Python/GMP crosscheck passed.", flush=True)
    dump("structured_witnesses.json", structured_audit(env))
    dump("small_exhaustive.json", small_pair_check())
    receipt["input_hashes_after"] = {str(SOURCE.relative_to(WORKSPACE)): sha(SOURCE)}
    assert receipt["input_hashes_before"] == receipt["input_hashes_after"]
    assert frozen_audit() == frozen
    receipt["elapsed_seconds"] = time.monotonic() - start
    receipt["clang"] = run_command(["clang", "--version"], env).splitlines()[0]
    receipt["rustc"] = run_command(["rustc", "--version"], env).strip()
    receipt["audit_code_hashes"] = {name: sha(ROOT / name) for name in ("audit.py", "model.py", "test_audit.py")}
    dump("run_receipt.json", receipt)
    print(json.dumps({"seconds": receipt["elapsed_seconds"], "tails": fresh["tail_counts"],
                      "width_misses": fresh["width_misses"]}, indent=2))


if __name__ == "__main__":
    main()
