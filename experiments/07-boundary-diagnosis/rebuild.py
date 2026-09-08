#!/usr/bin/env python3
"""Offline, sequential rebuild and diagnostic replay into a fresh external directory."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import time

sys.dont_write_bytecode = True
from verify import ROOT, verify


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work-dir", type=Path, required=True, help="Fresh directory outside this package; all build outputs stay there.")
    args = parser.parse_args()
    verified = verify()
    work = args.work_dir.expanduser().resolve()
    if work == ROOT or work.is_relative_to(ROOT):
        parser.error("work directory must be outside the staged package")
    if work.exists():
        parser.error("work directory must not already exist; existing artifacts are never overwritten")
    work.mkdir(parents=True)
    for folder in ["cargo-home", "target", "tmp", "logs"]:
        (work / folder).mkdir()
    shutil.copytree(ROOT / "source", work / "source")
    # The verified archive contains regular files/directories only; preserve no links.
    with tarfile.open(ROOT / "dependencies/vendor.tar.gz", "r:gz") as tar:
        for member in tar:
            dest = work / member.name
            if member.isdir():
                dest.mkdir(parents=True, exist_ok=True)
            else:
                dest.parent.mkdir(parents=True, exist_ok=True)
                with tar.extractfile(member) as src, dest.open("wb") as dst:
                    shutil.copyfileobj(src, dst)
                dest.chmod(member.mode & 0o777)
    env = {k: v for k, v in os.environ.items() if not k.startswith(("QIP_", "SUB4_", "DIALOG_", "TLM_", "WINDOWED_", "TRACE_", "CARGO_", "RUSTFLAGS", "RUSTC_WRAPPER", "RUSTC_WORKSPACE_WRAPPER"))}
    env.update(CARGO_HOME=str(work / "cargo-home"), CARGO_TARGET_DIR=str(work / "target"),
               CARGO_BUILD_JOBS="1", CARGO_NET_OFFLINE="true", TMPDIR=str(work / "tmp"),
               QIP_PINGPONG_PROFILE="guarded", TLM_MSBS="40")
    build = ["cargo", "build", "--release", "--frozen", "--offline", "--bin", "build_circuit",
             "--config", 'source.crates-io.replace-with="vendored-sources"',
             "--config", "source.vendored-sources.directory=" + json.dumps(str(work / "vendor"))]
    started = time.monotonic()
    with (work / "logs/build.log").open("wb") as output:
        subprocess.run(build, cwd=work / "source", env=env, stdout=output, stderr=subprocess.STDOUT, check=True, timeout=900)
    executable = work / "target/release/build_circuit"
    runs = [
        ("baseline-final", None, "baseline"),
        ("component-final", "component", "baseline"),
        ("local_regression-baseline", "local_regression", "baseline"),
    ]
    runs += [(f"{mode}-final-{variant}", mode, variant) for mode in ["cells", "witnesses"]
             for variant in ["baseline", "full_compare", "full_width"]]
    results = []
    for tag, mode, variant in runs:
        settings = dict(env)
        if mode is None:
            settings["QIP_ZERO_PROBE_INPUTS"] = str(work / "source/probe-denominators.txt")
        else:
            settings.update(QIP_BOUNDARY_MODE=mode, QIP_BOUNDARY_VARIANT=variant)
        output_path = work / "logs" / f"{tag}.log"
        with output_path.open("wb") as output:
            subprocess.run([str(executable)], cwd=work / "source", env=settings,
                           stdout=output, stderr=subprocess.STDOUT, check=True, timeout=600)
        expected = (ROOT / "logs" / f"{tag}.log").read_bytes()
        actual = output_path.read_bytes()
        result = {"log": f"logs/{tag}.log", "mode": mode or "original-zero-probe", "variant": variant,
                  "sha256": hashlib.sha256(actual).hexdigest(), "matches_retained_raw_log": actual == expected}
        results.append(result)
        if actual != expected:
            raise RuntimeError(f"rebuilt diagnostic differs from retained raw log: {tag}; preserve this output for investigation")
    source_unchanged = all((work / "source" / p.relative_to(ROOT / "source")).read_bytes() == p.read_bytes()
                           for p in (ROOT / "source").rglob("*") if p.is_file())
    if not source_unchanged:
        raise RuntimeError("build changed copied source or lockfile")
    receipt = {"schema": 1, "successful": True, "scope": "New offline source rebuild and nine small diagnostic replays, not full point-addition evaluation.",
               "stage_manifest_sha256": verified["checks"]["stage_manifest"]["manifest_sha256"],
               "cargo_home_started_empty": True, "vendored_dependencies_only": True,
               "cargo_network_offline": True, "source_and_lockfile_unchanged": source_unchanged,
               "sequential_jobs": 1, "runs": results, "elapsed_seconds": time.monotonic() - started,
               "binary_sha256": hashlib.sha256(executable.read_bytes()).hexdigest(),
               "runtime": {" ".join(cmd): subprocess.check_output(cmd, text=True).strip()
                           for cmd in [["rustc", "--version"], ["cargo", "--version"], ["python3", "--version"]]}}
    (work / "rebuild-verification.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
