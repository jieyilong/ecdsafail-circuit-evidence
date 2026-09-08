"""Read-only reconstruction from bounded experiment receipts (stdlib only)."""
from collections import Counter, defaultdict
import csv
import json


def rows(path):
    with path.open() as f:
        return list(csv.DictReader(f, delimiter="\t"))


def category(phase):
    if phase.startswith("pp_"):
        return phase
    if phase.startswith("square") or phase == "tlm_square":
        return "square"
    if "qrom" in phase or "split_" in phase:
        return "qrom"
    if "coord" in phase or "recover" in phase:
        return "coordinates"
    suffix = "initial" if phase.endswith("_initial") else "ordinary"
    if "codec" in phase or "decode" in phase:
        return "jump2_codec_" + suffix
    if "apply" in phase:
        return "jump2_payload_" + suffix
    if "gcd" in phase:
        return "jump2_value_" + suffix
    return "other_" + phase


def reconstruct(root):
    results = {}
    for folder in sorted((root / "runs").iterdir()):
        r = json.loads((folder / "result.json").read_text())
        if (folder / "stream.json").exists():
            r["stream"] = json.loads((folder / "stream.json").read_text())
            stream = r["stream"]
            kinds = {int(k):v for k,v in stream["kind_counts"].items()}
            assert set(kinds) <= set(range(18))
            assert sum(kinds.values()) == stream["operations"] == r["operations"]
            assert kinds.get(13, 0)+kinds.get(14, 0) == stream["static_toffoli"]
        if (folder / "allocator.tsv").exists():
            alloc = dict(line.split("\t",1) for line in (folder / "allocator.tsv").read_text().splitlines())
            r["allocator"] = {k:int(v) if v.isdigit() else v for k,v in alloc.items()}
            ledger, phases = defaultdict(Counter), defaultdict(Counter)
            previous_end = 0
            for p in rows(folder / "phases.tsv"):
                assert int(p["start"]) == previous_end
                assert int(p["end"])-int(p["start"]) == int(p["ops"])
                previous_end = int(p["end"])
                for key in ("ops", "ccx", "ccz", "hmr", "reset"):
                    ledger[category(p["phase"])][key] += int(p[key])
                    phases[p["phase"]][key] += int(p[key])
                phases[p["phase"]]["intervals"] += 1
            for p in list(ledger.values())+list(phases.values()):
                p["static_toffoli"] = p["ccx"]+p["ccz"]
            r["category_ledger"], r["phase_ledger"] = dict(ledger), dict(phases)
            r["raw_operations"] = sum(p["ops"] for p in ledger.values())
            r["raw_static_toffoli"] = sum(p["static_toffoli"] for p in ledger.values())
            assert r["raw_operations"] == int(alloc["precompiler_ops"])
            owners = rows(folder / "owners.tsv")
            peaks = {p["peak_phase"]:int(p["active"]) for p in owners}
            for phase, peak in peaks.items():
                own = [p for p in owners if p["peak_phase"] == phase]
                assert {int(p["active"]) for p in own} == {peak}
                assert len({p["op_index"] for p in own}) == 1
                assert sum(int(p["count"]) for p in own) == peak
            r["live_peak"] = max(peaks.values())
            assert r["live_peak"] == int(alloc["peak_qubits"]) == int(alloc["max_wire_plus_one"])
            r["phase_live_peaks"] = peaks
            r["peak_owners"] = [p for p in owners if int(p["active"]) == r["live_peak"]]
        results[folder.name] = r
    checks = []
    for name, r in results.items():
        if name+"-unchanged" in results and "stream" in r:
            other = results[name+"-unchanged"]
            assert r["compressed_sha256"] == other["compressed_sha256"]
            checks.append(dict(name=name, check="instrumentation_stream_identity", passed=r["stream"] == other.get("stream")))
        if name+"-count" in results and "raw_static_toffoli" in r:
            other = results[name+"-count"]
            for key in ("raw_static_toffoli", "raw_operations", "live_peak"):
                checks.append(dict(name=name, check="count_only_"+key, emitted=r[key], counted=other.get(key), passed=r[key] == other.get(key)))
    smoke, corpus = {}, None
    for name in results:
        folder = root / "runs" / name / "smoke"
        if not (folder / "inputs.tsv").exists():
            continue
        outcomes, batches = rows(folder / "inputs.tsv"), rows(folder / "batches.tsv")
        inputs = [{k:r[k] for k in ("batch", "index", "address", "target_x", "target_y", "addend_x", "addend_y", "expected_x", "expected_y")} for r in outcomes]
        corpus = inputs if corpus is None else corpus
        assert inputs == corpus, "common input mismatch"
        n = sum(int(r["shots"]) for r in batches)
        assert len(outcomes) == n == 64
        failed = [r for r in outcomes if r["any_failure"] == "1"]
        for r in outcomes:
            assert int(r["any_failure"]) == max(int(r[k]) for k in ("classical_failure", "phase_failure", "ancilla_failure"))
        smoke[name] = dict(n=n, mean_executed_toffoli=sum(int(r["toffoli"]) for r in batches)/n,
                          static_cost_is_separate=True, identity_rows=sum(int(r["address"]) == 0 for r in outcomes),
                          failures={k:sum(int(r[k]) for r in outcomes) for k in ("classical_failure", "phase_failure", "ancilla_failure", "any_failure")},
                          nonidentity_failures=sum(int(r["address"]) != 0 for r in failed), failed_indices=[int(r["index"]) for r in failed])
    controls = {}
    for square in ("legacy", "product"):
        names = [f"ablation-{b}-{square}" for b in ("legacy", "pingpong")]
        a,b = [results[name] for name in names]
        settings = []
        for name in names:
            settings.append({k:v for k,v in (line.split("\t",1) for line in (root / "runs" / name / "emitter-settings.tsv").read_text().splitlines()) if not k.startswith("ACCOUNTING_")})
        differences = {k:[settings[0].get(k),settings[1].get(k)] for k in set(settings[0])|set(settings[1]) if settings[0].get(k) != settings[1].get(k)}
        controls[square] = dict(effective_settings_differences=differences,
                               square_category_identical=a["category_ledger"]["square"] == b["category_ledger"]["square"],
                               static_toffoli_reduction=a["raw_static_toffoli"]-b["raw_static_toffoli"],
                               compiler="No post-emission pass in either path; built-in emitter specializations retained.")
    return dict(results=results, checks=checks, smoke=smoke, ablation_controls=controls,
                scope="Raw emitter category costs are static CCX+CCZ, not mean executed T. Owner snapshots are simultaneous allocator leases, not proof of clean qubits.")
