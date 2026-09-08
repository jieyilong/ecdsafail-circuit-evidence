#!/usr/bin/env python3
"""Serial, bounded builds and emissions. All children write under this directory."""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import resource
import signal
import sys
import shutil
import subprocess
import time

ROOT = Path(os.environ["ACCOUNTING_WORK_ROOT"]).resolve()
TREES = ("original-pingpong", "conservative-pingpong", "jump2")

def sha(p):
    with p.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()

def env():
    tmp = ROOT / "tmp"
    tmp.mkdir(exist_ok=True)
    return dict(PATH=os.environ["PATH"], HOME=os.environ["HOME"], TMPDIR=str(tmp),
                LANG="C", LC_ALL="C", CARGO_TARGET_DIR=str(ROOT / "build"),
                CARGO_BUILD_JOBS="2", CARGO_PROFILE_RELEASE_LTO="false",
                CARGO_PROFILE_RELEASE_CODEGEN_UNITS="1", RAYON_NUM_THREADS="4",
                OMP_NUM_THREADS="4")

def run(command, cwd, settings, label, timeout=600):
    log = ROOT / "logs" / f"{label}.log"
    log.parent.mkdir(exist_ok=True)
    if log.exists():
        log = log.with_name(f"{label}-{time.time_ns()}.log")
    start = time.time()
    with log.open("w") as f:
        try:
            p = subprocess.Popen(["/usr/bin/time", "-l" if sys.platform == "darwin" else "-v", *command], cwd=cwd,
                                 env=env() | settings, stdout=f, stderr=subprocess.STDOUT,
                                 start_new_session=True)
            peak_kib = 0
            while p.poll() is None:
                rows = subprocess.check_output(["ps", "-axo", "pgid=,rss="], text=True)
                rss = sum(int(row.split()[1]) for row in rows.splitlines()
                          if row.split() and int(row.split()[0]) == p.pid)
                peak_kib = max(peak_kib, rss)
                if rss > 11_000_000 or time.time()-start > timeout:
                    os.killpg(p.pid, signal.SIGKILL)
                    p.wait()
                    code = "memory_guard" if rss > 11_000_000 else "timeout"
                    break
                time.sleep(0.5)
            else:
                code = p.returncode
        except (subprocess.SubprocessError, OSError) as exc:
            if 'p' in locals() and p.poll() is None:
                os.killpg(p.pid, signal.SIGKILL)
                p.wait()
            code = str(exc)
            peak_kib = 0
    record = dict(command=command, cwd=str(cwd), settings=settings, exit_code=code,
                  elapsed_seconds=round(time.time()-start, 3), sampled_peak_group_kib=peak_kib,
                  log=str(log.relative_to(ROOT)))
    with (ROOT / "commands.jsonl").open("a") as f:
        f.write(json.dumps(record)+"\n")
    print(label, code, record["elapsed_seconds"], flush=True)
    return code

def build(which):
    for name in TREES:
        src = ROOT / which / name
        bins = ["build_circuit"]
        if which == "sources" and name == "conservative-pingpong":
            bins += ["eval_bounded"]
        command = ["cargo", "build", "--release", "--locked", "--offline"]
        for b in bins:
            command += ["--bin", b]
        target = ROOT / "builds" / which / name
        code = run(command, src, {"CARGO_TARGET_DIR": str(target)}, f"compile-{which}-{name}")
        if code != 0:
            raise RuntimeError(f"build failed: {which}/{name}; inspect work-directory logs")
        dst = ROOT / "bin" / which / name
        dst.mkdir(parents=True, exist_ok=True)
        for b in bins:
            shutil.copy2(target / "release" / b, dst / b)

def emit(name, tree, instrumented, settings, count_only=False):
    which = "instrumented" if instrumented else "sources"
    dst = ROOT / "runs" / name
    assert not dst.exists(), f"Run already exists: {dst}"
    dst.mkdir(parents=True)
    config = dict(settings)
    if instrumented:
        config["ACCOUNTING_DIR"] = str(dst)
    if count_only:
        config["ACCOUNTING_COUNT_ONLY"] = "1"
    code = run([str(ROOT / "bin" / which / tree / "build_circuit")], dst, config, name)
    result = dict(name=name, source=tree, instrumented=instrumented, count_only=count_only,
                  settings=settings, exit_code=code)
    if (dst / "ops.bin").exists():
        result["compressed_sha256"] = sha(dst / "ops.bin")
        result["compressed_bytes"] = (dst / "ops.bin").stat().st_size
        with (dst / "ops.bin").open("rb") as f:
            assert f.read(8) == b"QECCOPSZ"
            result["operations"] = int.from_bytes(f.read(8), "little")
    (dst / "result.json").write_text(json.dumps(result, indent=2)+"\n")
    if code != 0:
        raise RuntimeError(f"emission failed: {name}; receipt preserved")

def experiments():
    configs = [
        ("mixed1321", "original-pingpong", {}),
        ("original-w4", "original-pingpong", {"WINDOWED_MODE":"1", "WINDOW_BITS":"4", "WINDOWED_QROM_UNLOAD":"split"}),
        ("conservative-w4", "conservative-pingpong", {"WINDOWED_MODE":"1", "WINDOW_BITS":"4", "WINDOWED_QROM_UNLOAD":"split", "QIP_PINGPONG_PROFILE":"guarded", "TLM_MSBS":"40"}),
        ("jump2-mixed", "jump2", {}),
        ("pingpong-legacy-square", "original-pingpong", {"SUB4_LEGACY_SQUARE":"1"}),
    ]
    for name, tree, settings in configs:
        emit(name+"-unchanged", tree, False, settings)
        emit(name, tree, True, settings)
        emit(name+"-count", tree, True, settings, True)
    for name, tree, extra in [("windowed1338", "original-pingpong", {}),
                               ("conservative1392", "conservative-pingpong", {"QIP_PINGPONG_PROFILE":"guarded", "TLM_MSBS":"40"}),
                               ("jump2-windowed", "jump2", {})]:
        emit(name+"-count", tree, True, {"WINDOWED_MODE":"1", "WINDOW_BITS":"16", "WINDOWED_QROM_UNLOAD":"split", "SINGLE_CCX_FANOUT_DISABLE":"1"} | extra, True)

def ablation():
    shared = {"CONSTPROP_DISABLE":"1", "SINGLE_CCX_FANOUT_DISABLE":"1",
              "TLM_TARGET_Q":"1150", "TLM_FOLD_CHUNK_ZERO_CIN":"1",
              "TLM_FFG_MAX_G":"47", "TLM_APPLY_ADD_SKIP_LASTK":"1",
              "DIALOG_TAIL_NONCE":"2430844", "DIALOG_GCD_FOLD_MAJ1":"1"}
    for backend in ("pingpong", "legacy"):
        for square in ("product", "legacy"):
            settings = dict(shared)
            if backend == "legacy":
                settings["SUB4_LEGACY_POINT_ADD"] = "1"
            if square == "legacy":
                settings["SUB4_LEGACY_SQUARE"] = "1"
            name = f"ablation-{backend}-{square}"
            emit(name, "original-pingpong", True, settings)
            emit(name+"-unchanged", "original-pingpong", False, settings)

def smoke_names(names):
    evaluator = ROOT / "bin/sources/conservative-pingpong/eval_bounded"
    for name in names:
        dst = ROOT / "runs" / name
        if not (dst / "ops.bin").exists():
            continue
        settings = {"MIXED_WINDOW_BITS":"4", "EVAL_TESTS":"64", "EVAL_THREADS":"1",
                    "EVAL_SHARED_SEED":"qip-accounting-smoke-20260908-v1",
                    "EVAL_MAX_ERROR_RATE":"1", "EVAL_CHECKPOINT_DIR":str(dst / "smoke")}
        assert not (dst / "smoke").exists(), "Do not overwrite an existing smoke receipt"
        code = run([str(evaluator)], dst, settings, name+"-smoke", timeout=180)
        if code != 0:
            raise RuntimeError(f"evaluator failed: {name}; logs preserved")

def smoke():
    smoke_names([f"ablation-{b}-{s}" for b in ("pingpong", "legacy") for s in ("product", "legacy")])


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("action", choices=["build-original", "build-instrumented", "experiments", "ablation", "smoke", "bounded-all"])
    args = p.parse_args()
    if args.action == "bounded-all":
        build("instrumented")
        experiments()
        ablation()
        smoke()
    elif args.action.startswith("build"):
        build("sources" if args.action == "build-original" else "instrumented")
    elif args.action == "experiments":
        experiments()
    elif args.action == "ablation":
        ablation()
    else:
        smoke()
