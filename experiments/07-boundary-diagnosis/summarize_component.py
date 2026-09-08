#!/usr/bin/env python3
"""Derive component receipts and selected first-fixture paths from raw traces."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main():
    path = ROOT / "logs/component-final.log"
    summaries = {}
    excerpts = []
    for line in path.read_text().splitlines():
        if line.startswith(("COMPONENT ", "PRERESET ", "POSTRESET ")):
            kind, direction, *fields = line.split()
            row = {k: int(v, 0) for k, v in (s.split("=", 1) for s in fields)}
            summaries.setdefault(direction, {})[kind] = row
        if line.startswith("TRACE "):
            parts = line.split()
            fields = dict(p.split("=", 1) for p in parts[2:])
            keep = fields["label"] in ["value_walk_done", "halving_done", "divide_negated", "multiply_seeded", "coefficient_before_free", "coefficient_after_free"]
            keep |= parts[1] == "Divide" and fields["lane"] == "4" and int(fields["round"]) <= 3
            if keep:
                excerpts.append(line)
    for d, sections in summaries.items():
        comp = sections["COMPONENT"]
        pre, post = sections["PRERESET"], sections["POSTRESET"]
        sections["derived"] = {
            "output_p_count": comp["output_p"].bit_count(),
            "phase_count": comp["phase"].bit_count(),
            "coefficient_prereset_nonzero_count": pre["coefficient_nonzero"].bit_count(),
            "reset_phase_xor": hex(pre["phase"] ^ post["phase"]),
            "reset_phase_xor_count": (pre["phase"] ^ post["phase"]).bit_count(),
            "remaining_restore_phase_xor": hex(post["phase"] ^ comp["phase"]),
            "output_p_and_phase": (comp["output_p"] & comp["phase"]).bit_count(),
            "representation_or_phase_count": (comp["output_p"] | comp["phase"]).bit_count(),
            "mean_executed_toffoli": comp["toffoli_sum64"] / 64,
        }
    (ROOT / "component-summary.json").write_text(json.dumps(summaries, indent=2) + "\n")
    (ROOT / "trace-excerpts.log").write_text("\n".join(excerpts) + "\n")
    print(json.dumps({k: v["derived"] for k, v in summaries.items()}, indent=2))


if __name__ == "__main__":
    main()
