#!/usr/bin/env python3
"""Read-only portable evidence verification; Python 3.11+, standard library only."""
import csv
import difflib
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import sys
import tarfile
import tomllib

ROOT = Path(__file__).resolve().parent
P = 2**256 - 2**32 - 977
EXCLUDED = {"manifest.json", "metadata/stage-verification.json"}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(rel):
    return json.loads((ROOT / rel).read_text())


def require(condition, message):
    if not condition:
        raise ValueError(message)


def source_hashes():
    return {str(p.relative_to(ROOT / "source/src")): sha(p)
            for p in sorted((ROOT / "source/src").rglob("*")) if p.is_file()}


def cells(tag):
    lines = (ROOT / f"logs/cells-final-{tag}.log").read_text().splitlines()
    header = next(s.removeprefix("CELL_HEADER ") for s in lines if s.startswith("CELL_HEADER "))
    return list(csv.DictReader([header] + [s.removeprefix("CELL ") for s in lines if s.startswith("CELL ")]))


def check_manifest():
    manifest = read_json("manifest.json")
    actual = {str(p.relative_to(ROOT)) for p in ROOT.rglob("*") if p.is_file()
              and str(p.relative_to(ROOT)) not in EXCLUDED and "__pycache__" not in p.parts}
    require(actual == set(manifest["files"]), "package file inventory differs from stage manifest")
    for rel, record in manifest["files"].items():
        path = ROOT / rel
        require(not path.is_symlink() and path.resolve().is_relative_to(ROOT), f"nonlocal artifact: {rel}")
        require(sha(path) == record["sha256"] and path.stat().st_size == record["bytes"], f"artifact mismatch: {rel}")
    return {"files": len(actual), "manifest_sha256": sha(ROOT / "manifest.json")}


def check_provenance():
    lineage = read_json("provenance/lineage.json")
    for rel, expected in lineage["original_manifest_anchors"].items():
        require(sha(ROOT / rel) == expected, f"original provenance anchor changed: {rel}")
    original = read_json("provenance/original/artifacts-sha256.json")["files"]
    for rel, origin in lineage["copied_artifacts"].items():
        require(original[origin["original_path"]]["sha256"] == origin["sha256"], f"unanchored copy: {rel}")
        if rel not in lineage["adapted_files"]:
            require(sha(ROOT / rel) == origin["sha256"], f"copied original changed: {rel}")
    frozen = read_json("provenance/original/frozen-sha256.json")
    for candidate in frozen:
        directory = ROOT / "provenance/upstream-files" / candidate
        for path in directory.rglob("*"):
            if path.is_file():
                require(sha(path) == frozen[candidate][str(path.relative_to(directory))], f"upstream excerpt mismatch: {path.name}")
    require(read_json("provenance/original/test-results.json") == {"tests": 8, "failures": 0, "errors": 0, "successful": True}, "original test receipt mismatch")
    original_report = (ROOT / "provenance/original/REPORT.md").read_text()
    correction = read_json("provenance/editorial-correction.json")
    expected = original_report
    for replacement in correction["replacements"]:
        require(expected.count(replacement["before"]) == 1, "ambiguous scientific wording correction")
        expected = expected.replace(replacement["before"], replacement["after"], 1)
    corrected_report = (ROOT / correction["corrected_report"]).read_text()
    require(expected == corrected_report, "undocumented scientific report change")
    require(sha(ROOT / correction["original_report"]) == correction["original_scientific_report_sha256"], "original report anchor changed")
    require(sha(ROOT / correction["corrected_report"]) == correction["corrected_scientific_report_sha256"], "corrected scientific report hash differs")
    scientific_patch = "".join(difflib.unified_diff(original_report.splitlines(keepends=True), corrected_report.splitlines(keepends=True),
                                                  fromfile="a/REPORT.md", tofile="b/REPORT.md"))
    require(scientific_patch == (ROOT / "patches/scientific-wording-correction.diff").read_text(), "scientific correction diff differs")
    report = (ROOT / "REPORT.md").read_text()
    patch = "".join(difflib.unified_diff(corrected_report.splitlines(keepends=True), report.splitlines(keepends=True),
                                       fromfile="a/REPORT.md", tofile="b/REPORT.md"))
    require(patch == (ROOT / "patches/portable-report.diff").read_text(), "portable report patch differs")
    def scientific_sections(text):
        return {s.split("\n", 1)[0]: s for s in text.split("\n## ") if s.split("\n", 1)[0] not in ["Scope And Integrity", "Reproduction"]}
    require(scientific_sections(corrected_report) == scientific_sections(report), "undocumented scientific report text changed during packaging")
    return {"recorded_original_receipt_tests": 8, "original_upstream_trees_reread": False,
            "editorial_correction": "35 nonzero coefficient registers; fixture 4 confirmed p; aggregate word-p count unmeasured.",
            "status": "Bundled artifacts matched recorded upstream hashes; original external trees are not required or freshly verified."}


def check_sources():
    lineage = read_json("provenance/lineage.json")
    frozen = read_json("provenance/original/frozen-sha256.json")
    base = frozen["zero-payload-probe"]
    changes = set(lineage["source_changes"])
    additions = set(lineage["source_additions"])
    staged = {str(p.relative_to(ROOT / "source")): p for p in (ROOT / "source").rglob("*") if p.is_file()}
    require(set(staged) == set(base) | additions, "copied source tree has missing or unexpected files")
    for rel, path in staged.items():
        if rel not in changes | additions:
            require(sha(path) == base[rel], f"unapproved source change: {rel}")
    patch = []
    for rel in sorted(changes | additions):
        before = []
        if rel in changes:
            old = ROOT / "provenance/upstream-files/zero-payload-probe" / rel
            before = old.read_text().splitlines(keepends=True)
        patch.extend(difflib.unified_diff(before, staged[rel].read_text().splitlines(keepends=True), fromfile=f"a/{rel}", tofile=f"b/{rel}"))
    require("".join(patch) == (ROOT / "patches/diagnostic-source.diff").read_text(), "preserved source patch does not reconstruct the staged changes")
    for rel in read_json("provenance/original/integrity.json")["protected_files_unchanged"]:
        require(sha(staged[rel]) == base[rel], f"protected simulator/reference/evaluator changed: {rel}")
    require(source_hashes() == read_json("provenance/original/integrity.json")["copied_source_hashes"], "source differs from original diagnostic source hashes")
    probe = (ROOT / "provenance/upstream-files/zero-payload-probe/src/point_add/pingpong_div.rs").read_text()
    conservative = (ROOT / "provenance/upstream-files/conservative-pingpong/src/point_add/pingpong_div.rs").read_text()
    require(probe[:probe.index("pub(crate) fn report_zero_payload_probe()")].rstrip() == conservative.rstrip(), "published probe changed conservative arithmetic")
    receipts = list((ROOT / "provenance/original-run-receipts").glob("*.json"))
    require(len(receipts) == 9, "need all nine final run receipts")
    for path in receipts:
        receipt = json.loads(path.read_text())
        require(receipt["returncode"] == 0 and receipt["source_sha256"] == source_hashes(), f"run receipt source mismatch: {path.name}")
    return {"source_files": len(staged), "explicit_changed_files": sorted(changes), "added_files": sorted(additions), "protected_checks_unchanged": True}


def check_results():
    original = (ROOT / "source/zero-probe.log").read_text()
    current = (ROOT / "logs/baseline-final.log").read_text()
    require(re.findall(r"ZERO_PAYLOAD[^\n]+", original) == re.findall(r"ZERO_PAYLOAD[^\n]+", current), "published zero-probe masks differ")
    component = read_json("component-summary.json")
    raw = (ROOT / "logs/component-final.log").read_text()
    require(raw.count("SPLIT_EQ_UNSPLIT") == 2, "missing split/unsplit equivalence receipts")
    for direction, output, phase, pre in [("Divide", 28, 19, 0), ("Multiply", 46, 26, 35)]:
        record = component[direction]
        derived, comp = record["derived"], record["COMPONENT"]
        require((derived["output_p_count"], derived["phase_count"], derived["coefficient_prereset_nonzero_count"]) == (output, phase, pre), f"component counts differ: {direction}")
        require(comp["output"] == comp["output_p"] and comp["denominator"] == comp["ancilla"] == 0, f"component value/cleanup mismatch: {direction}")
        require(derived["remaining_restore_phase_xor"] == "0x0", "unlocalized restoration phase")
        fields = dict(s.split("=", 1) for s in next(s for s in raw.splitlines() if s.startswith(f"COMPONENT {direction} ")).split()[2:])
        require({k: int(v, 0) for k, v in fields.items()} == comp, "derived component summary differs from raw log")
    require(component["Multiply"]["derived"]["reset_phase_xor_count"] == 23, "nonzero reset count changed")
    correction = read_json("provenance/editorial-correction.json")
    require(correction["coefficient_prereset_nonzero_count"] == 35 and correction["coefficient_prereset_word_p_count"] is None, "nonzero count was reinterpreted as a word-p count")
    require(sha(ROOT / "component-summary.json") == correction["component_summary_sha256_unchanged"], "component-summary metadata changed")
    fixture4 = next(line for line in raw.splitlines() if line.startswith("TRACE Multiply lane=4 ") and "label=coefficient_before_free " in line)
    coefficient_word = dict(s.split("=", 1) for s in fixture4.split()[2:])["regs"].split(":")[0]
    require(int(coefficient_word, 16) == P, "fixture 4 is not confirmed p in the retained trace")
    for variant in ["baseline", "full_compare", "full_width"]:
        rows = cells(variant)
        require(len(rows) == 700, f"cell grid truncated: {variant}")
        require(all(int(r[k]) == 0 for r in rows for k in ["ancilla", "source_bad", "control_bad"]), "cell final preservation checks differ")
        witness = (ROOT / f"logs/witnesses-final-{variant}.log").read_text()
        require(witness.count("PHASE_RULE_CHECK seeds=8 lanes_per_seed=64 matched=true") == 6, "phase-rule tests missing")
        require(witness.count("UNCANCELLED ") == witness.count("PAIRED "), "input-dependent phase pairing missing")
        first = witness.split("WITNESS fused_halve", 1)[0]
        require(first.count("UNCANCELLED ") == (3 if variant == "baseline" else 2), "widening negative witness changed")
        require("hot=506 op=2799" in first and "PAIRED hot=506 zero_controls_vs_witness phase=0xffffffff00000000" in first, "precise carry-equality witness missing")
        for summary in read_json("cell-summary.json")[f"cells-final-{variant}"]:
            selected = [r for r in rows if r["kernel"] == summary["kernel"] and
                        ("canonical" if max(int(r["source"], 16), int(r["target"], 16)) < P else "includes_p") == summary["scope"]]
            require(len(selected) == summary["cases"], "summary case count differs from final raw grid")
            for flag in ["word_bad", "field_bad", "phase", "ancilla", "source_bad", "control_bad"]:
                require(sum(int(r[flag]) for r in selected) == summary[flag], "summary differs from final raw grid")
    full = next(r for r in cells("full_width") if r["kernel"] == "halve" and r["target"] == "0x1" and r["sign"] == "0")
    require(int(full["field_bad"]) == 1 and int(full["got"], 16) - int(full["expected"], 16) == 2**255, "full-width halving negative result changed")
    return {"original_masks_reproduced": True, "nonzero_multiply_prereset": 35, "reset_phase_changes": 23,
            "scope": "Raw emitted cells and isolated components, not an entire-kernel zero-error claim."}


def check_local_regression():
    rows = cells("baseline")
    for control in (0, 1):
        for value in (0, 1, P - 1):
            row = next(r for r in rows if r["kernel"] == "canonical_negate_exact" and int(r["target"], 16) == value and int(r["sign"]) == control)
            require(all(int(row[k]) == 0 for k in ["word_bad", "field_bad", "phase", "ancilla", "source_bad", "control_bad"]), "canonical local boundary regression changed")
    negative = [r for r in rows if r["kernel"] == "canonical_negate_exact" and int(r["target"], 16) == P]
    require(any(int(r["phase"]) for r in negative), "out-of-contract p negative test missing")
    text = (ROOT / "logs/local_regression-baseline.log").read_text()
    require("total_shots=9200" in text and "peak=514 emitted_toffoli=777 toffoli_sum=7148400 mean_toffoli=777" in text, "local regression count or cost changed")
    return {"evaluations": 9200, "peak_qubits": 514, "toffoli_per_input": 777, "integrated_into_replay": False}


def check_walk():
    # Import is local-only; prevent cache writes during portable verification.
    sys.dont_write_bytecode = True
    from value_walk import check
    data = read_json("value-walk.json")
    selection = read_json("source/selection.json")["selected"]
    expected = [check(int(r["denominator"], 16)) for r in selection]
    require(data["fixtures"] == expected, "exact fixture precheck does not reproduce")
    require([r["convergence"] for r in expected] == [r["rounds"] for r in selection], "published convergence counts differ")
    require(all(r["first_bad"] is None for r in expected), "fixture value walk overflow")
    small = [check(d) for d in range(1, 257)] + [check(P - 1)]
    require(data["small_integer_and_p_minus_one_prechecks"] == small and all(r["first_bad"] is not None for r in small), "small-denominator negative prechecks differ")
    return {"valid_fixture_count": 64, "small_denominator_width_failures_retained": 257}


def check_dependencies():
    record = read_json("dependencies/vendor-manifest.json")
    archive = ROOT / "dependencies/vendor.tar.gz"
    require(sha(archive) == record["sha256"], "vendored dependency archive changed")
    locked = tomllib.loads((ROOT / "source/Cargo.lock").read_text())["package"]
    checksums = {(p["name"], p["version"]): p["checksum"] for p in locked if "source" in p}
    require(len(checksums) == record["crate_count"] == len(record["crates"]), "vendored dependency coverage differs from lockfile")
    with tarfile.open(archive, "r:gz") as tar:
        members = {m.name: m for m in tar.getmembers()}
        for name, member in members.items():
            path = PurePosixPath(name)
            require(not path.is_absolute() and ".." not in path.parts and path.parts[0] == "vendor" and (member.isfile() or member.isdir()), "unsafe vendor archive entry")
        for crate in record["crates"]:
            key = crate["name"], crate["version"]
            require(checksums[key] == crate["registry_checksum"], "dependency is not anchored in original Cargo.lock")
            prefix = f"vendor/{crate['directory']}/"
            checksum = json.load(tar.extractfile(members[prefix + ".cargo-checksum.json"]))
            require(checksum["package"] == checksums[key], "Cargo vendor checksum differs from lockfile")
    return {"vendored_crates": record["crate_count"], "network_needed": False}


def verify():
    checks = {}
    for name, fn in [
        ("stage_manifest", check_manifest), ("recorded_provenance", check_provenance),
        ("source_patch_and_protected_checks", check_sources), ("retained_results", check_results),
        ("local_regression", check_local_regression), ("exact_value_walk", check_walk),
        ("offline_dependencies", check_dependencies),
    ]:
        checks[name] = fn()
    return {"schema": 1, "successful": True, "portable_check_groups": len(checks),
            "mode": "Read-only verification of this staged package; no network or original-workspace lookup.",
            "checks": checks}


if __name__ == "__main__":
    try:
        print(json.dumps(verify(), indent=2))
    except Exception as error:
        print(json.dumps({"successful": False, "error": str(error)}, indent=2))
        raise SystemExit(1)
