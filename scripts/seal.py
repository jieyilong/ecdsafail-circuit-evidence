#!/usr/bin/env python3
"""Maintainer command: seal the curated files without changing the original freeze."""
import json
from common import ROOT, sha, verify_original, verify_sources

verify_original()
verify_sources()
files={}
for p in sorted(ROOT.rglob("*")):
    rel=p.relative_to(ROOT)
    if not p.is_file() or any(part in {".git", ".work", "__pycache__"} for part in rel.parts) or p.suffix in {".pyc", ".pyo"}:
        continue
    if rel.as_posix()=="provenance/publication-manifest.json":
        continue
    assert not p.is_symlink()
    files[rel.as_posix()]=sha(p)
(ROOT/"provenance/publication-manifest.json").write_text(json.dumps(dict(format="ecdsafail-publication-manifest-v1", files=files),indent=2,sort_keys=True)+"\n")
print(f"Sealed {len(files)} curated files; original freeze and evidence bytes unchanged.")
