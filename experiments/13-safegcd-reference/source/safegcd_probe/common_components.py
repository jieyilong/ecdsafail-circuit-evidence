"""Frozen-stream common fresh corpus, including long ping-pong examples."""
import hashlib
import json
import os
from pathlib import Path
import random
import subprocess

from full import Full, ROOT, SECP256K1_P
from pingpong import PingPong


def main():
    here = Path(__file__).resolve().parent
    p = SECP256K1_P
    rng = random.Random(202609221404)
    cases = [(z, x) for z in (1, 2, 3, 0xd3, 1 << 255, p-1, p-2, (p+1)//2)
             for x in (0, 1, 2, p-1, p-2)]
    cases += [(rng.randrange(1, p), rng.randrange(p)) for _ in range(88)]
    digest = hashlib.sha256(b"".join(z.to_bytes(32, "big") + x.to_bytes(32, "big") for z, x in cases)).hexdigest()
    reports = []
    for name, c, directory in (("safegcd", Full(p), "full-secp256k1"),
                                ("pingpong", PingPong(p, 1536), "matched-pingpong-secp256k1")):
        if name == "pingpong":
            convergence = {str(z): c.convergence(z) for z, _ in cases}
        out = here / directory
        for mode in ("div", "mul"):
            vectors = out / ("common-" + mode + "-vectors.txt")
            c.fixtures(vectors, cases, mode == "mul")
            env = dict(os.environ, VERIFY_SCOPE="common_" + name + "_" + mode)
            env.pop("VERIFY_REVERSE", None)
            if mode == "mul":
                env["VERIFY_REVERSE"] = "1"
            dest = out / ("common-" + mode + "-results.json")
            subprocess.run([str(here.parent / "target/release/safegcd_round_verify"),
                            str(out / "div.kmx"), str(vectors), str(dest)],
                           check=True, env=env, stdout=subprocess.DEVNULL, timeout=90)
            reports.append(json.loads(dest.read_text()))
            print(name + " " + mode + " common corpus PASS", flush=True)
    result = {"status": "PASS", "seed": 202609221404, "common_cases_each": len(cases),
              "corpus_sha256": digest, "reports": reports,
              "pingpong_max_observed": max(convergence.values()),
              "pingpong_denominator_3_rounds": convergence[str(3)],
              "pingpong_0xd3_rounds": convergence[str(0xd3)],
              "pingpong_2power255_rounds": convergence[str(1 << 255)],
              "pingpong_1536_round_budget": "conditional, not a universal bound"}
    (ROOT / "research/qip-oral-20260922/safegcd/common-component-results.json").write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
