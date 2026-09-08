#!/usr/bin/env python3
"""Stream a QECCOPSZ artifact without retaining its uncompressed gate list."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

NAMES = ("Neg", "Register", "AppendToRegister", "BitInvert", "BitStore0", "BitStore1", "X", "Z", "CX", "CZ", "Swap", "R", "Hmr", "CCX", "CCZ", "PushCondition", "PopCondition", "DebugPrint")


def measure(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    counts = Counter()
    with tempfile.TemporaryFile() as compressed:
        with path.open("rb") as f:
            header = f.read(16)
            assert header[:8] == b"QECCOPSZ"
            expected = int.from_bytes(header[8:], "little")
            shutil.copyfileobj(f, compressed)
        compressed.seek(0)
        process = subprocess.Popen(["zstd", "-dc"], stdin=compressed, stdout=subprocess.PIPE)
        remainder = b""
        while True:
            block = process.stdout.read(4 << 20)
            if not block:
                break
            block = remainder + block
            stop = len(block) - len(block) % 56
            counts.update(block[0:stop:56])
            for offset in (1, 2, 3):
                assert not any(block[offset:stop:56]), "Invalid operation tag"
            remainder = block[stop:]
        assert process.wait() == 0 and not remainder
    assert sum(counts.values()) == expected and set(counts) <= set(range(len(NAMES)))
    return dict(ops_sha256=h.hexdigest(), static_operations=expected,
                static_toffoli=counts[13] + counts[14], static_hmr=counts[12], static_reset=counts[11],
                operation_kind_counts={NAMES[i]: counts[i] for i in range(len(NAMES))},
                toffoli_depth=None, feed_forward_rounds=None,
                note="Static HMR/reset counts are not executed measurement counts or feed-forward depth.")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("ops", type=Path)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    result = measure(args.ops)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))
