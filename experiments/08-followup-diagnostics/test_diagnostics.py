import csv
import hashlib
import os
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
import replay_model as m
from prepare_inputs import BETA,GX,GY,add

ROOT=Path(__file__).resolve().parent
EVIDENCE=Path(os.environ.get('ECDSAFAIL_EVIDENCE_ROOT',str(ROOT.parents[1]/'ecdsafail-circuit-evidence')))

class Diagnostics(unittest.TestCase):
    def test_supported_zero_slope(self):
        self.assertEqual(pow(BETA,3,m.P),1)
        self.assertNotEqual(BETA,1)
        slope=3*GX*GX*pow(2*GY,-1,m.P)%m.P
        double_x=(slope*slope-2*GX)%m.P
        double_y=(slope*(GX-double_x)-GY)%m.P
        for power in (1,2):
            r=(pow(BETA,power,m.P)*GX%m.P,GY)
            out=add(r,(GX,GY))
            self.assertNotEqual(r[0],GX)
            self.assertNotEqual(out[0],GX)
            self.assertNotEqual(r,(double_x,-double_y%m.P))
            self.assertEqual(out[1],-GY%m.P)

    def test_chunk_equality_positive_control(self):
        from collections import Counter
        events=Counter()
        s=1;t=m.M
        result,carry=m.chunks(s,t,40,events)
        self.assertEqual((result,carry),(0,1))
        self.assertEqual(events['chunk_equality'],1)
        self.assertEqual(events['chunk_predicate'],2)
        self.assertEqual(events['chunk_prefix'],1)

    def test_width_repair_of_smoke_cell(self):
        from collections import Counter
        witness=json.loads((ROOT/'targeted-analysis.json').read_text())['fold_witness']
        s=int(witness['source'],16);t=int(witness['target'],16)
        old,new=Counter(),Counter()
        oldout=m.ordinary(s,t,0,True,56,26,28,old)
        newout=m.ordinary(s,t,0,True,72,40,48,new)
        self.assertEqual(newout,(2*t+s)%m.P)
        self.assertEqual(oldout,newout-2**56)
        self.assertEqual(old['fold_width'],1)
        self.assertEqual(new['fold_width'],0)

    def test_gmp_against_python(self):
        import collections
        data=hashlib.shake_256(b'qip-pingpong-round-tail-20260908-v1'+bytes(8)).digest(32000)
        ds=[int.from_bytes(data[i:i+32],'big') for i in range(0,len(data),32)]
        ds += list(range(1,33)) + [m.P-1]
        with tempfile.NamedTemporaryFile() as f:
            f.write(b''.join(d.to_bytes(32,'big') for d in ds));f.flush()
            native=json.loads(subprocess.check_output([str(ROOT/'round_tail'),f.name,str(len(ds))]))
        hist=collections.Counter();bad=[0,0]
        for d in ds:
            result=m.walk(d,800)
            hist[str(result[4] or 801)]+=1
            bad[0]+=m.walk(d,704,4)[3] is not None
            bad[1]+=m.walk(d,736,20)[3] is not None
        self.assertEqual(dict(hist),native['histogram'])
        self.assertEqual(bad,[native['original_width_misses'],native['conservative_width_misses']])

    def test_unchanged_trusted_modules(self):
        original=EVIDENCE/'sources/trees/conservative-pingpong'
        for name in ['src/sim.rs','src/circuit.rs','src/weierstrass_elliptic_curve.rs','Cargo.toml','Cargo.lock','src/bin/eval_bounded.rs']:
            self.assertEqual((ROOT/'source'/name).read_bytes(),(original/name).read_bytes(),name)

    def test_segmented_equals_whole_stream(self):
        records=json.loads((ROOT/'targeted-runs.json').read_text())
        self.assertEqual(len(records),8)
        self.assertTrue(all(r['unsegmented_output_identical'] for r in records))

    def test_reproduce_prior_smoke(self):
        previous=EVIDENCE/'experiments/06-resource-accounting/receipts/runs/ablation-pingpong-product/smoke/inputs.tsv'
        with previous.open() as f:old=list(csv.DictReader(f,delimiter='\t'))
        with (ROOT/'logs/ablation-pingpong-product-smoke.tsv').open() as f:new=list(csv.DictReader(f,delimiter='\t'))
        for a,b in zip(old,new):
            self.assertEqual(int(a['got_x'],16),int(b['got_x'],16))
            self.assertEqual(int(a['got_y'],16),int(b['got_y'],16))
            for k in ['classical','phase','ancilla']:
                self.assertEqual(a[k+'_failure'],b[k])

if __name__=='__main__':unittest.main(verbosity=2)
