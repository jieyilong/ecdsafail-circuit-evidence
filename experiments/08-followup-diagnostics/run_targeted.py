"""Replay unchanged bounded streams with explicit fixtures, retaining every lane."""
import hashlib
import argparse
import json
import os
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parent
PRIOR = ROOT.parent/'qip2027-mechanism-revision-20260908/accounting/runs'
def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--streams-root',type=Path,default=PRIOR)
    args=parser.parse_args()
    results=[]
    for artifact in ['ablation-pingpong-product','mixed1321','original-w4','conservative-w4']:
        for fixture in ['smoke','zero-slope']:
            source=args.streams_root.resolve()/artifact
            binary=ROOT/'target/release/eval_followup'
            command=[str(binary),str(source/'ops.bin'),str(ROOT/f'{fixture}.tsv'),str(source/'phases.tsv')]
            env=dict(os.environ,EVAL_SHARED_SEED='qip-accounting-smoke-20260908-v1',TRACE_LANE='50' if fixture=='smoke' else '0')
            name=f'{artifact}-{fixture}'
            start=time.time()
            with (ROOT/'logs'/f'{name}.tsv').open('w') as out, (ROOT/'logs'/f'{name}.trace').open('w') as err:
                result=subprocess.run(command,env=env,stdout=out,stderr=err,timeout=180)
            record={'name':name,'command':command,'exit_code':result.returncode,'seconds':time.time()-start,
                    'ops_sha256':hashlib.sha256((source/'ops.bin').read_bytes()).hexdigest(),
                    'input_sha256':hashlib.sha256((ROOT/f'{fixture}.tsv').read_bytes()).hexdigest()}
            results.append(record)
            (ROOT/'targeted-runs.json').write_text(json.dumps(results,indent=2)+'\n')
            print(name,result.returncode,round(record['seconds'],2),flush=True)
            assert result.returncode==0
            plain=command[:-1]+['-']
            check=subprocess.run(plain,env=env,capture_output=True,timeout=180,check=True)
            assert check.stdout==(ROOT/'logs'/f'{name}.tsv').read_bytes(), 'segmentation changed outputs'
            record['unsegmented_output_identical']=True
            record['binary_sha256']=hashlib.sha256(binary.read_bytes()).hexdigest()
            (ROOT/'targeted-runs.json').write_text(json.dumps(results,indent=2)+'\n')
if __name__=='__main__':
    main()
