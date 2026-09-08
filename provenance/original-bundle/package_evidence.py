"""Package frozen ledgers without changing the prespecified analysis."""
import argparse
import csv
import gzip
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import shutil
import sys
import tempfile

FIELDS = ("batch", "index", "address", "target_x", "target_y", "addend_x", "addend_y",
          "expected_x", "expected_y", "got_x", "got_y", "got_address",
          "classical_failure", "phase_failure", "ancilla_failure", "any_failure")
META = FIELDS[:9]
OUT = ("index", *FIELDS[9:])
PAIRS = (("got_x", "expected_x"), ("got_y", "expected_y"), ("got_address", "address"))


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_tsv(path):
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")
        return reader.fieldnames, list(reader)


def gz_tsv(path, fields, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", fileobj=raw, mode="wb", mtime=0) as z:
            with io.TextIOWrapper(z, encoding="ascii", newline="") as f:
                w = csv.DictWriter(f, fields, delimiter="\t", lineterminator="\n", extrasaction="ignore")
                w.writeheader()
                w.writerows(rows)


def compact(row):
    row = dict(row)
    for got, expected in PAIRS:
        canonical = hex(int(row[expected])) if expected == "address" else row[expected]
        if row[got] == canonical:
            row[got] = "="
    return row


def expand(meta, outcome):
    row = dict(meta)
    row.update(outcome)
    for got, expected in PAIRS:
        if row[got] == "=":
            row[got] = hex(int(row[expected])) if expected == "address" else row[expected]
    return row


def check_oracle_coverage(spec, freeze_hash, receipt):
    expected = {s["name"]: s for s in spec["strata"]}
    assert len(expected) == len(spec["strata"]) == 9
    assert receipt["freeze_sha256"] == spec["freeze_sha256"] == freeze_hash
    assert set(receipt["strata"]) == set(expected)
    assert receipt["mismatches"] == 0
    total = 0
    for name, s in expected.items():
        r = receipt["strata"][name]
        assert r["verified_cases"] == s["n"] and r["mismatches"] == 0
        assert r["seed"] == s["seed"] and int(r["beta"], 16) == int(s["beta"], 16)
        total += r["verified_cases"]
    assert total == receipt["verified_cases"] == 100000


def check_offsets(checkpoint):
    _, batches = read_tsv(checkpoint / "batches.tsv")
    with (checkpoint / "inputs.tsv").open("rb") as f:
        fields = f.readline().decode("ascii").rstrip("\n").split("\t")
        assert tuple(fields) == FIELDS
        for b in batches:
            rows = []
            for _ in range(int(b["shots"])):
                line = f.readline()
                assert line.endswith(b"\n")
                row = dict(zip(fields, line.decode("ascii").rstrip("\n").split("\t"), strict=True))
                assert row["batch"] == b["batch"]
                rows.append(row)
            assert f.tell() == int(b["inputs_end_offset"])
            for flag, count in (("phase_failure", "phase_garbage_batches"), ("ancilla_failure", "ancilla_garbage_batches")):
                assert int(b[count]) == int(any(int(r[flag]) for r in rows))
        assert f.read() == b""


def package(source, dest):
    assert not dest.exists(), "Choose a new release directory"
    freeze = json.loads((source / "freeze.json").read_text())
    spec = json.loads((source / "fresh-corpus-spec.json").read_text())
    assert spec["freeze_sha256"] == sha(source / "freeze.json")
    assert (source / "analysis.json").exists() and (source / "oracle-check.json").exists()
    dest.mkdir(parents=True)
    for name in ("freeze.json", "fresh-corpus-spec.json", "analysis.json", "oracle-check.json"):
        shutil.copy2(source / name, dest / name)
    omitted = []
    for rel, digest in freeze["files_sha256"].items():
        assert sha(source / rel) == digest
        if rel.startswith("artifacts/code/") or rel == "artifacts/source.tar.gz":
            (dest / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source / rel, dest / rel)
        else:
            omitted.append(rel)
    for s in spec["strata"]:
        ref_case = source / "results/pingpong_conservative" / s["name"]
        fields, rows = read_tsv(ref_case / "checkpoint/inputs.tsv")
        assert tuple(fields) == FIELDS
        corpus = {r["index"]: r for r in rows}
        assert len(corpus) == len(rows) == s["n"]
        gz_tsv(dest / "corpus" / (s["name"] + ".tsv.gz"), META, rows)
        for name in freeze["candidates"]:
            src_case = source / "results" / name / s["name"]
            target = dest / "results" / name / s["name"]
            target.mkdir(parents=True)
            for f in ("configuration.json", "COMPLETE.json", "eval.log", "checkpoint/manifest.tsv", "checkpoint/batches.tsv"):
                (target / f).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_case / f, target / f)
            fields, outcomes = read_tsv(src_case / "checkpoint/inputs.tsv")
            assert tuple(fields) == FIELDS
            for r in outcomes:
                assert tuple(r[k] for k in META) == tuple(corpus[r["index"]][k] for k in META)
            # Preserve original completion order so reconstruction recovers the raw file hash.
            gz_tsv(target / "checkpoint/outcomes.tsv.gz", OUT, map(compact, outcomes))
    supplemental = dest / "supplementary"
    supplemental.mkdir()
    for path in (source.parent / "source-snapshots").glob("*.tar.gz"):
        shutil.copy2(path, supplemental / path.name)
    for profile in ("base", "rounds", "widths", "guarded", "guarded-coordinates"):
        src = source.parent / "development" / profile
        target = supplemental / "development" / profile
        target.mkdir(parents=True)
        for name in ("summary.json", "eval.log", "checkpoint/manifest.tsv", "checkpoint/batches.tsv"):
            if (src / name).exists():
                (target / name).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src / name, target / name)
        data = (src / "checkpoint/inputs.tsv").read_bytes()
        (target / "checkpoint/inputs.tsv.gz").write_bytes(gzip.compress(data, mtime=0))
    shutil.copy2(source.parent / "development/oracle-check.json", supplemental / "development/oracle-check.json")
    shutil.copy2(source.parent / "phase-diagnostic/trace-parallel.log", supplemental / "coordinate-phase-trace.log")
    for label in ("official", "auxiliary"):
        src = source.parent / "evaluator-equivalence" / label
        target = supplemental / "evaluator-equivalence" / label
        (target / "checkpoint").mkdir(parents=True)
        for name in ("eval.log", "checkpoint/manifest.tsv", "checkpoint/batches.tsv"):
            shutil.copy2(src / name, target / name)
        data = (src / "checkpoint/inputs.tsv").read_bytes()
        (target / "checkpoint/inputs.tsv.gz").write_bytes(gzip.compress(data, mtime=0))
    reproduced = sha(source.parent / "operator-reproduction/ops.bin")
    assert reproduced == freeze["candidates"]["pingpong_conservative"]["ops_sha256"]
    receipt = dict(source_commit=freeze["source_commit"], reproduced_ops_sha256=reproduced,
                   frozen_ops_sha256=freeze["candidates"]["pingpong_conservative"]["ops_sha256"],
                   emission_settings=freeze["candidates"]["pingpong_conservative"]["settings"],
                   scope="Byte comparison of the recorded source rebuild against the frozen stream, not another accuracy experiment")
    (supplemental / "operator-reproduction.json").write_text(json.dumps(receipt, indent=2, sort_keys=True)+"\n")
    shutil.copy2(source.parent / "operator-reproduction/build.log", supplemental / "operator-reproduction.log")
    shutil.copy2(source.parent / "EVIDENCE_README.md", dest / "README.md")
    shutil.copy2(Path(__file__), dest / "package_evidence.py")
    index = dict(format="lossless-bounded-qip-release-v1", omitted_large_artifacts=omitted,
                 files={str(p.relative_to(dest)): sha(p) for p in dest.rglob("*") if p.is_file()})
    (dest / "release-index.json").write_text(json.dumps(index, indent=2, sort_keys=True) + "\n")
    verify(dest)


def materialize(release, work):
    index = json.loads((release / "release-index.json").read_text())
    for rel, digest in index["files"].items():
        assert sha(release / rel) == digest, rel
    freeze = json.loads((release / "freeze.json").read_text())
    for rel, digest in freeze["files_sha256"].items():
        if rel not in index["omitted_large_artifacts"]:
            assert sha(release / rel) == digest, rel
    for name in ("freeze.json", "fresh-corpus-spec.json"):
        shutil.copy2(release / name, work / name)
    spec = json.loads((work / "fresh-corpus-spec.json").read_text())
    for s in spec["strata"]:
        _, rows = read_tsv(release / "corpus" / (s["name"] + ".tsv.gz"))
        corpus = {r["index"]: r for r in rows}
        assert len(corpus) == len(rows) == s["n"]
        for name in freeze["candidates"]:
            src = release / "results" / name / s["name"]
            dst = work / "results" / name / s["name"]
            shutil.copytree(src, dst)
            _, outcomes = read_tsv(src / "checkpoint/outcomes.tsv.gz")
            path = dst / "checkpoint/inputs.tsv"
            with path.open("w", encoding="ascii", newline="") as f:
                w = csv.DictWriter(f, FIELDS, delimiter="\t", lineterminator="\n")
                w.writeheader()
                w.writerows(expand(corpus[r["index"]], r) for r in outcomes)
            complete = json.loads((src / "COMPLETE.json").read_text())
            for f, digest in complete["ledger_sha256"].items():
                assert sha(dst / "checkpoint" / f) == digest, (name, s["name"], f)
            check_offsets(dst / "checkpoint")


def verify(release, oracle=False):
    with tempfile.TemporaryDirectory(prefix="qip-ledger-check-") as tmp:
        work = Path(tmp)
        materialize(release, work)
        code = release / "artifacts/code/experiments/bounded_qip"
        sys.path.insert(0, str(code))
        module_spec = importlib.util.spec_from_file_location("frozen_analysis", code / "analyze.py")
        module = importlib.util.module_from_spec(module_spec)
        module_spec.loader.exec_module(module)
        result = module.analyze(work)
        assert result == json.loads((release / "analysis.json").read_text())
        spec = json.loads((work / "fresh-corpus-spec.json").read_text())
        recorded = json.loads((release / "oracle-check.json").read_text())
        check_oracle_coverage(spec, sha(work / "freeze.json"), recorded)
        for path in (release / "supplementary/development").glob("*/checkpoint/inputs.tsv.gz"):
            profile = path.parents[1].name
            target = work / "development" / profile
            shutil.copytree(path.parents[1], target)
            (target / "checkpoint/inputs.tsv").write_bytes(gzip.decompress(path.read_bytes()))
            check_offsets(target / "checkpoint")
            _, _, stats = module.read_case(target)
            expected = json.loads((target / "summary.json").read_text())
            for key in ("n", "Q", "mean_T", "QT", "classical_failure", "phase_failure", "ancilla_failure", "any_failure"):
                assert stats[key] == expected[key], (profile, key)
        equiv = []
        for label in ("official", "auxiliary"):
            src = release / "supplementary/evaluator-equivalence" / label
            dst = work / "equivalence" / label
            shutil.copytree(src, dst)
            (dst / "checkpoint/inputs.tsv").write_bytes(gzip.decompress((src / "checkpoint/inputs.tsv.gz").read_bytes()))
            check_offsets(dst / "checkpoint")
            eq_rows, _, eq_stats = module.read_case(dst)
            assert len(eq_rows) == eq_stats["n"] == 8192
            equiv.append((eq_rows, eq_stats))
        assert equiv[0] == equiv[1]
        if oracle:
            oracle_spec = importlib.util.spec_from_file_location("frozen_oracle", code / "verify_oracle.py")
            oracle_module = importlib.util.module_from_spec(oracle_spec)
            oracle_spec.loader.exec_module(oracle_module)
            for name, expected in recorded["strata"].items():
                assert oracle_module.verify_case(work / "results/pingpong_conservative" / name) == expected
        print("Verified 300,000 final outcome rows and raw hashes, frozen analysis, five development ledgers, and 8,192 evaluator-equivalence cases.")
        if oracle:
            print("Independently reconstructed all 100,000 input triples and expected sums with OpenSSL.")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("command", choices=("package", "verify"))
    p.add_argument("path", type=Path)
    p.add_argument("--destination", type=Path)
    p.add_argument("--oracle", action="store_true")
    args = p.parse_args()
    if args.command == "package":
        assert args.destination
        package(args.path.resolve(), args.destination.resolve())
    else:
        verify(args.path.resolve(), args.oracle)
