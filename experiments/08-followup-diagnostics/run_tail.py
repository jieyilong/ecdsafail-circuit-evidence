"""Deterministic rejection-sampled denominator study, with bounded sample size."""
import argparse
import hashlib
import json
import subprocess
import time
from pathlib import Path
P=2**256-2**32-977
ROOT=Path(__file__).resolve().parent
def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--n',type=int,default=10000)
    args=parser.parse_args()
    assert 0<args.n<=10000000
    seed=b'qip-pingpong-round-tail-20260908-v1'
    data=ROOT/'denominators.bin'
    count=0; block=0
    with data.open('wb') as f:
        while count<args.n:
            raw=hashlib.shake_256(seed+block.to_bytes(8,'little')).digest(32000)
            block+=1
            for off in range(0,len(raw),32):
                if 0<int.from_bytes(raw[off:off+32],'big')<P:
                    f.write(raw[off:off+32]);count+=1
                    if count==args.n:break
    start=time.time()
    run=subprocess.run([str(ROOT/'round_tail'),str(data),str(args.n)],capture_output=True,text=True,check=True)
    result=json.loads(run.stdout)
    result.update(seconds=time.time()-start,seed=seed.decode(),generator='SHAKE256(seed || uint64_le(block)), 1000 big-endian words per block, reject zero and >=p',denominators_sha256=hashlib.sha256(data.read_bytes()).hexdigest())
    result['tail_counts']={str(b):sum(n for k,n in result['histogram'].items() if int(k)>b) for b in (704,736,768,800)}
    result['mean_rounds']=result['round_sum_censored']/args.n if result['censored_at_801']==0 else None
    (ROOT/f'tail-{args.n}.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='histogram'},indent=2))
if __name__=='__main__':main()
