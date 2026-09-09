"""Post-hoc ordinary replay guard diagnostics on actual frozen affine inputs.

Uses raw noncanonical payload words and their correlations. Counts predicate
disagreements, not measured phase failures. Does not model the coordinate shell's
internal carry guards, specialized seed phases, or general coherent error.
"""
import argparse
from collections import Counter
import csv
import gzip
import hashlib
import json
from pathlib import Path
import time
import replay_model as model
ROOT=Path(__file__).resolve().parent
CORPUS=ROOT.parents[1]/'ecdsafail-circuit-evidence/experiments/02-fresh-windowed/data/corpus'
def main():
    p=argparse.ArgumentParser();p.add_argument('--per-stratum',type=int,default=1000)
    p.add_argument('--evidence-root',type=Path,default=ROOT.parents[1]/'ecdsafail-circuit-evidence')
    args=p.parse_args()
    total=Counter(); affected=Counter(); strata={}; witnesses=[]; provenance={}; start=time.time()
    corpus=args.evidence_root/'experiments/02-fresh-windowed/data/corpus'
    paths=sorted(corpus.glob('*.tsv.gz'))
    assert len(paths)==9, 'expected all nine frozen corpus strata'
    for path in paths:
        provenance[path.name]=hashlib.sha256(path.read_bytes()).hexdigest()
        with gzip.open(path,'rt') as f: rows=list(csv.DictReader(f,delimiter='\t'))
        rows=sorted(rows,key=lambda r:int(r['index']))[:args.per_stratum]
        count=0;local=Counter();skipped=0
        for r in rows:
            rx,ry,ax,ay=[int(r[k],16) for k in ['target_x','target_y','addend_x','addend_y']]
            if (ax,ay)==(0,0):skipped+=1;continue
            dx=(rx-ax)%model.P
            if not dx:skipped+=1;continue
            div=model.replay(dx,(ry-ay)%model.P)
            slope=int(div['output'],16)
            den=(rx+2*ax-slope*slope)%model.P
            if not den:skipped+=1;continue
            mul=model.replay(den,slope,inverse=True)
            events=Counter(div['events'])+Counter(mul['events'])
            total.update(events);affected.update(events.keys());local.update(events.keys());count+=1
            if events and len(witnesses)<20:witnesses.append({'stratum':path.stem,'index':r['index'],'division':div,'multiplication':mul})
        strata[path.name]={'evaluated':count,'skipped':skipped,'affected':dict(local)}
        result={'scope':__doc__,'per_stratum_prefix':args.per_stratum,'strata':strata,'events':dict(total),
                'affected_inputs':dict(affected),'witnesses':witnesses,'input_hashes':provenance,'seconds':time.time()-start}
        (ROOT/f'guards-{args.per_stratum}.json').write_text(json.dumps(result,indent=2)+'\n')
        print(path.name,count,dict(local),round(time.time()-start,2),flush=True)
if __name__=='__main__':main()
