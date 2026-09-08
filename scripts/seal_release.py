#!/usr/bin/env python3
"""Refresh the publication inventory after deliberate edits, never the study freeze."""
import argparse
import json
import subprocess

from common import ROOT, atomic_write, ensure_checks_enabled, safe_path, sha
from verify_mechanism import verify_preserved_v1_science


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", required=True)
    args = parser.parse_args()
    ensure_checks_enabled()
    verify_preserved_v1_science()
    names = subprocess.check_output(["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"], cwd=ROOT).decode().split("\0")
    names = sorted(set(n for n in names if n and n != "provenance/publication-manifest.json"))
    files = {name: sha(safe_path(ROOT, name)) for name in names}
    data = dict(format="ecdsafail-publication-manifest-v1", release=args.version,
                previous_release="v1.0.0", files=files)
    atomic_write(ROOT / "provenance/publication-manifest.json", json.dumps(data, indent=2, sort_keys=True) + "\n")
    print(f"Sealed {len(files)} publication files for {args.version}; original science files unchanged.")


if __name__ == "__main__":
    main()
