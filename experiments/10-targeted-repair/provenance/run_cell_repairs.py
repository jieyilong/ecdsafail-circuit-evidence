"""Compare actual emitted replay cells on the retained boundary grid."""
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parent
WORKSPACE = ROOT.parents[1]
SOURCE = WORKSPACE / 'ecdsafail-qip-oral-repairs-20260922'
BINARY = SOURCE / 'target/release/build_circuit'
P = 2**256 - 2**32 - 977

def main():
    out = ROOT / 'repair-results'
    out.mkdir(exist_ok=True)
    variants = {
        'guarded': {},
        'exact_chunk': {'QIP_EXACT_CHUNK_CARRY': '1'},
        'chunk_and_endpoints': {'QIP_EXACT_CHUNK_CARRY': '1', 'QIP_CANONICAL_ENDPOINTS': '1'},
        'canonical_reference': {'QIP_CANONICAL_REPLAY': '1'},
    }
    env = {k: v for k, v in os.environ.items() if k in ('PATH', 'HOME', 'TMPDIR', 'LANG')}
    env.update(QIP_PINGPONG_PROFILE='guarded768', QIP_BOUNDARY_MODE='cells', DIALOG_GCD_FOLD_MAJ1='1')
    summary = {}
    for name, extra in variants.items():
        result = subprocess.run([str(BINARY)], cwd=SOURCE, env=env | extra, capture_output=True, text=True, timeout=180)
        (out / (name + '.stdout')).write_text(result.stdout)
        (out / (name + '.stderr')).write_text(result.stderr)
        result.check_returncode()
        lines = result.stdout.splitlines()
        header = next(x.removeprefix('CELL_HEADER ') for x in lines if x.startswith('CELL_HEADER '))
        rows = list(csv.DictReader(io.StringIO(header + '\n' + '\n'.join(x.removeprefix('CELL ') for x in lines if x.startswith('CELL ')))))
        kernels = {}
        for row in rows:
            if int(row['source'], 16) >= P or int(row['target'], 16) >= P:
                continue
            entry = kernels.setdefault(row['kernel'], {'cases': 0, 'word_bad': 0, 'field_bad': 0, 'phase': 0, 'ancilla': 0, 'source_bad': 0, 'control_bad': 0,
                'peak': int(row['peak']), 'static_toffoli': int(row['emitted_toffoli'])})
            entry['cases'] += 1
            for key in ('word_bad', 'field_bad', 'phase', 'ancilla', 'source_bad', 'control_bad'):
                entry[key] += int(row[key])
        summary[name] = kernels
        print(name, json.dumps(kernels), flush=True)
    report = {'binary_sha256': hashlib.sha256(BINARY.read_bytes()).hexdigest(), 'scope': 'Emitted local cells on canonical boundary grid; not full calls or an all-input proof.', 'variants': summary}
    (out / 'cell-summary.json').write_text(json.dumps(report, indent=2) + '\n')

if __name__ == '__main__':
    main()
