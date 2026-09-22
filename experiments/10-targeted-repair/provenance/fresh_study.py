"""Freeze the targeted repair before a new nine-table, 100,000-input study."""
import csv
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parent
WORKSPACE = ROOT.parents[1]
SOURCE = WORKSPACE/'ecdsafail-qip-oral-repairs-20260922'
ARTIFACT = ROOT/'repair-results/masked_chunk_coords-w16'
ORDER = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141

def sha(path):
    with path.open('rb') as f: return hashlib.file_digest(f,'sha256').hexdigest()

def main():
    output=ROOT/'fresh-zero-mask-100k'
    if output.exists(): raise FileExistsError('New study directory required; existing results are immutable.')
    output.mkdir()
    source_hashes={str(p.relative_to(SOURCE)):sha(p) for p in sorted((SOURCE/'src').rglob('*.rs'))}
    freeze={'time_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'source':source_hashes,
        'ops_sha256':sha(ARTIFACT/'ops.bin'),'driver_sha256':sha(SOURCE/'target/release/eval_bounded'),
        'analysis_sha256':sha(Path(__file__)),'protocol':{'inputs':100000,'strata':9,'window_bits':16,
        'counts':[11111]*8+[11112],'fresh_seed':'generated only after freeze file closes',
        'record_all_failures':True,'source_tuning_after_freeze':False,
        'candidate':'guarded768 + zero payload sign mask + exact chunk-carry cleanup + canonical coordinate subtractions',
        'scope':'One candidate on new inputs; no accuracy-matched comparison to previous studies.'}}
    (output/'freeze.json').write_text(json.dumps(freeze,indent=2)+'\n')
    master=os.urandom(32).hex()
    bases=[1]+[int.from_bytes(hashlib.sha256((master+f':base:{i}').encode()).digest(),'big')%(ORDER-1)+1 for i in range(2)]
    plan=[]
    for bi,base in enumerate(bases):
        for shift in [0,128,240]:
            i=len(plan)
            plan.append({'index':i,'base':hex(base),'shift':shift,'beta':hex(base*pow(2,shift,ORDER)%ORDER),
                'seed':master+f':stratum:{i}','n':11112 if i==8 else 11111})
    (output/'plan.json').write_text(json.dumps({'master_seed':master,'strata':plan},indent=2)+'\n')
    summaries=[]
    for spec in plan:
        directory=output/f"stratum-{spec['index']}"
        directory.mkdir()
        env={k:v for k,v in os.environ.items() if k in ['PATH','HOME','TMPDIR','LANG']}
        env.update(WINDOWED_MODE='1',WINDOW_BITS='16',WINDOWED_TESTS=str(spec['n']),WINDOWED_MAX_ERROR_RATE='1',
            EVAL_THREADS='6',EVAL_SHARED_SEED=spec['seed'],QIP_TABLE_BETA=spec['beta'],EVAL_CHECKPOINT_DIR=str(directory/'checkpoint'))
        start=time.monotonic()
        with (directory/'stdout').open('w') as o,(directory/'stderr').open('w') as e:
            proc=subprocess.run([str(SOURCE/'target/release/eval_bounded')],cwd=ARTIFACT,env=env,stdout=o,stderr=e,timeout=3600)
        proc.check_returncode()
        rows=list(csv.DictReader((directory/'checkpoint/inputs.tsv').open(),delimiter='\t'))
        batches=list(csv.DictReader((directory/'checkpoint/batches.tsv').open(),delimiter='\t'))
        summary={'stratum':spec,'seconds':time.monotonic()-start,'outcomes':len(rows),'batches':len(batches)}
        summaries.append(summary)
        (output/'progress.json').write_text(json.dumps(summaries,indent=2)+'\n')
        print(json.dumps(summary),flush=True)
    assert sum(s['outcomes'] for s in summaries)==100000
    assert source_hashes=={str(p.relative_to(SOURCE)):sha(p) for p in sorted((SOURCE/'src').rglob('*.rs'))}
    assert sha(ARTIFACT/'ops.bin')==freeze['ops_sha256']
    (output/'completed.json').write_text(json.dumps({'completed':True,'source_unchanged':True,'summaries':summaries},indent=2)+'\n')

if __name__=='__main__':main()
