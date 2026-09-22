"""Check standalone canonical coefficient maps, not only reachable payloads."""
import json
import os
from pathlib import Path
import random
import subprocess

from full import Full, ROOT, SECP256K1_P
from scalar import coefficient_forward


def main():
    here = Path(__file__).resolve().parent
    reports = []
    for p in (3, 5, 7, 11, 17, 31, SECP256K1_P):
        c = Full(p)
        tag = "secp256k1" if p == SECP256K1_P else str(p)
        out = here / ("coeff-" + tag)
        out.mkdir(exist_ok=True)
        (out / "coeff.kmx").write_text("\n".join(
            op[0] + " " + " ".join("q" + str(q) for q in op[1:]) for op in c.coeff_ops) + "\n")
        if p < 128:
            pairs = [(a, b) for a in range(p) for b in range(p)]
        else:
            rng = random.Random(202609221358)
            pairs = [(a, b) for a in (0, 1, 2, p//2, p//2+1, p-2, p-1)
                     for b in (0, 1, 2, p//2, p//2+1, p-2, p-1)]
            pairs += [(rng.randrange(p), rng.randrange(p)) for _ in range(256)]
        def encode(pair, record):
            bits = ["0"] * c.size
            for reg, value in zip((c.a, c.b), pair):
                for j, q in enumerate(reg):
                    bits[q] = str((value >> j) & 1)
            bits[c.e], bits[c.s] = map(str, record)
            return "".join(bits)
        with (out / "vectors.txt").open("w") as stream:
            for record in ((0, 0), (1, 0), (1, 1)):
                for pair in pairs:
                    expected = coefficient_forward(pair, record, p)
                    stream.write(encode(pair, record) + " " + encode(expected, record) + "\n")
        dest = out / "results.json"
        env = dict(os.environ, VERIFY_SCOPE="canonical_coefficient_round")
        env.pop("VERIFY_REVERSE", None)
        subprocess.run([str(here.parent / "target/release/safegcd_round_verify"), str(out / "coeff.kmx"),
                        str(out / "vectors.txt"), str(dest)], env=env, check=True, stdout=subprocess.DEVNULL)
        result = json.loads(dest.read_text())
        result["prime"] = str(p)
        reports.append(result)
        print("coefficient maps PASS p=" + tag, flush=True)
    (ROOT / "research/qip-oral-20260922/safegcd/coefficient-gate-results.json").write_text(
        json.dumps({"status": "PASS", "results": reports}, indent=2) + "\n")


if __name__ == "__main__":
    main()
