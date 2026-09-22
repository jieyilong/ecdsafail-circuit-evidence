"""Audit frozen artifact hashes and aggregate measured results only."""
import hashlib
import json
from pathlib import Path
import re

from full import ROOT


def main():
    work = Path(__file__).resolve().parents[1]
    dest = ROOT / "research/qip-oral-20260922/safegcd"
    ref = ROOT / "ecdsafail-circuit-evidence/experiments/09-canonical-reference/source"
    private = work / "matched_reference"
    def digest(path):
        h = hashlib.sha256()
        with path.open("rb") as f:
            for data in iter(lambda: f.read(1048576), b""):
                h.update(data)
        return h.hexdigest()
    changed = []
    for path in sorted((ref / "src").rglob("*.rs")):
        relative = path.relative_to(ref)
        if digest(path) != digest(private / relative):
            changed.append(str(relative))
    assert changed == ["src/point_add/pingpong_div.rs"]
    components = {}
    for label, directory in (("safegcd", "full-secp256k1"), ("pingpong_same_primitives", "matched-pingpong-secp256k1"),
                             ("pingpong_768_same_primitives", "matched-pingpong-768")):
        out = work / "safegcd_probe" / directory
        report = json.loads((out / "emission.json").read_text())
        assert digest(out / "div.kmx") == report["sha256"]
        assert sum(counts.get("CCX", 0) for counts in report["phase_gate_counts"].values()) == report["static_T"]
        components[label] = report
    shell = {}
    for label in ("canonical-safegcd", "canonical-pingpong"):
        out = work / "safegcd_probe" / (label + "-w4")
        emitted = json.loads((out / "emit-run.json").read_text())
        score = json.loads((out / "research-score.json").read_text())
        log = (out / "eval.log").read_text()
        builder = (out / "emit.log").read_text()
        bookkeeping = int(re.search(r"REFERENCE_COUNTS Q=\d+ static_toffoli=(\d+)", builder).group(1))
        static_t = emitted["serialized_counts"]["static_toffoli"]
        assert bookkeeping - static_t == 6144
        assert int(re.search(r"shots failing any channel:\s*(\d+)", log).group(1)) == 0
        assert digest(out / "ops.bin") == emitted["ops_sha256"]
        shell[label] = {"window_bits": 4, "samples": 64,
                        "Q": score["metrics"]["qubits"], "static_T_serialized": static_t,
                        "mean_executed_T_log_precision": float(re.search(r"avg executed Toffoli\s*:\s*([\d.]+)", log).group(1)),
                        "builder_bookkeeping_T": bookkeeping, "discarded_forward_bookkeeping_T": 6144,
                        "output_phase_ancilla_failures": [0, 0, 0],
                        "ops_sha256": emitted["ops_sha256"],
                        "matched_shell": True, "matched_arithmetic_lowering_between_shell_rows": False}
    source_hashes = {str(path.relative_to(work)): digest(path) for path in sorted((work / "safegcd_probe").glob("*.py"))}
    for relative in ("src/bin/safegcd_round_verify.rs", "matched_reference/src/point_add/pingpong_div.rs",
                     "matched_reference/src/point_add/safegcd_stream.rs", "matched_reference/src/point_add/canonical_replay.rs",
                     "matched_reference/src/point_add/trailmix_ludicrous/square.rs",
                     "matched_reference/src/point_add/trailmix_ludicrous/ec_add.rs"):
        source_hashes[relative] = digest(work / relative)
    report = {"status": "PASS", "label": "unoptimized references, not optimized safegcd",
              "components": components, "actual_w4_full_shells": shell,
              "frozen_reference_changed_existing_sources": changed,
              "square_coordinate_shell_and_qrom_unchanged": True,
              "source_sha256": source_hashes,
              "common_components": json.loads((dest / "common-component-results.json").read_text())}
    report["common_components"]["pingpong_denominator_3_rounds"] = components["pingpong_same_primitives"]["convergence_rounds"]["3"]
    report["pp768_diagnostic_failures"] = json.loads((dest / "pingpong-768-results.json").read_text())
    (dest / "full-results.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"status": "PASS", "component_Q_T": {k: [v["Q_static_allocated"], v["static_T"]] for k,v in components.items()},
                      "shells": shell}, indent=2))


if __name__ == "__main__":
    main()
