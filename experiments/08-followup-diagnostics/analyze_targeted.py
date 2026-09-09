"""Verify source-model correspondence to emitted intermediate states and final outputs."""
import csv
import hashlib
import json
from pathlib import Path
import replay_model as model
ROOT=Path(__file__).resolve().parent
def rows(path):return list(csv.DictReader(path.open(),delimiter='\t'))
def main():
    summaries={}
    for path in sorted((ROOT/'logs').glob('*.tsv')):
        got=rows(path)
        summaries[path.stem]={k:sum(int(r[k]) for r in got) for k in ['classical','phase','ancilla']}
        summaries[path.stem]['all_interfaces_preserved']=all(r['interface_ok']=='true' for r in got)
    fixture=rows(ROOT/'smoke.tsv')[50]
    a={k:int(fixture[k],16) for k in ['rx','ry','ax','ay','ex','ey']}
    dx=(a['rx']-a['ax'])%model.P
    dy=(a['ry']-a['ay'])%model.P
    lam=dy*pow(dx,-1,model.P)%model.P
    mul_den=(a['ax']-a['ex'])%model.P
    trace=[]
    division_50=model.replay(dx,dy,guarded=False)
    multiplication=model.replay(mul_den,lam,inverse=True,guarded=False,trace=trace)
    raw=(ROOT/'logs/ablation-pingpong-product-smoke.trace').read_text().splitlines()
    coefficients=[int(r.split('\t')[3],16) for r in raw if r.startswith('COEFFICIENT\tpp_replay_inverse_ordinary\t')]
    numerators=[int(r.split('\t')[4],16) for r in raw if r.startswith('TRACE\tpp_replay_inverse_ordinary\t')]
    assert len(coefficients)==len(numerators)==702
    for (k,x,y),gx,gy in zip(trace[:702],coefficients,numerators):
        assert x==gx and y==gy,(k,hex(x),hex(gx),hex(y),hex(gy))
    k=271
    tape,*_=model.walk(mul_den,704,4)
    before=next(t for t in trace if t[0]==k+1)
    after=next(t for t in trace if t[0]==k)
    target,source=before[1],before[2]
    sign=1-tape[k]
    raw_sum=((2*target)&model.M)^(model.M if sign else 0)
    raw_sum+=source
    overflow=raw_sum>>256
    raw_word=raw_sum&model.M
    d=target>>255
    correction=(overflow-d if sign else overflow+d)*model.F
    folded=model.low_add(raw_word,correction,56)
    exact_fold=(raw_word+correction)&model.M
    assert folded!=exact_fold
    assert abs(folded-exact_fold)==2**56
    assert after[1]==folded^(model.M if sign else 0)
    value=(2*target+(-source if sign else source))%model.P
    witness={'round_zero_based':k,'source':hex(source),'target':hex(target),'sign':sign,
             'raw_word':hex(raw_word),'correction':correction,'folded_56':hex(folded),
             'full_fold':hex(exact_fold),'fold_difference':str(folded-exact_fold),
             'expected_cell_output':hex(value),'actual_cell_output':hex(after[1]),
             'matched_ordinary_round_boundaries':702}
    # Model the coordinate shell exactly, excluding unsupported identity-addend rows.
    comparisons=[]
    for profile,artifact in [(False,'original-w4'),(True,'conservative-w4')]:
        for corpus in ['smoke','zero-slope']:
            expected=rows(ROOT/f'{corpus}.tsv')
            got=rows(ROOT/'logs'/f'{artifact}-{corpus}.tsv')
            for r,g in zip(expected,got):
                a={k:int(r[k],16) for k in ['rx','ry','ax','ay','ex','ey']}
                if (a['ax'],a['ay'])==(0,0):continue
                dx=(a['rx']-a['ax'])%model.P
                division=model.replay(dx,(a['ry']-a['ay'])%model.P,guarded=profile)
                slope=int(division['output'],16)
                d=(a['rx']+2*a['ax']-slope*slope)%model.P
                multiplication=model.replay(d,slope,inverse=True,guarded=profile)
                output=((a['ax']-d)%model.P,(int(multiplication['output'],16)-a['ay'])%model.P)
                assert output==(int(g['got_x'],16),int(g['got_y'],16)),(artifact,corpus,r['label'])
                comparisons.append([artifact,corpus,r['label']])
    result={'summaries':summaries,'fixture_50_division':division_50,
            'fixture_50_multiplication':model.replay(mul_den,lam,inverse=True,guarded=False),
            'fold_witness':witness,'complete_coordinate_model_matches':len(comparisons),
            'scope':'Source-word model verified against 702 emitted inverse-round boundaries for fixture 50 and 246 final point outputs. No general phase-model equivalence claim.'}
    (ROOT/'targeted-analysis.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
