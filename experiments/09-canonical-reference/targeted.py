"""Use the unchanged simulator/loader to test stored supported point fixtures."""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
ROOT=Path(__file__).resolve().parent
PREV=ROOT.parent/'qip2027-followup-diagnostics'
def main():
    p=argparse.ArgumentParser();p.add_argument('--w',type=int,default=4);p.add_argument('--baseline',action='store_true');a=p.parse_args()
    binary=PREV/'target/release/eval_followup'
    ops=ROOT/f'emit-window-{a.w}/ops.bin'
    if a.baseline:
        assert a.w==16
        ops=ROOT.parent/'qip2027-bounded-20260908/windowed-pilot/guarded-coordinates/ops.bin'
    results=[]
    for name in ['zero-slope','smoke']:
        tag=f'target-w{a.w}-{name}-'+('baseline' if a.baseline else 'canonical')
        env=dict(os.environ,EVAL_SHARED_SEED='qip-canonical-reference-targeted-20260909-v1')
        start=time.time()
        with (ROOT/'logs'/f'{tag}.tsv').open('w') as out,(ROOT/'logs'/f'{tag}.log').open('w') as err:
            result=subprocess.run([str(binary),str(ops),str(PREV/f'{name}.tsv'),'-'],env=env,stdout=out,stderr=err,timeout=600)
        assert result.returncode==0
        with (ROOT/'logs'/f'{tag}.tsv').open() as f:rows=list(csv.DictReader(f,delimiter='\t'))
        record={'name':tag,'seconds':time.time()-start,'ops_sha256':hashlib.sha256(ops.read_bytes()).hexdigest(),'input_sha256':hashlib.sha256((PREV/f'{name}.tsv').read_bytes()).hexdigest(),'failures':{k:sum(int(r[k]) for r in rows) for k in ['classical','phase','ancilla']},'interfaces_restored':all(r['interface_ok']=='true' for r in rows)}
        results.append(record);(ROOT/'logs'/f'{tag}.json').write_text(json.dumps(record,indent=2)+'\n');print(record,flush=True)
if __name__=='__main__':main()
