#!/usr/bin/env python3
"""Write a portable release manifest and, optionally, a local experiment manifest."""
import argparse
from pathlib import Path

from analyze_results import sha256


def manifest(base, files):
    lines = [f"{sha256(path)}  {path.relative_to(base).as_posix()}" for path in sorted(files)]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--workspace", type=Path)
    args = p.parse_args()
    here = Path(__file__).resolve().parent
    repo = here.parents[1]
    files = [path for path in here.rglob("*") if path.is_file() and "__pycache__" not in path.parts and path.name != "ARTIFACT_MANIFEST.sha256"]
    files.append(repo / "WINDOWED_PINGPONG.md")
    (here / "ARTIFACT_MANIFEST.sha256").write_text(manifest(repo, files))
    print(f"Release manifest: {len(files)} files")
    if args.workspace:
        root = args.workspace.resolve()
        output = root / "outputs/ecdsafail-pingpong-windowed-100k-20260907"
        local = [path for path in output.rglob("*") if path.is_file() and path.name != "ARTIFACT_MANIFEST.sha256"]
        local.append(root / "ECDSAFAIL_PINGPONG_VALIDATION_EXPERIMENTS.md")
        (output / "ARTIFACT_MANIFEST.sha256").write_text(manifest(root, local))
        print(f"Local manifest (paths relative to paper workspace): {len(local)} files")
