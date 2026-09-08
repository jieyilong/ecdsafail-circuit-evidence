#!/usr/bin/env python3
"""Check the evaluator fingerprint with bounded memory (requires NumPy and zstd)."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

import numpy as np


def check(ops, manifest):
    expected = dict(line.split("\t", 1) for line in manifest.read_text().splitlines())
    h = hashlib.shake_256(b"quantum_ecc-checkpoint-ops-v1")
    with tempfile.TemporaryFile() as compressed:
        with ops.open("rb") as f:
            header = f.read(16)
            assert header[:8] == b"QECCOPSZ"
            count = int.from_bytes(header[8:], "little")
            assert count == int(expected["ops"])
            h.update(header[8:])
            shutil.copyfileobj(f, compressed)
        compressed.seek(0)
        process = subprocess.Popen(["zstd", "-dc"], stdin=compressed, stdout=subprocess.PIPE)
        remainder, seen = b"", 0
        while True:
            block = process.stdout.read(4 << 20)
            if not block:
                break
            block = remainder + block
            stop = len(block) - len(block) % 56
            data = np.frombuffer(block[:stop], dtype=np.uint8).reshape(-1, 56)
            assert not data[:, 1:4].any()
            packed = np.empty((len(data), 49), dtype=np.uint8)
            packed[:, 0] = data[:, 0]
            packed[:, 1:] = data[:, 8:]
            h.update(packed.tobytes())
            seen += len(data)
            remainder = block[stop:]
        assert process.wait() == 0 and not remainder and seen == count
    result = dict(operations=count, fingerprint=h.hexdigest(16), expected_fingerprint=expected["ops_fingerprint"])
    assert result["fingerprint"] == result["expected_fingerprint"], result
    return result


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("ops", type=Path)
    p.add_argument("manifest", type=Path)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    result = check(args.ops, args.manifest)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
