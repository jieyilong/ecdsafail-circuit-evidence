"""Independently reconcile the frozen repair study and affine reference outputs."""
import csv
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
P=2**256-2**32-977
ORDER=0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141

def point(x,y):return int(x,16),int(y,16)
def add(a,b):
    if a==(0,0):return b
    if b==(0,0):return a
    x,y=a;u,v=b
    if x==u and (y+v)%P==0:return (0,0)
    slope=(3*x*x*pow(2*y,-1,P) if a==b else (v-y)*pow(u-x,-1,P))%P
    z=(slope*slope-x-u)%P
    return z,(slope*(x-z)-y)%P
def sha(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def main():
    study=ROOT/'fresh-zero-mask-100k'
    assert json.loads((study/'completed.json').read_text())['completed']
    plan=json.loads((study/'plan.json').read_text())
    totals=dict(n=0,toffoli=0,clifford=0,classical_failure=0,phase_failure=0,ancilla_failure=0,any_failure=0,identity=0,generic_exceptions=0)
    reports=[]
    for spec in plan['strata']:
        directory=study/f"stratum-{spec['index']}"/'checkpoint'
        rows=list(csv.DictReader((directory/'inputs.tsv').open(),delimiter='\t'))
        batches=list(csv.DictReader((directory/'batches.tsv').open(),delimiter='\t'))
        assert len(rows)==spec['n']
        assert sorted(int(r['index']) for r in rows)==list(range(spec['n']))
        assert len({int(b['batch']) for b in batches})==len(batches)
        count={k:0 for k in totals}
        for r in rows:
            a=point(r['target_x'],r['target_y']);b=point(r['addend_x'],r['addend_y'])
            for v in [a,b]:assert v==(0,0) or (v[1]*v[1]-v[0]**3-7)%P==0
            expected=add(a,b)
            assert expected==point(r['expected_x'],r['expected_y'])
            bad=int(point(r['got_x'],r['got_y'])!=expected)
            assert bad==int(r['classical_failure'])
            assert int(r['address'])==int(r['got_address'],16)
            assert int(r['any_failure'])==int(any(int(r[k]) for k in ['classical_failure','phase_failure','ancilla_failure']))
            count['n']+=1;count['identity']+=int(b==(0,0))
            count['generic_exceptions']+=int(b!=(0,0) and (a==(0,0) or a[0]==b[0] or expected==(0,0) or expected[0]==b[0]))
            for k in ['classical_failure','phase_failure','ancilla_failure','any_failure']:count[k]+=int(r[k])
        assert sum(int(b['shots']) for b in batches)==spec['n']
        count['toffoli']=sum(int(b['toffoli']) for b in batches)
        count['clifford']=sum(int(b['clifford']) for b in batches)
        for key,field in [('classical_failure','classical_failures'),('phase_failure','phase_failure_shots'),('ancilla_failure','ancilla_failure_shots'),('any_failure','any_failure_shots')]:
            assert count[key]==sum(int(b[field]) for b in batches)
        for k in count:totals[k]+=count[k]
        reports.append(dict(spec=spec,counts=count,input_sha256=sha(directory/'inputs.tsv'),batch_sha256=sha(directory/'batches.tsv')))
    assert totals['n']==100000
    mean=totals['toffoli']/totals['n'];success=1-totals['any_failure']/totals['n']
    result={'counts':totals,'Q':1419,'static_toffoli':1524503,'mean_T':mean,'QxT':1419*mean,'p_hat':success,'QxT_over_p_hat':1419*mean/success,
        'zero_failure_upper_95':1-0.05**(1/totals['n']) if totals['any_failure']==0 else None,
        'strata':reports,'verification':'complete unique indices, failure unions, restored address, batch totals, independent Python affine oracle',
        'scope':'fresh single-candidate nine-table test; structured counterexamples remain; not a coherent error bound'}
    (study/'verified-results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='strata'},indent=2))
if __name__=='__main__':main()
