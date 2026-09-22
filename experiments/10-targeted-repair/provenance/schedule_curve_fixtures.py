"""Lift exact denominator counterexamples to supported affine point pairs."""
import csv
from pathlib import Path

ROOT=Path(__file__).resolve().parent
P=2**256-2**32-977
G=(0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798,
   0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8)
def add(a,b):
    if a is None:return b
    if b is None:return a
    x,y=a;u,v=b
    if x==u and (y+v)%P==0:return None
    slope=((3*x*x)*pow(2*y,-1,P) if a==b else (v-y)*pow(u-x,-1,P))%P
    z=(slope*slope-x-u)%P
    return z,(slope*(x-z)-y)%P
def main():
    rows=[]
    for denominator in [1,3,2**255]:
        a=None
        for j in range(1,16):
            a=add(a,G)
            x=(a[0]+denominator)%P
            rad=(x*x*x+7)%P
            y=pow(rad,(P+1)//4,P)
            if y*y%P!=rad:continue
            for yy in [y,(-y)%P]:
                r=(x,yy);out=add(r,a)
                if out is None or out[0]==a[0]:continue
                assert (r[0]-a[0])%P==denominator
                for lane in range(8):
                    rows.append([f'd{denominator}-y{int(yy==y)}-{lane}',*map(hex,(*r,*a,*out)),j])
            if len(rows)%16==0 and rows:break
    assert len(rows)==48
    with (ROOT/'repair-results/schedule-points.tsv').open('w') as f:
        w=csv.writer(f,delimiter='\t');w.writerow(['label','rx','ry','ax','ay','ex','ey','address']);w.writerows(rows)
    print('48 measurement lanes on six supported affine inputs; denominators 1,3,2^255; j<16')
if __name__=='__main__':main()
