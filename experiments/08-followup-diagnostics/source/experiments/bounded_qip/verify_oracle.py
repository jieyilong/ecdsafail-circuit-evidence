"""Independently reconstruct case inputs/sums with OpenSSL through cryptography."""
import argparse
from functools import lru_cache
import hashlib
import json
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric import ec
from analyze import read_case, sha

ORDER = int("FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141",16)


def point(scalar):
    scalar %= ORDER
    if scalar == 0:
        return (0,0)
    p = ec.derive_private_key(scalar,ec.SECP256K1()).public_key().public_numbers()
    return p.x,p.y


def verify_case(case):
    rows,manifest,_ = read_case(case)
    n=len(rows)
    beta=int(manifest["qip_table_beta"],16)
    seed=manifest["seed"]
    shake=hashlib.shake_256(b"quantum_ecc-shared-comparison-v1"+seed.encode())
    buffer=b""
    offset=0
    def take(count):
        nonlocal buffer,offset
        end=offset+count
        if len(buffer)<end:
            buffer=shake.digest(end+65536)
        data=buffer[offset:end]
        offset=end
        return data
    @lru_cache(maxsize=None)
    def addend(j):
        return point(beta*j)
    rejected_identity=rejected_equal_x=0
    index=0
    while index<n:
        a=int.from_bytes(take(32),"little")
        target=point(a)
        if target==(0,0):
            rejected_identity+=1
            continue
        j=int.from_bytes(take(8),"little")&65535
        add=addend(j)
        if j!=0 and target[0]==add[0]:
            rejected_equal_x+=1
            continue
        expected=point(a+beta*j)
        row=rows[index]
        assert int(row["address"])==j, (index,"address")
        assert tuple(int(row[k],16) for k in ("target_x","target_y"))==target,(index,"target")
        assert tuple(int(row[k],16) for k in ("addend_x","addend_y"))==add,(index,"addend")
        assert tuple(int(row[k],16) for k in ("expected_x","expected_y"))==expected,(index,"expected")
        index+=1
    return dict(verified_cases=n,beta=hex(beta),seed=seed,random_bytes_consumed=offset,
        rejected_identity_accumulators=rejected_identity,rejected_equal_x=rejected_equal_x,
        oracle="cryptography/OpenSSL secp256k1 scalar multiplication",mismatches=0)


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("path",type=Path)
    p.add_argument("--final",action="store_true")
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    if args.final:
        spec=json.loads((args.path/"fresh-corpus-spec.json").read_text())
        results={}
        for s in spec["strata"]:
            results[s["name"]]=verify_case(args.path/"results/pingpong_conservative"/s["name"])
        result=dict(freeze_sha256=sha(args.path/"freeze.json"),strata=results,
                    verified_cases=sum(v["verified_cases"] for v in results.values()),mismatches=0)
    else:
        result=verify_case(args.path)
    args.output.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print(json.dumps(result,indent=2,sort_keys=True))
