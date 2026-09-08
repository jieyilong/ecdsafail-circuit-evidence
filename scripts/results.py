#!/usr/bin/env python3
"""Render readable result tables from the unmodified records; never rerun statistics."""
import argparse
import csv
from decimal import Decimal
import gzip
import io
import json
from pathlib import Path

from common import ROOT, FRESH, CANDIDATES, PROFILES, atomic_write, read_json, verify_original, verify_sources

LABELS={"original-pingpong":"Original ping-pong", "conservative-pingpong":"Conservative ping-pong", "jump2":"Jump-2"}


def tsv(path):
    opener=gzip.open if str(path).endswith(".gz") else open
    with opener(path,"rt",newline="") as f:
        return list(csv.DictReader(f,delimiter="\t"))


def csv_text(rows, fields=None):
    fields=fields or list(rows[0])
    f=io.StringIO(newline="")
    w=csv.DictWriter(f,fields,lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    return f.getvalue()


def table(headers, rows):
    return "\n".join(["| "+" | ".join(headers)+" |", "|"+"---|"*len(headers), *("| "+" | ".join(map(str,r))+" |" for r in rows)])


def fixed(value, digits=0):
    return f"{Decimal(str(value)):,.{digits}f}"


def render():
    verify_original()
    verify_sources()
    output={}
    report=read_json(FRESH/"analysis.json")
    corpus=read_json(FRESH/"corpus-spec.json")
    keys=("n","Q","static_toffoli","mean_T","mean_Clifford","QT","pass_fraction","retry_proxy","classical_failure","phase_failure","ancilla_failure","any_failure","identity_rows","identity_failures","extra_generic_exceptions","stratified_one_sided95_upper","zero_failure_pooled95_upper")
    rows=[]
    for name,old in CANDIDATES.items():
        r=report["circuits"][old]
        rows.append(dict(candidate=name, **{k:r[k] for k in keys}))
    output[FRESH/"summary.csv"]=csv_text(rows)
    readable=table(["Circuit","Cases","Q","Mean T","Q x T","Pass fraction","Any-channel failures"],
        [[LABELS[r["candidate"]],fixed(r["n"]),fixed(r["Q"]),fixed(r["mean_T"],5),fixed(r["QT"],5),r["pass_fraction"],r["any_failure"]] for r in rows])
    text="# Fresh Windowed Study: Results\n\nGenerated from the preserved [analysis JSON](analysis.json). Each circuit received the same 100,000 cases across nine table strata. Costs include failed inputs.\n\n"+readable+"\n\n"
    text+="## Failure Channels\n\n"+table(["Circuit","Classical","Phase","Ancilla","Any"],[[LABELS[r["candidate"]],r["classical_failure"],r["phase_failure"],r["ancilla_failure"],r["any_failure"]] for r in rows])+"\n\nChannels overlap. All three retained identity-addend cases pass in every circuit. There are no additional generic-domain exceptions.\n\n"
    text+="## Uncertainty and Scope\n\n"+table(["Circuit","Stratified upper 95% bound","Zero-event upper 95% bound"],[[LABELS[r["candidate"]],f"{r['stratified_one_sided95_upper']:.12g}","not applicable" if r["zero_failure_pooled95_upper"] is None else f"{r['zero_failure_pooled95_upper']:.12g}"] for r in rows])+"\n\nBounds above are probabilities, not percentages. They concern each circuit's allocation-weighted error rate under the stated sampling model. They are not simultaneous across the three circuits, all-input guarantees, or coherent-error bounds. `retry_proxy` in the CSV is only a per-call sensitivity calculation.\n\nThe [zero-payload probe](../05-zero-payload/RESULTS.md) finds representation and phase limitations on structured subroutine inputs. Its cases are separate from this frozen random study.\n\n"
    strata=[]
    totals=[]
    for s in corpus["strata"]:
        totals.append([s["name"],s["n"],*(report["circuits"][old]["strata"][s["name"]]["any_failure"] for old in CANDIDATES.values())])
        for name,old in CANDIDATES.items():
            r=report["circuits"][old]["strata"][s["name"]]
            strata.append(dict(stratum=s["name"],candidate=name,n=r["n"],mean_T=r["mean_T"],total_T=r["total_T"],total_Clifford=r["total_Clifford"],classical=r["classical_failure"],phase=r["phase_failure"],ancilla=r["ancilla_failure"],any=r["any_failure"],identity_rows=r["identity_rows"],wilson95_low=r["wilson95"][0],wilson95_high=r["wilson95"][1]))
    text+="## By Table Stratum\n\n"+table(["Stratum","Cases","Original ping-pong failures","Conservative failures","Jump-2 failures"],totals)+"\n\nFull precision: [summary.csv](summary.csv), [strata.csv](strata.csv), [paired.csv](paired.csv). The [failure index](failures.csv) identifies every failing case without omitting the successful rows from the underlying data.\n"
    output[FRESH/"RESULTS.md"]=text
    output[FRESH/"strata.csv"]=csv_text(strata)
    paired=[]
    for name,r in report["paired"].items():
        paired.append(dict(comparison=name,**{k:v for k,v in r.items() if k!="per_stratum"}))
    output[FRESH/"paired.csv"]=csv_text(paired)
    failures=[]
    for name in CANDIDATES:
        for s in corpus["strata"]:
            for r in tsv(FRESH/"runs"/name/s["name"]/"checkpoint/outcomes.tsv.gz"):
                if int(r["any_failure"]):
                    failures.append(dict(candidate=name,stratum=s["name"],index=int(r["index"]),classical=int(r["classical_failure"]),phase=int(r["phase_failure"]),ancilla=int(r["ancilla_failure"])))
    failures.sort(key=lambda r:(r["candidate"],r["stratum"],r["index"]))
    assert len(failures)==sum(r["any_failure"] for r in rows)
    output[FRESH/"failures.csv"]=csv_text(failures)
    overview="# Results at a Glance\n\nThis repository preserves the September 8, 2026 validation study. It does not replace the paper's older exploratory corpus or establish complete Shor correctness.\n\n"+readable+"\n\nThe conservative circuit adds 54 qubits and 11.12% mean Toffolis relative to original ping-pong. Against Jump-2, it uses 230 more qubits, 17.74% fewer mean Toffolis, and 1.46% lower raw Q x T. These are different empirical accuracy/resource points, not equal-error optima.\n\nSee [full results and uncertainty](experiments/02-fresh-windowed/RESULTS.md), [development results](experiments/01-development/RESULTS.md), and the [negative zero-payload findings](experiments/05-zero-payload/RESULTS.md).\n"
    output[ROOT/"RESULTS.md"]=overview
    development=ROOT/"experiments/01-development"
    dev=[]
    for name,old in PROFILES.items():
        r=read_json(development/"runs"/name/"summary.json")
        dev.append(dict(profile=name,original_profile=old,n=r["n"],Q=r["Q"],mean_T=r["mean_T"],QT=r["QT"],classical=r["classical_failure"],phase=r["phase_failure"],ancilla=r["ancilla_failure"],any=r["any_failure"]))
    output[development/"summary.csv"]=csv_text(dev)
    output[development/"RESULTS.md"]="# Development Study: Results\n\nThese are cumulative development configurations, not held-out accuracy estimates. All five results are retained.\n\n"+table(["Configuration","N","Q","Mean T","Classical","Phase","Ancilla","Any"],[[r["profile"],fixed(r["n"]),r["Q"],fixed(r["mean_T"],6),r["classical"],r["phase"],r["ancilla"],r["any"]] for r in dev])+"\n\nThe last profile was selected before fresh input generation. The shared phase-only case is documented in [experiment 04](../04-coordinate-phase/README.md). Settings are explained in the [original frozen protocol](../../sources/frozen-tools/bounded_qip/PROTOCOL.md).\n"
    eq=ROOT/"experiments/03-evaluator-equivalence"
    records=[]
    for name in ("official","auxiliary"):
        data=tsv(eq/"runs"/name/"checkpoint/inputs.tsv.gz")
        batches=tsv(eq/"runs"/name/"checkpoint/batches.tsv")
        records.append((name,data,batches))
    assert {r["index"]:r for r in records[0][1]} == {r["index"]:r for r in records[1][1]}
    normalize=lambda rows:{r["batch"]:{k:v for k,v in r.items() if k!="inputs_end_offset"} for r in rows}
    assert normalize(records[0][2])==normalize(records[1][2])
    equiv=[dict(evaluator=name,n=len(data),batches=len(batches),total_T=sum(int(r["toffoli"]) for r in batches),total_Clifford=sum(int(r["clifford"]) for r in batches),any_failure=sum(int(r["any_failure"]) for r in data)) for name,data,batches in records]
    output[eq/"summary.csv"]=csv_text(equiv)
    output[eq/"RESULTS.md"]="# Evaluator Equivalence: Results\n\nThe two evaluators agree on all 8,192 input/output/flag records and all 128 batches of integer gate totals. File completion order and byte offsets may differ. This is an agreement test for the mixed beta-one interface, not independent quantum verification.\n\n"+table(["Evaluator","Cases","Batches","Total Toffolis","Total counted Clifford","Any failures"],[[r[k] for k in equiv[0]] for r in equiv])+"\n"
    diag=ROOT/"experiments/04-coordinate-phase"
    traces=[]
    for line in (diag/"trace.log").read_text().splitlines():
        if line.startswith("QIP_PHASE_TRACE "):
            traces.append(dict(item.split("=",1) for item in line.split()[1:]))
    nonzero=[r for r in traces if int(r["delta"],16)]
    assert len(nonzero)==1 and nonzero[0]["phase"]=="tlm_coord_x_sub" and nonzero[0]["delta"]=="0x0000100000000000"
    output[diag/"stages.csv"]=csv_text(traces)
    case={name:next(r for r in tsv(development/"runs"/name/"checkpoint/inputs.tsv.gz") if r["index"]=="6828") for name in PROFILES}
    output[diag/"case-6828.json"]=json.dumps(case,indent=2,sort_keys=True)+"\n"
    output[diag/"RESULTS.md"]="# Coordinate-Phase Diagnosis\n\nThe original four profiles share a phase-only failure at development case **6828**, batch 106, lane 44. The trace first records its phase increment in the initial x subtraction. Subsequent stages have zero net phase delta on that lane, not a proof that every internal phase operation was correct.\n\n"+table(["Stage","Start op","End op","Phase delta","Cumulative phase"],[[r[k] for k in ("phase","start","end","delta","cumulative")] for r in traces])+"\n\nThe 19-bit coordinate-prefix check misses a lower-bit carry. Widening that check to 40 removes this development failure at about 72 extra mean Toffolis and unchanged Q. [All profile outcomes for this case](case-6828.json) are retained. The diagnostic log's inherited overall-shot denominator is not a sample-size claim for the selected-batch trace.\n"
    zero=ROOT/"experiments/05-zero-payload"
    probe=ROOT/"sources/trees/zero-payload-probe"
    zrows=[]
    for line in (probe/"zero-probe.log").read_text().splitlines():
        if line.startswith("ZERO_PAYLOAD "):
            r=dict(item.split("=",1) for item in line.split()[1:])
            zrows.append(dict(direction=r["direction"],n=64,noncanonical_zero=int(r["noncanonical_zero"]),phase_flags=int(r["phase_bad"]),denominator_mismatches=int(r["denominator_bad"]),dirty_ancillas=int(r["ancilla_bad"]),output_mask=r["output_mask"],phase_mask=r["phase_mask"],ancilla_mask=r["ancilla_mask"]))
    assert len(zrows)==2
    output[zero/"summary.csv"]=csv_text(zrows)
    output[zero/"RESULTS.md"]="# Zero-Payload Boundary Probe: Negative Results\n\nThis post-hoc diagnostic is separate from the frozen random study. Its 64 denominators have converged, width-safe value walks, but the modular payload is set to zero.\n\n"+table(["Direction","Cases","Output p instead of canonical zero","Phase flags","Denominator mismatches","Dirty ancillas"],[[r[k] for k in ("direction","n","noncanonical_zero","phase_flags","denominator_mismatches","dirty_ancillas")] for r in zrows])+"\n\nThe noncanonical words remain congruent to zero modulo the field modulus. Phase and representation categories overlap. These are subroutine observations, not full point-addition failure counts, an error-rate estimate, or evidence of all-input correctness. No repair was inserted into the frozen candidates.\n\n[Raw report](../../sources/trees/zero-payload-probe/zero-probe.log) | [Selected inputs and value-walk checks](../../sources/trees/zero-payload-probe/selection.json) | [Probe source and original instructions](../../sources/trees/zero-payload-probe/README.md)\n"
    return output


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--check",action="store_true")
    args=p.parse_args()
    generated=render()
    for path,content in generated.items():
        if args.check:
            assert path.read_text()==content, path
        else:
            path.parent.mkdir(parents=True,exist_ok=True)
            atomic_write(path,content)
    print(f"{'Verified' if args.check else 'Generated'} {len(generated)} readable result files.")
