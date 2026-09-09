"""Verify retained outcomes, freeze hashes, emitted counts, and an independent oracle."""
import csv
import hashlib
import json
import math
from pathlib import Path
import subprocess
ROOT=Path(__file__).resolve().parent
P=2**256-2**32-977
G=(0x79be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798,0x483ada7726a3c4655da4fbfc0e1108a8fd17b448a68554199c47d08ffb10d4b8)
def read(path):
    with path.open() as f:return list(csv.DictReader(f,delimiter='\t'))
def sha(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def add(a,b):
    if a is None:return b
    if b is None:return a
    x,y=a;u,v=b
    if x==u:
        if (y+v)%P==0:return None
        lam=3*x*x*pow(2*y,-1,P)%P
    else:lam=(v-y)*pow((u-x)%P,-1,P)%P
    rx=(lam*lam-x-u)%P
    return rx,(lam*(x-rx)-y)%P
def main():
    freeze=json.loads((ROOT/'candidate-freeze.json').read_text())
    for rel,digest in freeze['files_sha256'].items():assert sha(ROOT/rel)==digest,rel
    stream=json.loads(subprocess.check_output([str(ROOT/'target/release/stats_stream'),str(ROOT/'emit-window-16/ops.bin')]))
    assert stream['static_toffoli']==5188043
    (ROOT/'emitted-counts.json').write_text(json.dumps(stream,indent=2)+'\n')
    directory=ROOT/'emit-window-16/fresh-4096'
    rows=read(directory/'inputs.tsv');batches=read(directory/'batches.tsv')
    assert len(rows)==4096 and len({r['index'] for r in rows})==4096
    assert len(batches)==64 and sum(int(r['shots']) for r in batches)==4096
    failures={k:sum(int(r[k+'_failure']) for r in rows) for k in ['classical','phase','ancilla','any']}
    assert not any(failures.values())
    toffoli=sum(int(r['toffoli']) for r in batches)
    powers=[G]
    for _ in range(15):powers.append(add(powers[-1],powers[-1]))
    table={0:None}
    for row in rows:
        j=int(row['address'])
        if j not in table:
            a=None
            for i,q in enumerate(powers):
                if (j>>i)&1:a=add(a,q)
            table[j]=a
        r=tuple(int(row[k],16) for k in ['target_x','target_y'])
        a=tuple(int(row[k],16) for k in ['addend_x','addend_y'])
        expected=tuple(int(row[k],16) for k in ['expected_x','expected_y'])
        assert (r[1]**2-r[0]**3-7)%P==0
        assert a==(table[j] or (0,0))
        assert add(r,table[j])==expected
        assert tuple(int(row[k],16) for k in ['got_x','got_y'])==expected
    cells=[]
    for line in (ROOT/'logs/cells-w4-n1024-canonical.log').read_text().splitlines():
        if line.startswith('CELL '):cells.append(next(csv.reader([line[5:]])))
    canonical=[r for r in cells if int(r[2],16)<P and int(r[3],16)<P]
    assert len(canonical)==576
    assert all(not any(int(x) for x in r[6:12]) for r in canonical)
    component=(ROOT/'logs/component-w4-n1024-canonical.log').read_text()
    summaries=[x for x in component.splitlines() if x.startswith('COMPONENT ')]
    assert len(summaries)==2
    for line in summaries:
        assert all(f'{field}=0x0000000000000000' in line for field in ['output','output_p','denominator','phase','ancilla'])
    targeted={}
    for w in [4,16]:
        for corpus in ['zero-slope','smoke']:
            name=f'target-w{w}-{corpus}-canonical'
            cases=read(ROOT/'logs'/f'{name}.tsv')
            assert len(cases)==64
            assert all(r['classical']==r['phase']==r['ancilla']=='0' and r['interface_ok']=='true' for r in cases)
            targeted[name]=64
    result={'Q':1804,'static_toffoli':stream['static_toffoli'],'operations':stream['operations'],
            'fresh_inputs':4096,'toffoli_sum':toffoli,'mean_T':toffoli/4096,
            'Q_times_mean_T':1804*toffoli/4096,'failures':failures,
            'zero_failure_one_sided_95_bound':-math.expm1(math.log(.05)/4096),
            'independent_python_oracle_cases':4096,'canonical_cell_cases':576,
            'zero_component_cases':128,'targeted_passes':targeted,
            'freeze_files_unchanged':True,
            'scope':'Canonical replay and three exact coordinate subtractions. Finite value schedule, square, and remaining coordinate routines are inherited. Not an all-input full-point-addition proof.',
            'accounting_note':'The emitted stream is authoritative. REFERENCE_COUNTS in the builder includes 6144 temporary forward-construction Toffolis discarded when three inverse subtraction blocks are emitted. They are absent from ops.bin.'}
    (ROOT/'results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
