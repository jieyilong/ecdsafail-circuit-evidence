"""Read-only publication verification and scalar reanalysis; no circuit execution."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parent
EVIDENCE=ROOT.parents[1]
def main():
    if not __debug__:raise RuntimeError('Assertions must remain enabled')
    original=json.loads((ROOT/'provenance/original-manifest.json').read_text())
    moved={'README.md':'provenance/original-README.md','REPORT.md':'provenance/original-REPORT.md'}
    for rel,digest in original.items():
        path=ROOT/moved.get(rel,rel)
        assert hashlib.sha256(path.read_bytes()).hexdigest()==digest,rel
    subprocess.run([sys.executable,'-B',str(ROOT/'verify_records.py')],check=True,capture_output=True,text=True)
    names=['test_supported_zero_slope','test_chunk_equality_positive_control','test_width_repair_of_smoke_cell','test_unchanged_trusted_modules','test_segmented_equals_whole_stream','test_reproduce_prior_smoke']
    env=dict(os.environ,ECDSAFAIL_EVIDENCE_ROOT=str(EVIDENCE))
    tests=subprocess.run([sys.executable,'-B',str(ROOT/'test_diagnostics.py'),*[f'Diagnostics.{name}' for name in names]],env=env,capture_output=True,text=True,check=True)
    with tempfile.TemporaryDirectory(prefix='ecdsafail-followup-verify-') as tmp:
        work=Path(tmp)
        for path in ROOT.glob('*.py'):shutil.copy2(path,work/path.name)
        for path in ROOT.glob('*.tsv'):shutil.copy2(path,work/path.name)
        shutil.copytree(ROOT/'logs',work/'logs')
        subprocess.run([sys.executable,'-B',str(work/'analyze_targeted.py')],check=True,capture_output=True,text=True)
        assert json.loads((work/'targeted-analysis.json').read_text())==json.loads((ROOT/'targeted-analysis.json').read_text())
    print(json.dumps({'status':'PASS','preserved_original_files':len(original),'standard_library_tests':len(names),'scalar_reanalysis_matches':True,'tail_trials_recorded':10000000,'guard_cases_recorded':99997,'scope':'Record integrity, scalar/trace correspondence, and local tests. No new circuit or ten-million-trial execution; GMP crosscheck is optional.'},indent=2))
if __name__=='__main__':main()
