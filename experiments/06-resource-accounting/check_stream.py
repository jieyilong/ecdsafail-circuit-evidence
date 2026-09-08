#!/usr/bin/env python3
"""Rebuild the ledger and evidence checks without loading a complete stream."""
from collections import Counter, defaultdict
import csv
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parent

def rows(path):
    with path.open() as f:
        return list(csv.DictReader(f, delimiter="\t"))

def stream(path):
    counts = Counter()
    digest = hashlib.sha256()
    with path.open("rb", buffering=0) as f:
        assert f.read(8) == b"QECCOPSZ"
        expected = int.from_bytes(f.read(8), "little")
        proc = subprocess.Popen(["zstd", "-dc"], stdin=f, stdout=subprocess.PIPE)
        rest = b""
        while True:
            block = proc.stdout.read(4 << 20)
            if not block:
                break
            digest.update(block)
            block = rest + block
            stop = len(block) - len(block) % 56
            counts.update(block[:stop:56])
            assert all(not any(block[i:stop:56]) for i in (1,2,3))
            rest = block[stop:]
        code = proc.wait()
        proc.stdout.close()
        assert code == 0 and not rest
    assert sum(counts.values()) == expected and set(counts) <= set(range(18))
    return dict(operations=expected, static_toffoli=counts[13]+counts[14],
                raw_body_sha256=digest.hexdigest(), kind_counts=dict(counts))

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="Rehash a newly rebuilt QECCOPSZ stream; requires zstd CLI")
    p.add_argument("ops", type=Path)
    args = p.parse_args()
    print(json.dumps(stream(args.ops), indent=2))
