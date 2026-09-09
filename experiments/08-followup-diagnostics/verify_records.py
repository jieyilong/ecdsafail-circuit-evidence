"""Read-only integrity and numeric consistency verification, no external paths."""
import csv
import hashlib
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
def main():
    manifest=json.loads((ROOT/'manifest.json').read_text())
    for rel,digest in manifest.items():
        path=ROOT/rel
        assert path.is_relative_to(ROOT) and '..' not in Path(rel).parts
        assert hashlib.sha256(path.read_bytes()).hexdigest()==digest,rel
    t=json.loads((ROOT/'tail-10000000.json').read_text())
    assert sum(t['histogram'].values())==t['n']==10000000
    assert sum(int(k)*n for k,n in t['histogram'].items())==t['round_sum_censored']
    for budget,count in t['tail_counts'].items():
        assert count==sum(n for k,n in t['histogram'].items() if int(k)>int(budget))
    assert t['tail_counts']=={'704':1535,'736':6,'768':0,'800':0}
    g=json.loads((ROOT/'guards-11112.json').read_text())
    assert len(g['strata'])==9
    assert sum(x['evaluated'] for x in g['strata'].values())==99997
    assert sum(x['skipped'] for x in g['strata'].values())==3
    assert g['events']==g['affected_inputs']=={}
    a=json.loads((ROOT/'targeted-analysis.json').read_text())
    for name,summary in a['summaries'].items():
        with (ROOT/'logs'/f'{name}.tsv').open() as f:rows=list(csv.DictReader(f,delimiter='\t'))
        assert len(rows)==64
        for k in ['classical','phase','ancilla']:assert summary[k]==sum(int(r[k]) for r in rows)
        assert all(r['interface_ok']=='true' for r in rows)
    witness=a['fold_witness']
    assert int(witness['folded_56'],16)-int(witness['full_fold'],16)==-2**56
    assert witness['matched_ordinary_round_boundaries']==702
    records=json.loads((ROOT/'targeted-runs.json').read_text())
    assert len(records)==8 and all(r['unsegmented_output_identical'] for r in records)
    print(f'PASS: {len(manifest)} file hashes, targeted lane summaries, tail histogram, and guard records')
if __name__=='__main__':main()
