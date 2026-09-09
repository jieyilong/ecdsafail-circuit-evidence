"""Generate exact affine fixtures and preserve the prior smoke corpus verbatim."""
import csv
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
W = ROOT.parents[1]
P = 2**256 - 2**32 - 977
GX = 0x79be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798
GY = 0x483ada7726a3c4655da4fbfc0e1108a8fd17b448a68554199c47d08ffb10d4b8
BETA = pow(2, (P-1)//3, P)
assert BETA != 1 and pow(BETA, 3, P) == 1

def add(r, a):
    if a == (0,0):
        return r
    slope = (r[1]-a[1])*pow((r[0]-a[0]) % P, -1, P) % P
    x = (slope*slope-r[0]-a[0]) % P
    return x, (slope*(a[0]-x)-a[1]) % P

def write(name, rows):
    with (ROOT/name).open('w') as f:
        writer = csv.writer(f, delimiter='\t', lineterminator='\n')
        writer.writerow(['label','rx','ry','ax','ay','ex','ey','address'])
        writer.writerows(rows)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--evidence-root',type=Path,default=W/'ecdsafail-circuit-evidence')
    args=parser.parse_args()
    origin = args.evidence_root/'experiments/06-resource-accounting/receipts/runs/ablation-pingpong-product/smoke/inputs.tsv'
    old = list(csv.DictReader(origin.open(), delimiter='\t'))
    rows = [[r['index']]+[r[k] for k in ['target_x','target_y','addend_x','addend_y','expected_x','expected_y']]+[r['address']] for r in old]
    write('smoke.tsv', rows)
    fixtures = []
    for power in (1,2):
        a = (GX,GY)
        r = (pow(BETA,power,P)*GX % P,GY)
        out = add(r,a)
        assert all((y*y-x*x*x-7)%P==0 for x,y in (a,r,out))
        assert r[0] != a[0] and out[0] != a[0] and out[1] == -GY % P
        fixtures.append({'power':power,'r':list(map(hex,r)),'a':list(map(hex,a)),'out':list(map(hex,out))})
    write('zero-slope.tsv', [[f'zero-{power}-{i}']+f['r']+f['a']+f['out']+[1] for power,f in enumerate(fixtures,1) for i in range(32)])
    (ROOT/'fixture-proof.json').write_text(json.dumps({'beta':hex(BETA),'fixtures':fixtures,'original_smoke_sha256':hashlib.sha256(origin.read_bytes()).hexdigest()},indent=2)+'\n')

if __name__=='__main__':
    main()
