"""Diagnostic only: previously fixed PP768 horizon, unchanged common corpus."""
import json
import os
from pathlib import Path
import subprocess
from full import ROOT

here = Path(__file__).resolve().parent
out = here / "matched-pingpong-768"
reports = []
for mode in ("div", "mul"):
    original = here / "matched-pingpong-secp256k1" / ("common-" + mode + "-vectors.txt")
    width = json.loads((out / "emission.json").read_text())["Q_static_allocated"]
    vectors = out / ("common-" + mode + "-vectors.txt")
    # Public wires are the same first 512; every remaining expected wire is zero.
    with vectors.open("w") as f:
        for line in original.read_text().splitlines():
            a, b = line.split()
            f.write(a[:512] + "0" * (width-512) + " " + b[:512] + "0" * (width-512) + "\n")
    env = dict(os.environ, VERIFY_REPORT_FAILURES="1", VERIFY_SCOPE="fixed_PP768_" + mode)
    env.pop("VERIFY_REVERSE", None)
    if mode == "mul": env["VERIFY_REVERSE"] = "1"
    dest = out / (mode + "-failures.json")
    subprocess.run([str(here.parent / "target/release/safegcd_round_verify"), str(out / "div.kmx"), str(vectors), str(dest)], env=env, check=True)
    reports.append(json.loads(dest.read_text()))
(ROOT / "research/qip-oral-20260922/safegcd/pingpong-768-results.json").write_text(json.dumps({"fixed_preexisting_horizon":768, "same_common_corpus":True, "reports":reports}, indent=2)+"\n")
