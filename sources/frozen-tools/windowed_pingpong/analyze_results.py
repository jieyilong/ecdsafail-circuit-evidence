#!/usr/bin/env python3
"""Analyze complete paired ledgers, or the losslessly factored release ledgers."""
import argparse
from collections import Counter
import csv
import gzip
import hashlib
import io
import json
import math
from pathlib import Path
import shutil

N = 100_000
Z = 1.959963984540054
META = ("index", "address", "target_x", "target_y", "addend_x", "addend_y", "expected_x", "expected_y")
FLAGS = ("classical_failure", "phase_failure", "ancilla_failure", "any_failure")
OUT = ("index", "got_x", "got_y", "got_address", *FLAGS)


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def tsv(path):
    op = gzip.open if path.suffix == ".gz" else open
    with op(path, "rt", newline="") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def write_gzip_tsv(path, fields, rows):
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", fileobj=raw, mode="wb", mtime=0) as compressed:
            with io.TextIOWrapper(compressed, encoding="ascii", newline="") as f:
                writer = csv.DictWriter(f, fields, delimiter="\t", lineterminator="\n", extrasaction="ignore")
                writer.writeheader()
                writer.writerows(rows)


def read_case(path, corpus=None):
    if (path / "inputs.tsv").exists():
        rows = tsv(path / "inputs.tsv")
    else:
        assert corpus is not None, "Factored outcomes require --corpus"
        rows = []
        for outcome in tsv(path / "outcomes.tsv.gz"):
            row = dict(corpus[int(outcome["index"])])
            row.update(outcome)
            for got, expected in (("got_x", "expected_x"), ("got_y", "expected_y"), ("got_address", "address")):
                if row[got] == "=":
                    row[got] = hex(int(row[expected])) if expected == "address" else row[expected]
            row["batch"] = str(int(row["index"]) // 64)
            rows.append(row)
    ledger = {int(row["index"]): row for row in rows}
    assert len(rows) == len(ledger) == N
    assert set(ledger) == set(range(N))
    manifest = dict(line.split("\t", 1) for line in (path / "manifest.tsv").read_text().splitlines())
    assert manifest["seed"] == "ecdsafail-windowed-independent-random-100k-v1"
    assert int(manifest["target_shots"]) == N and int(manifest["window_bits"]) == 16
    batches = tsv(path / "batches.tsv")
    assert len({int(b["batch"]) for b in batches}) == (N + 63) // 64
    assert sum(int(b["shots"]) for b in batches) == N
    for b in batches:
        index = int(b["batch"])
        subset = [ledger[i] for i in range(64 * index, min(64 * index + 64, N))]
        assert len(subset) == int(b["shots"])
        for flag, total in zip(FLAGS, ("classical_failures", "phase_failure_shots", "ancilla_failure_shots", "any_failure_shots")):
            assert sum(int(row[flag]) for row in subset) == int(b[total])
    for index, row in ledger.items():
        assert int(row["batch"]) == index // 64
        assert int(row["any_failure"]) == int(any(int(row[f]) for f in FLAGS[:3]))
        mismatch = row["expected_x"] != row["got_x"] or row["expected_y"] != row["got_y"] or int(row["got_address"], 16) != int(row["address"])
        assert mismatch == bool(int(row["classical_failure"]))
    return ledger, manifest, batches


def wilson(f, n):
    r = f / n
    den = 1 + Z * Z / n
    c = (r + Z * Z / (2 * n)) / den
    h = Z * math.sqrt(r * (1 - r) / n + Z * Z / (4 * n * n)) / den
    return [c - h, c + h]


def paired(a, b, indices):
    counts = Counter((int(a[i]["any_failure"]), int(b[i]["any_failure"])) for i in indices)
    a_only, b_only = counts[1, 0], counts[0, 1]
    n, discordant = len(indices), a_only + b_only
    diff = (b_only - a_only) / n
    h = Z * math.sqrt(max(0, discordant / n - diff * diff) / n)
    sign_p = min(1, 2 * sum(math.comb(discordant, k) for k in range(min(a_only, b_only) + 1)) / 2**discordant)
    result = dict(n=n, both_fail=counts[1, 1], baseline_only_fail=a_only, candidate_only_fail=b_only,
                neither_fail=counts[0, 0], candidate_minus_baseline_failure_rate=diff,
                paired_normal_95_interval=[diff - h, diff + h], exact_two_sided_sign_p=sign_p,
                exploratory_noninferiority_margin=0.0005,
                upper_95_below_margin=(diff + h <= 0.0005))
    if b_only == 0:
        # Delta = P(candidate-only failure) - P(baseline-only failure).
        # An exact upper bound on its first term also upper-bounds Delta.
        result["conservative_exact_one_sided_95_upper_on_regression"] = -math.expm1(math.log(0.05) / n)
    return result


def analyze(cases, corpus_path=None, export=None):
    corpus = {int(r["index"]): r for r in tsv(corpus_path)} if corpus_path else None
    ledgers, summaries = {}, {}
    for name, path in cases.items():
        rows, manifest, batches = read_case(path, corpus)
        ledgers[name] = rows
        mean_t = sum(int(b["toffoli"]) for b in batches) / N
        mean_c = sum(int(b["clifford"]) for b in batches) / N
        q = int(manifest["qubits"])
        counts = {f: sum(int(r[f]) for r in rows.values()) for f in FLAGS}
        f = counts["any_failure"]
        identity = [i for i, r in rows.items() if int(r["address"]) == 0]
        identity_f = sum(int(rows[i]["any_failure"]) for i in identity)
        summaries[name] = dict(qubits=q, mean_toffoli=mean_t, mean_clifford=mean_c,
                               static_operations=int(manifest["ops"]), ops_fingerprint=manifest["ops_fingerprint"],
                               **counts, pass_rate=1 - f / N, failure_rate_wilson_95=wilson(f, N),
                               raw_qxt=q * mean_t, retry_adjusted_qxt=q * mean_t / (1 - f / N),
                               identity_indices=sorted(identity), identity_failures=identity_f,
                               nonidentity_failures=f - identity_f, nonidentity_n=N - len(identity),
                               nonidentity_failure_rate=(f - identity_f) / (N - len(identity)),
                               nonidentity_wilson_95=wilson(f - identity_f, N - len(identity)),
                               address_failures=sum(int(r["got_address"], 16) != int(r["address"]) for r in rows.values()))
    reference = ledgers["mixed_pingpong"]
    corpus_hash = hashlib.sha256()
    for index in range(N):
        values = tuple(reference[index][f] for f in META)
        corpus_hash.update(("\t".join(values) + "\n").encode("ascii"))
        for name, ledger in ledgers.items():
            assert tuple(ledger[index][f] for f in META) == values, (name, index)
    common = [i for i, r in reference.items() if int(r["address"]) != 0 and r["target_x"] != r["addend_x"] and r["expected_x"] != r["addend_x"]]
    comparisons = (("mixed_pingpong", "windowed_pingpong"), ("windowed_jump2", "windowed_pingpong"),
                   ("mixed_jump2", "windowed_jump2"), ("mixed_jump2", "mixed_pingpong"))
    result = dict(tests=N, corpus_sha256_sorted_metadata=corpus_hash.hexdigest(), corpus_mismatches=0,
                  common_domain_size=len(common), circuits=summaries, paired={})
    for a, b in comparisons:
        if a not in ledgers or b not in ledgers:
            continue
        result["paired"][a + "_vs_" + b] = {"all_inputs": paired(ledgers[a], ledgers[b], list(range(N))),
                                                    "common_domain": paired(ledgers[a], ledgers[b], common)}
        by_channel = {}
        for flag in FLAGS:
            by_channel[flag] = {
                "baseline_only_indices": [i for i in range(N) if int(ledgers[a][i][flag]) and not int(ledgers[b][i][flag])],
                "candidate_only_indices": [i for i in range(N) if int(ledgers[b][i][flag]) and not int(ledgers[a][i][flag])],
            }
        result["paired"][a + "_vs_" + b]["discordant_indices_by_channel"] = by_channel
    if export:
        export.mkdir(parents=True, exist_ok=True)
        write_gzip_tsv(export / "corpus.tsv.gz", META, (reference[i] for i in range(N)))
        for name, rows in ledgers.items():
            dest = export / name
            dest.mkdir(exist_ok=True)
            compact = []
            for i in range(N):
                row = dict(rows[i])
                for got, expected in (("got_x", "expected_x"), ("got_y", "expected_y"), ("got_address", "address")):
                    same = int(row[got], 16) == int(row[expected]) if expected == "address" else row[got] == row[expected]
                    if same:
                        row[got] = "="
                compact.append(row)
            write_gzip_tsv(dest / "outcomes.tsv.gz", OUT, compact)
            for filename in ("manifest.tsv", "batches.tsv"):
                shutil.copy2(cases[name] / filename, dest / filename)
        # Reconstruct every observed output and recompute all statistics from the release.
        exported = analyze({name: export / name for name in cases}, export / "corpus.tsv.gz")
        assert exported == result
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", action="append", nargs=2, metavar=("NAME", "PATH"), required=True)
    parser.add_argument("--corpus", type=Path)
    parser.add_argument("--export", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = analyze({name: Path(path) for name, path in args.case}, args.corpus, args.export)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))
