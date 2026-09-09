"""Freeze the reference candidate before a new, independently seeded pilot."""
import hashlib
import json
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parent
out=ROOT/'candidate-freeze.json'
assert not out.exists()
files=[ROOT/'emit-window-16/ops.bin',ROOT/'target/release/eval_bounded',ROOT/'run.py']+sorted((ROOT/'source/src').rglob('*.rs'))
hashes={str(p.relative_to(ROOT)):hashlib.file_digest(p.open('rb'),'sha256').hexdigest() for p in files}
record={'frozen_utc':datetime.now(timezone.utc).isoformat(),'inputs':4096,'window_bits':16,
        'table':'[j]G','seed':'qip-canonical-replay-fresh-20260909-v1','threads':2,
        'policy':'Preserve every output and phase/ancilla flag. Do not tune after observing the pilot. This is not the original frozen 100,000-input study.',
        'files_sha256':hashes}
out.write_text(json.dumps(record,indent=2)+'\n')
print('Candidate frozen before fresh input generation.')
