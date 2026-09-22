"""Generous small-prime checks for the primitive-matched comparison row."""
import json
import os
from pathlib import Path
import subprocess
import sys

from full import ROOT


def main():
    here = Path(__file__).resolve().parent
    binary = here.parent / "target/release/safegcd_round_verify"
    reports = []
    for p in (3, 5, 7, 11, 13, 17, 31, 61):
        out = here / ("matched-pingpong-p" + str(p))
        subprocess.run([sys.executable, "-B", str(here / "pingpong.py"), "--prime", str(p),
                        "--output", str(out)], check=True, stdout=subprocess.DEVNULL)
        for mode in ("div", "mul"):
            env = dict(os.environ, VERIFY_SCOPE="primitive_matched_pingpong_" + mode.upper())
            env.pop("VERIFY_REVERSE", None)
            if mode == "mul":
                env["VERIFY_REVERSE"] = "1"
            dest = out / (mode + "-results.json")
            subprocess.run([str(binary), str(out / "div.kmx"), str(out / (mode + "-vectors.txt")),
                            str(dest)], check=True, env=env, stdout=subprocess.DEVNULL)
            report = json.loads(dest.read_text())
            report["p"] = p
            reports.append(report)
        print("primitive-matched ping-pong DIV/MUL PASS p=" + str(p), flush=True)
    result = {"status": "PASS", "cases_each_direction": sum(r["forward_inverse_cases"] for r in reports[::2]),
              "budget": "8*n+16 for exhaustive listed small primes; no universal n256 claim",
              "results": reports}
    (ROOT / "research/qip-oral-20260922/safegcd/pingpong-small-results.json").write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
