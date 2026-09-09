"""Validate complete stratified ledgers and report allocation-weighted statistics."""
import argparse
from collections import Counter
import csv
from decimal import Decimal
import hashlib
import json
import math
from pathlib import Path

META = ("index", "address", "target_x", "target_y", "addend_x", "addend_y", "expected_x", "expected_y")
FLAGS = ("classical_failure", "phase_failure", "ancilla_failure", "any_failure")
BATCH_FLAGS = ("classical_failures", "phase_failure_shots", "ancilla_failure_shots", "any_failure_shots")
Z = 1.959963984540054


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def tsv(path):
    with Path(path).open() as f:
        return list(csv.DictReader(f, delimiter="\t"))


def wilson(k, n):
    p = k / n
    den = 1 + Z*Z/n
    mid = (p + Z*Z/(2*n))/den
    half = Z*math.sqrt(p*(1-p)/n + Z*Z/(4*n*n))/den
    return [max(0, mid-half), min(1, mid+half)]


def cp_upper(k, n, alpha=0.05):
    if k == n:
        return 1.0
    if k == 0:
        return -math.expm1(math.log(alpha)/n)
    lo, hi = 0.0, 1.0
    for _ in range(70):
        p = (lo+hi)/2
        term = n*math.log1p(-p)
        total = term
        for j in range(1, k+1):
            term += math.log(n-j+1)-math.log(j)+math.log(p)-math.log1p(-p)
            a, b = max(total, term), min(total, term)
            total = a + math.log1p(math.exp(b-a))
        if math.exp(total) > alpha:
            lo = p
        else:
            hi = p
    return hi


def read_case(case, expected=None):
    root = Path(case) / "checkpoint"
    manifest = dict(line.split("\t", 1) for line in (root / "manifest.tsv").read_text().splitlines())
    n = int(manifest["target_shots"])
    assert n > 0
    raw = tsv(root / "inputs.tsv")
    rows = {int(r["index"]): r for r in raw}
    assert len(raw) == len(rows) == n and set(rows) == set(range(n))
    batches = tsv(root / "batches.tsv")
    assert len(batches) == len({int(b["batch"]) for b in batches}) == (n+63)//64
    assert {int(b["batch"]) for b in batches} == set(range((n+63)//64))
    for i, row in rows.items():
        assert int(row["batch"]) == i//64
        assert all(int(row[f]) in (0, 1) for f in FLAGS)
        assert int(row["any_failure"]) == int(any(int(row[f]) for f in FLAGS[:3]))
        mismatch = (int(row["got_x"], 16) != int(row["expected_x"], 16)
                    or int(row["got_y"], 16) != int(row["expected_y"], 16)
                    or int(row["got_address"], 16) != int(row["address"]))
        assert mismatch == bool(int(row["classical_failure"]))
    for b in batches:
        i = int(b["batch"])
        subset = [rows[j] for j in range(i*64, min(n, (i+1)*64))]
        assert int(b["shots"]) == len(subset)
        assert int(b["toffoli"]) >= 0 and int(b["clifford"]) >= 0
        for flag, total in zip(FLAGS, BATCH_FLAGS):
            assert sum(int(r[flag]) for r in subset) == int(b[total])
    if expected:
        for key, value in expected.items():
            assert str(manifest[key]) == str(value), (key, manifest[key], value)
    counts = {f: sum(int(r[f]) for r in rows.values()) for f in FLAGS}
    identity = [i for i, r in rows.items() if int(r["address"]) == 0]
    exceptions = [i for i, r in rows.items() if int(r["address"]) != 0 and (
        int(r["target_x"], 16) == int(r["addend_x"], 16)
        or int(r["expected_x"], 16) == int(r["addend_x"], 16))]
    total_t = sum(int(b["toffoli"]) for b in batches)
    total_c = sum(int(b["clifford"]) for b in batches)
    q = int(manifest["qubits"])
    stats = dict(n=n, Q=q, total_T=total_t, total_Clifford=total_c,
                 mean_T=str(Decimal(total_t)/n), QT=str(q*Decimal(total_t)/n),
                 **counts, failure_rate=counts["any_failure"]/n,
                 wilson95=wilson(counts["any_failure"], n),
                 exact_one_sided95_upper=cp_upper(counts["any_failure"], n),
                 identity_rows=len(identity), identity_failures=sum(int(rows[i]["any_failure"]) for i in identity),
                 extra_generic_exceptions=exceptions, address_failures=sum(int(r["got_address"],16)!=int(r["address"]) for r in rows.values()))
    return rows, manifest, stats


def paired(a, b):
    assert set(a) == set(b)
    counts = Counter((int(a[i]["any_failure"]), int(b[i]["any_failure"])) for i in a)
    return dict(n=len(a), both_fail=counts[1,1], baseline_only=counts[1,0], candidate_only=counts[0,1], neither_fail=counts[0,0])


def analyze(root):
    root = Path(root)
    freeze = json.loads((root / "freeze.json").read_text())
    spec = json.loads((root / "fresh-corpus-spec.json").read_text())
    assert spec["freeze_sha256"] == sha(root / "freeze.json")
    all_rows, results = {}, {}
    for name, candidate in freeze["candidates"].items():
        combined, strata = {}, {}
        for s in spec["strata"]:
            case = root / "results" / name / s["name"]
            rows, manifest, stats = read_case(case, dict(seed=s["seed"], target_shots=s["n"],
                qip_table_beta=hex(int(s["beta"], 16)), window_bits=16, qubits=candidate["Q"],
                ops=candidate["static_operations"], ops_fingerprint=candidate["ops_fingerprint"]))
            config = json.loads((case / "configuration.json").read_text())
            assert config["freeze_sha256"] == spec["freeze_sha256"]
            assert config["candidate"] == name and config["stratum"] == s
            assert config["ops_sha256"] == candidate["ops_sha256"]
            strata[s["name"]] = stats
            combined.update({(s["name"], i): row for i, row in rows.items()})
        n = sum(s["n"] for s in strata.values())
        assert n == 100000 == len(combined)
        q = candidate["Q"]
        tt = sum(s["total_T"] for s in strata.values())
        tc = sum(s["total_Clifford"] for s in strata.values())
        counts = {f: sum(s[f] for s in strata.values()) for f in FLAGS}
        f = counts["any_failure"]
        upper = sum(s["n"]*cp_upper(s["any_failure"], s["n"], 0.05/len(strata)) for s in strata.values())/n
        results[name] = dict(n=n, Q=q, mean_T=str(Decimal(tt)/n), mean_Clifford=str(Decimal(tc)/n),
            QT=str(q*Decimal(tt)/n), retry_proxy=str(q*Decimal(tt)/(n-f)), **counts,
            pass_fraction=str(Decimal(n-f)/n), stratified_one_sided95_upper=upper,
            zero_failure_pooled95_upper=(-math.expm1(math.log(0.05)/n) if f==0 else None),
            identity_rows=sum(s["identity_rows"] for s in strata.values()),
            identity_failures=sum(s["identity_failures"] for s in strata.values()),
            extra_generic_exceptions=sum(len(s["extra_generic_exceptions"]) for s in strata.values()),
            strata=strata, static_toffoli=candidate["static_toffoli"])
        all_rows[name] = combined
    ref = all_rows["pingpong_base"]
    for key in ref:
        values = tuple(ref[key][m] for m in META)
        for name, rows in all_rows.items():
            assert tuple(rows[key][m] for m in META) == values, (name, key)
    comparisons = {}
    for a,b in (("pingpong_base","pingpong_conservative"),("jump2","pingpong_conservative"),("jump2","pingpong_base")):
        comparisons[a+"_vs_"+b] = paired(all_rows[a],all_rows[b])
        comparisons[a+"_vs_"+b]["per_stratum"] = {
            s["name"]: paired({k:r for k,r in all_rows[a].items() if k[0]==s["name"]},
                              {k:r for k,r in all_rows[b].items() if k[0]==s["name"]}) for s in spec["strata"]}
    return dict(scope="Fresh frozen single-call stratified study, not full Shor or a coherent error bound",
                freeze_sha256=spec["freeze_sha256"], cases_per_circuit=100000, circuits=results,
                paired=comparisons, input_metadata_mismatches=0)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("root", type=Path)
    p.add_argument("--case", action="store_true")
    args = p.parse_args()
    if args.case:
        _, _, result = read_case(args.root)
    else:
        result = analyze(args.root)
        (args.root / "analysis.json").write_text(json.dumps(result, indent=2, sort_keys=True)+"\n")
    print(json.dumps(result, indent=2, sort_keys=True))
