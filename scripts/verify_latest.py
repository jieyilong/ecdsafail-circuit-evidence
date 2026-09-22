"""Read-only verification of the September 22 targeted-repair supplement."""
import csv
import gzip
import io
import json
import math
from pathlib import Path
import re

from common import ROOT, read_json, safe_path, sha, ensure_checks_enabled

EXPERIMENT=ROOT/'experiments/10-targeted-repair'
P=2**256-2**32-977
G=(0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798,
   0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8)

def rows(path):
    opener=gzip.open if path.suffix=='.gz' else open
    with opener(path,'rt',newline='') as stream:return list(csv.DictReader(stream,delimiter='\t'))

def add(a,b):
    if a==(0,0):return b
    if b==(0,0):return a
    x,y=a;u,v=b
    if x==u and (y+v)%P==0:return (0,0)
    slope=(3*x*x*pow(2*y,-1,P) if a==b else (v-y)*pow(u-x,-1,P))%P
    z=(slope*slope-x-u)%P
    return z,(slope*(x-z)-y)%P

def mul(k,a):
    out=(0,0)
    while k:
        if k&1:out=add(out,a)
        a=add(a,a);k>>=1
    return out

def verify_ledger(records,batches,n,beta,oracle=True):
    assert sorted(int(r['index']) for r in records)==list(range(n)), 'Missing or duplicate cases'
    assert sorted(int(b['batch']) for b in batches)==list(range((n+63)//64)), 'Missing or duplicate batches'
    totals={k:0 for k in ['n','toffoli','clifford','classical_failure','phase_failure','ancilla_failure','any_failure','identity','generic_exceptions']}
    grouped={}
    table=None
    if oracle:
        base=mul(beta,G);table=[(0,0)]
        for _ in range(65535):table.append(add(table[-1],base))
    for r in records:
        idx=int(r['index']);j=int(r['address']);batch=int(r['batch'])
        assert batch==idx//64 and 0<=j<65536
        point=lambda x,y:(int(r[x],16),int(r[y],16))
        a=point('target_x','target_y');b=point('addend_x','addend_y')
        expected=point('expected_x','expected_y');got=point('got_x','got_y')
        for v in [a,b,expected]:
            assert all(0<=x<P for x in v)
            assert v==(0,0) or (v[1]*v[1]-v[0]**3-7)%P==0
        if oracle:
            assert b==table[j], 'Wrong selected addend'
            assert expected==add(a,b), 'Wrong reference result'
        flags={k:int(r[k]) for k in ['classical_failure','phase_failure','ancilla_failure','any_failure']}
        assert all(v in [0,1] for v in flags.values())
        assert flags['classical_failure']==int(got!=expected)
        assert flags['any_failure']==int(any(flags[k] for k in ['classical_failure','phase_failure','ancilla_failure']))
        assert int(r['got_address'],16)==j
        totals['n']+=1;totals['identity']+=int(b==(0,0))
        totals['generic_exceptions']+=int(b!=(0,0) and (a==(0,0) or a[0]==b[0] or expected==(0,0) or expected[0]==b[0]))
        for k,v in flags.items():totals[k]+=v
        grouped.setdefault(batch,[]).append(flags)
    mapping={'classical_failure':'classical_failures','phase_failure':'phase_failure_shots','ancilla_failure':'ancilla_failure_shots','any_failure':'any_failure_shots'}
    for b in batches:
        cases=grouped[int(b['batch'])]
        assert len(cases)==int(b['shots'])
        for flag,key in mapping.items():assert sum(c[flag] for c in cases)==int(b[key])
        for k in ['toffoli','clifford']:totals[k]+=int(b[k])
    return totals

def verify_latest(oracle=True):
    ensure_checks_enabled()
    previous=read_json(ROOT/'provenance/v1.3.0-publication-manifest.json')['files']
    preserved={k:v for k,v in previous.items() if k.startswith(('experiments/','sources/','supporting/','provenance/')) and k!='provenance/publication-manifest.json'}
    for k,v in preserved.items():assert sha(safe_path(ROOT,k))==v,k
    imports=read_json(ROOT/'provenance/v1.4.0-import-map.json')['files']
    for item in imports:
        path=safe_path(ROOT,item['published']);assert sha(path)==item['published_sha256'],str(path)
        if item['gzip']:
            import hashlib
            assert hashlib.sha256(gzip.decompress(path.read_bytes())).hexdigest()==item['original_sha256']
    study=EXPERIMENT/'fresh-study';freeze=read_json(study/'freeze.json')
    for name,digest in freeze['source'].items():assert sha(safe_path(EXPERIMENT/'source',name))==digest,name
    summary=read_json(study/'verified-results.json');total={k:0 for k in summary['counts']}
    for spec in read_json(study/'plan.json')['strata']:
        checkpoint=study/f"stratum-{spec['index']}"/'checkpoint'
        count=verify_ledger(rows(checkpoint/'inputs.tsv.gz'),rows(checkpoint/'batches.tsv'),spec['n'],int(spec['beta'],16),oracle)
        for k,v in count.items():total[k]+=v
    assert total==summary['counts']
    assert total['n']==100000 and total['any_failure']==0 and total['identity']==4
    assert summary['Q']==1419 and summary['static_toffoli']==1524503
    assert summary['mean_T']==total['toffoli']/total['n']
    assert math.isclose(summary['QxT'],1419*summary['mean_T'],rel_tol=1e-14)
    assert summary['p_hat']==1-total['any_failure']/total['n']
    assert math.isclose(summary['QxT_over_p_hat'],summary['QxT']/summary['p_hat'],rel_tol=1e-14)
    assert math.isclose(summary['zero_failure_upper_95'],1-0.05**(1/total['n']),rel_tol=1e-12)
    diagnostics=EXPERIMENT/'diagnostics'
    for width in [4,16]:
        for fixture in ['zero-slope','smoke']:
            data=rows(diagnostics/f'masked_chunk_coords-w{width}'/(fixture+'.stdout'))
            assert len(data)==64
            assert all(int(r[k])==0 for r in data for k in ['classical','phase','ancilla'])
            assert all(r['interface_ok']=='true' for r in data)
    failed=rows(diagnostics/'schedule-points-w4.tsv')
    assert len(failed)==48 and sum(int(r['classical']) for r in failed)==48
    assert sum(int(r['phase']) for r in failed)==25
    assert 'qubits=1402' in (diagnostics/'mixed-repair/zero-slope.stderr').read_text()
    safegcd=read_json(ROOT/'experiments/13-safegcd-reference/common-component-results.json')['reports']
    assert [(r['Q'],r['static_T_forward']) for r in safegcd]==[(3300,7501932),(3300,7501932),(3088,12574712),(3088,12574712)]
    negative=read_json(ROOT/'experiments/13-safegcd-reference/pingpong-768-results.json')['reports']
    assert all(r['any_failures']==12 and r['cases']==128 for r in negative)
    return {'status':'PASS','fresh_cases':total['n'],'Q':summary['Q'],'mean_T':summary['mean_T'],'any_failures':0,
        'preserved_v13_scientific_files':len(preserved),'imported_files':len(imports),'independent_table_and_affine_oracle':oracle,
        'scope':'Recorded evidence/source verification and classical oracle, not a new quantum-circuit run or all-input proof'}

if __name__=='__main__':print(json.dumps(verify_latest(),indent=2))
