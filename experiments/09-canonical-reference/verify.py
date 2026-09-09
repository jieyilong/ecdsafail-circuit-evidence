"""Read-only verification of recorded reference results, not circuit execution."""
import csv
import hashlib
import json
import math
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from analyze import add, P, G

def sha(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def data(path):return json.loads(path.read_text())
def rows(path):
    with path.open() as f:return list(csv.DictReader(f,delimiter='\t'))
def safe(rel):
    path=Path(rel)
    assert not path.is_absolute() and '..' not in path.parts,rel
    return ROOT/path

def verify():
    if not __debug__:raise RuntimeError('Assertions must remain enabled')
    original=data(ROOT/'provenance/original-manifest.json')
    for rel,digest in original.items():
        p=ROOT/'provenance/original-README.md' if rel=='README.md' else safe(rel)
        assert sha(p)==digest,rel
    current=data(ROOT/'manifest.json')
    for rel,digest in current.items():assert sha(safe(rel))==digest,rel
    freeze=data(ROOT/'candidate-freeze.json')
    omitted={'emit-window-16/ops.bin','target/release/eval_bounded'}
    for rel,digest in freeze['files_sha256'].items():
        if rel in omitted:
            assert not safe(rel).exists(),'large original artifact should be omitted'
        else:assert sha(safe(rel))==digest,rel
    receipt=data(ROOT/'logs/random-w16-n4096-canonical.json')
    assert receipt['exit_code']==0
    assert receipt['binary_sha256']==freeze['files_sha256']['target/release/eval_bounded']
    expected=data(ROOT/'results.json')
    stream=data(ROOT/'emitted-counts.json')
    assert sum(stream['kinds'])==stream['operations']==250012176
    assert stream['kinds'][13]+stream['kinds'][14]==stream['static_toffoli']==5188043
    emission=(ROOT/'logs/emit-w16-n1024-canonical.log').read_text()
    q,transient,count=map(int,re.search(r'REFERENCE_COUNTS Q=(\d+) static_toffoli=(\d+) ops=(\d+)',emission).groups())
    assert q==expected['Q']==1804 and transient-stream['static_toffoli']==6144
    ledger=ROOT/'emit-window-16/fresh-4096'
    inputs=rows(ledger/'inputs.tsv');batches=rows(ledger/'batches.tsv')
    manifest=dict(line.split('\t',1) for line in (ledger/'manifest.tsv').read_text().splitlines())
    assert manifest['seed']==freeze['seed']==receipt['env']['EVAL_SHARED_SEED']
    assert manifest['target_shots']=='4096' and manifest['window_bits']=='16'
    assert int(manifest['ops'])==stream['operations'] and int(manifest['qubits'])==q
    assert {int(r['index']) for r in inputs}==set(range(4096)) and len(inputs)==4096
    assert {int(r['batch']) for r in batches}==set(range(64)) and len(batches)==64
    channels=['classical','phase','ancilla','any']
    for r in inputs:
        assert int(r['batch'])==int(r['index'])//64
        assert int(r['got_address'],0)==int(r['address'])
        flags=[int(r[c+'_failure']) for c in channels]
        assert flags[3]==int(any(flags[:3])) and all(x in (0,1) for x in flags)
    for b in batches:
        case_rows=[r for r in inputs if r['batch']==b['batch']]
        assert len(case_rows)==int(b['shots'])==64
        for name,column in [('classical','classical_failures'),('phase','phase_failure_shots'),('ancilla','ancilla_failure_shots'),('any','any_failure_shots')]:
            assert sum(int(r[name+'_failure']) for r in case_rows)==int(b[column])
    toffoli=sum(int(b['toffoli']) for b in batches)
    failures={c:sum(int(r[c+'_failure']) for r in inputs) for c in channels}
    assert failures==expected['failures']==dict.fromkeys(channels,0)
    assert toffoli==expected['toffoli_sum']==21248476273
    assert toffoli/4096==expected['mean_T']
    assert q*toffoli/4096==expected['Q_times_mean_T']
    assert math.isclose(-math.expm1(math.log(.05)/4096),expected['zero_failure_one_sided_95_bound'],rel_tol=1e-12)
    # Independent Python group operations recheck every stored reference sum.
    powers=[G]
    for _ in range(15):powers.append(add(powers[-1],powers[-1]))
    table={0:None}
    for r in inputs:
        j=int(r['address']);assert 0<=j<2**16
        if j not in table:
            a=None
            for k,v in enumerate(powers):
                if (j>>k)&1:a=add(a,v)
            table[j]=a
        point=tuple(int(r[k],16) for k in ['target_x','target_y'])
        a=tuple(int(r[k],16) for k in ['addend_x','addend_y'])
        result=tuple(int(r[k],16) for k in ['expected_x','expected_y'])
        assert all(0<=x<P for x in point+a+result)
        assert (point[1]**2-point[0]**3-7)%P==0
        assert a==(table[j] or (0,0))
        assert add(point,table[j])==result
        assert tuple(int(r[k],16) for k in ['got_x','got_y'])==result
    cells=[next(csv.reader([line[5:]])) for line in (ROOT/'logs/cells-w4-n1024-canonical.log').read_text().splitlines() if line.startswith('CELL ')]
    canonical=[r for r in cells if int(r[2],16)<P and int(r[3],16)<P]
    assert len(canonical)==576 and len(cells)==700
    assert all(not any(map(int,r[6:12])) for r in canonical)
    components=[line for line in (ROOT/'logs/component-w4-n1024-canonical.log').read_text().splitlines() if line.startswith('COMPONENT ')]
    assert len(components)==2
    for line in components:assert all(f'{k}=0x0000000000000000' in line for k in ['output','output_p','denominator','phase','ancilla'])
    for w in [4,16]:
        for name in ['zero-slope','smoke']:
            tag=f'target-w{w}-{name}-canonical'
            cases=rows(ROOT/'logs'/f'{tag}.tsv');assert len(cases)==64
            assert all(r['classical']==r['phase']==r['ancilla']=='0' and r['interface_ok']=='true' for r in cases)
            record=data(ROOT/'logs'/f'{tag}.json')
            if w==16:assert record['ops_sha256']==freeze['files_sha256']['emit-window-16/ops.bin']
    # The unsuccessful replay-only attempt remains visible, not overwritten.
    for w,count in [(4,30),(16,38)]:
        cases=rows(ROOT/f'attempts/replay-only/logs/target-w{w}-zero-slope-canonical.tsv')
        assert sum(int(r['phase']) for r in cases)==count
    return {'status':'PASS','original_files_preserved':len(original),'pilot_rows':4096,
            'independent_python_oracle_cases':4096,'canonical_cell_cases':576,'noncanonical_cell_cases_retained':124,
            'component_cases':128,'targeted_lanes':256,'Q':q,'static_toffoli':stream['static_toffoli'],
            'mean_T':toffoli/4096,'failures':failures,'replay_only_failure_counts':[30,38],
            'omitted_original_artifacts':sorted(omitted),'fresh_circuit_execution':False,'stream_recounted':False,
            'scope':'Preserved record/source checks and independent classical arithmetic. Recorded stream counts and native hashes are receipts, not a new circuit execution or all-input proof.'}

if __name__=='__main__':print(json.dumps(verify(),indent=2))
