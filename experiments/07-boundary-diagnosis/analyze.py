#!/usr/bin/env python3
"""Summarize raw diagnostic records, without changing checks or dropping failures."""
import csv
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
P = 2**256 - 2**32 - 977


def read_cells(path):
    lines = path.read_text().splitlines()
    header = next(s.removeprefix("CELL_HEADER ") for s in lines if s.startswith("CELL_HEADER "))
    return list(csv.DictReader([header] + [s.removeprefix("CELL ") for s in lines if s.startswith("CELL ")]))


def main():
    results = {}
    for path in sorted((ROOT / "logs").glob("cells-*.log")):
        groups = defaultdict(list)
        for row in read_cells(path):
            scope = "canonical" if max(int(row["source"], 16), int(row["target"], 16)) < P else "includes_p"
            groups[row["kernel"], scope].append(row)
        summary = []
        for (kernel, scope), rows in groups.items():
            row = {"kernel": kernel, "scope": scope, "cases": len(rows)}
            for check in ["word_bad", "field_bad", "phase", "ancilla", "source_bad", "control_bad"]:
                row[check] = sum(int(r[check]) for r in rows)
                failures = [r for r in rows if int(r[check])]
                if failures:
                    row[f"first_{check}"] = min(failures, key=lambda r: (int(r["source"], 16) + int(r["target"], 16), int(r["sign"])))
            row["peak"] = int(rows[0]["peak"])
            row["emitted_toffoli"] = int(rows[0]["emitted_toffoli"])
            summary.append(row)
        results[path.stem] = summary
    (ROOT / "cell-summary.json").write_text(json.dumps(results, indent=2) + "\n")
    with (ROOT / "cell-summary.csv").open("w") as out:
        columns = ["variant", "kernel", "scope", "cases", "word_bad", "field_bad", "phase", "ancilla", "source_bad", "control_bad", "peak", "emitted_toffoli"]
        writer = csv.DictWriter(out, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for variant, rows in results.items():
            writer.writerows(dict(r, variant=variant) for r in rows)
    for variant, rows in results.items():
        print(variant)
        for r in rows:
            print(r["kernel"], r["scope"], r["cases"], "word/field/phase/anc", *(r[c] for c in ["word_bad", "field_bad", "phase", "ancilla"]))
            if "first_field_bad" in r:
                f = r["first_field_bad"]
                print(" first field failure:", {k: f[k] for k in ["sign", "source", "target", "got", "expected"]})


if __name__ == "__main__":
    main()
