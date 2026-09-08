#!/usr/bin/env python3
"""Inspect one complete fresh-study input and output without expanding all ledgers."""
import argparse
import csv
import gzip
import json
from common import ROOT, FRESH, CANDIDATES, read_json, verify_original


def find(path,index):
    with gzip.open(path,"rt",newline="") as f:
        for row in csv.DictReader(f,delimiter="\t"):
            if int(row["index"])==index:
                return row
    raise ValueError(f"Index {index} not found in {path}")


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--candidate",choices=CANDIDATES,required=True)
    p.add_argument("--stratum",required=True)
    p.add_argument("--index",type=int,required=True)
    args=p.parse_args()
    verify_original()
    strata={s["name"]:s for s in read_json(FRESH/"corpus-spec.json")["strata"]}
    if args.stratum not in strata or not 0<=args.index<strata[args.stratum]["n"]:
        p.error("Unknown stratum or out-of-range case index")
    row=find(FRESH/"data/corpus"/(args.stratum+".tsv.gz"),args.index)
    row.update(find(FRESH/"runs"/args.candidate/args.stratum/"checkpoint/outcomes.tsv.gz",args.index))
    for got,expected in (("got_x","expected_x"),("got_y","expected_y"),("got_address","address")):
        if row[got]=="=":
            row[got]=hex(int(row[expected])) if expected=="address" else row[expected]
    print(json.dumps(dict(candidate=args.candidate,stratum=args.stratum,record=row),indent=2))
