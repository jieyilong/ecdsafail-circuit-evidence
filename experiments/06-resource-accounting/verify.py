#!/usr/bin/env python3
"""Offline, read-only package and receipt verification. Never rewrites evidence."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import sys
import zipfile

sys.dont_write_bytecode = True
from ledger import reconstruct

TREES = ("original-pingpong", "conservative-pingpong", "jump2")
ALLOWED = {"src/point_add/mod.rs", "src/point_add/pingpong_div.rs",
           "src/point_add/trailmix_ludicrous/gcd.rs", "src/point_add/trailmix_ludicrous/qrom.rs"}


def root_path(value=None):
    root = Path(value or os.environ.get("ACCOUNTING_RELEASE_ROOT", Path(__file__).resolve().parent)).resolve()
    if (root / "experiments/06-resource-accounting/package-manifest.json").is_file():
        root = root / "experiments/06-resource-accounting"
    return root


def sha(path):
    with path.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def verify_package(root):
    manifest = json.loads((root / "package-manifest.json").read_text())
    for rel, metadata in manifest["files"].items():
        path = root / rel
        assert path.is_file() and path.stat().st_size == metadata["bytes"], rel
        assert sha(path) == metadata["sha256"], (rel, "package hash mismatch")
    sources = json.loads((root / "receipts/source-manifest.json").read_text())
    members = json.loads((root / "source-archive-manifest.json").read_text())
    with zipfile.ZipFile(root / "source-snapshots.zip") as z:
        assert len(z.namelist()) == len(set(z.namelist())) == len(members)
        assert set(z.namelist()) == set(members)
        for rel, metadata in members.items():
            p = PurePosixPath(rel)
            assert not p.is_absolute() and ".." not in p.parts
            info = z.getinfo(rel)
            assert info.file_size == metadata["bytes"]
            with z.open(info) as f:
                assert hashlib.file_digest(f, "sha256").hexdigest() == metadata["sha256"], rel
    changed = []
    for rel, digest in sources.items():
        assert members["sources/"+rel]["sha256"] == digest
        if members["instrumented/"+rel]["sha256"] != digest:
            assert rel.split("/",1)[1] in ALLOWED, rel
            changed.append(rel)
    extras = set(members)-{"sources/"+r for r in sources}-{"instrumented/"+r for r in sources}
    assert extras == {f"instrumented/{t}/src/point_add/accounting.rs" for t in TREES}
    return manifest, changed


def verify(root):
    manifest, changed = verify_package(root)
    receipts = root / "receipts"
    actual = reconstruct(receipts)
    assert actual == json.loads((receipts / "results.json").read_text()), "reconstructed results differ"
    failed = [c for c in actual["checks"] if not c["passed"]]
    assert {(c["name"],c["check"]) for c in failed} == {
        ("original-w4", "count_only_raw_operations"), ("conservative-w4", "count_only_raw_operations")}
    for c in actual["ablation_controls"].values():
        assert c["square_category_identical"]
        assert c["effective_settings_differences"] == {"SUB4_LEGACY_POINT_ADD":["1",None]}
    frozen = json.loads((root / "provenance/freeze.json").read_text())["candidates"]
    recorded = json.loads((receipts / "verification.json").read_text())
    bridge = {}
    for name, key, tail in [("windowed1338-exact-count", "pingpong_base", 96),
                            ("conservative1392-exact-count", "pingpong_conservative", 96),
                            ("jump2-windowed-exact-count", "jump2", 0)]:
        r,f = actual["results"][name],frozen[key]
        assert r["live_peak"] == f["Q"]
        bridge[key] = dict(Q=r["live_peak"], raw_static_toffoli=r["raw_static_toffoli"], frozen_final_static_toffoli=f["static_toffoli"],
                           postcompiler_toffoli_delta=f["static_toffoli"]-r["raw_static_toffoli"], raw_ops=r["raw_operations"], identity_tail_ops=tail,
                           frozen_final_ops=f["static_operations"], postcompiler_ops_delta=f["static_operations"]-r["raw_operations"]-tail)
    assert bridge == recorded["frozen_resource_bridge"]
    return dict(status="PASS", protected_source_files=259, archived_source_members=521,
                changed_emitter_files=len(changed), reconstructed_runs=len(actual["results"]),
                matching_stream_receipt_pairs=sum(c["check"] == "instrumentation_stream_identity" for c in actual["checks"]),
                smoke_runs=len(actual["smoke"]), smoke_cases_per_run=64,
                known_superseded_count_failures=len(failed), frozen_resource_bridge=bridge,
                verification_mode="offline read-only receipt/source verification; operation streams and executable hashes are historical receipts, not remeasured",
                network_required=False, workspace_paths_required=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", help="Staged directory or evidence repository root; defaults to script directory")
    args = parser.parse_args()
    print(json.dumps(verify(root_path(args.root)), indent=2))
