#!/usr/bin/env python3
"""Optional source rebuild in a fresh scratch directory, never in the receipts."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
import zipfile

sys.dont_write_bytecode = True
from verify import root_path, sha, verify_package, TREES


def evidence_root(root, explicit):
    if explicit:
        candidate = Path(explicit).resolve()
        assert (candidate / "sources/trees").is_dir(), "expected evidence repository sources/trees"
        return candidate
    return next((p for p in root.parents if (p / "sources/trees").is_dir() and (p / "provenance/freeze.json").is_file()), None)


def prepare(root, work, external):
    assert not work.exists(), "Use a new --work-dir; existing outputs are never overwritten"
    verify_package(root)
    work.mkdir(parents=True)
    with zipfile.ZipFile(root / "source-snapshots.zip") as z:
        for info in z.infolist():
            dst = work / info.filename
            dst.parent.mkdir(parents=True, exist_ok=True)
            with z.open(info) as src, dst.open("wb") as out:
                shutil.copyfileobj(src, out)
    if external:
        manifest = json.loads((root / "receipts/source-manifest.json").read_text())
        for rel,digest in manifest.items():
            assert sha(external / "sources/trees" / rel) == digest, rel
    shutil.copy2(root / "source-archive-manifest.json", work / "source-archive-manifest.json")
    marker = dict(source_archive_sha256=sha(root / "source-snapshots.zip"), external_source_crosscheck=bool(external))
    (work / "prepared.json").write_text(json.dumps(marker, indent=2)+"\n")
    print(json.dumps(dict(status="PREPARED", work_dir=str(work), **marker), indent=2))


def exact_counts(runner):
    for name,tree,extra in [("windowed1338", "original-pingpong", {}),
                            ("conservative1392", "conservative-pingpong", {"QIP_PINGPONG_PROFILE":"guarded", "TLM_MSBS":"40"}),
                            ("jump2-windowed", "jump2", {})]:
        common = {"WINDOWED_MODE":"1", "WINDOWED_QROM_UNLOAD":"split", "SINGLE_CCX_FANOUT_DISABLE":"1"} | extra
        small = common | {"WINDOW_BITS":"4"}
        runner.emit(name+"-exact-w4", tree, True, small)
        runner.emit(name+"-exact-w4-unchanged", tree, False, small)
        runner.emit(name+"-exact-w4-count", tree, True, small | {"ACCOUNTING_EXACT_QROM":"1"}, True)
        runner.emit(name+"-exact-count", tree, True, common | {"WINDOW_BITS":"16", "ACCOUNTING_EXACT_QROM":"1"}, True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("action", choices=["prepare", "build", "ablation", "accounting", "all"])
    p.add_argument("--root", help="Package or evidence repository root")
    p.add_argument("--work-dir", type=Path, required=True, help="New scratch output directory; use _work/NAME inside the package")
    p.add_argument("--evidence-root", help="Optional read-only crosscheck against an evidence repository; otherwise autodetected")
    args = p.parse_args()
    root, work = root_path(args.root), args.work_dir.resolve()
    if work == root or root.is_relative_to(work):
        p.error("work directory must not contain the release")
    if work.is_relative_to(root) and work.relative_to(root).parts[0] != "_work":
        p.error("inside the release, rebuild output must be under _work/")
    if args.action == "prepare":
        prepare(root, work, evidence_root(root,args.evidence_root))
        return
    verify_package(root)
    assert (work / "prepared.json").is_file(), "Run prepare first"
    marker = json.loads((work / "prepared.json").read_text())
    assert marker["source_archive_sha256"] == sha(root / "source-snapshots.zip")
    manifest = json.loads((work / "source-archive-manifest.json").read_text())
    for rel,metadata in manifest.items():
        assert sha(work / rel) == metadata["sha256"], (rel,"source was edited")
    os.environ["ACCOUNTING_WORK_ROOT"] = str(work)
    spec = importlib.util.spec_from_file_location("portable_runner", root / "runner.py")
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    if args.action in ("build","all"):
        runner.build("sources")
        runner.build("instrumented")
    if args.action in ("ablation","all"):
        runner.ablation()
        runner.smoke()
    if args.action in ("accounting","all"):
        runner.experiments()
        exact_counts(runner)
        # The four ablation runs and two original/default runs share the seed.
        for name in ("mixed1321", "pingpong-legacy-square"):
            runner.smoke_names([name])


if __name__ == "__main__":
    main()
