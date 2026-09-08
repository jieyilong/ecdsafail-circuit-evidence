"""Emit isolated replay cells from a pinned checkout, without changing that checkout."""
import argparse
import csv
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import tarfile

COMMIT = "897dda2b0cf267151ecd973252d2a5078cbf1b63"
ROOT = Path(__file__).resolve().parents[1]
DRIVER = r'''
#[allow(dead_code)]
#[path = "../point_add/mod.rs"]
mod point_add;
#[allow(unused_imports)]
use quantum_ecc::{circuit, sim, weierstrass_elliptic_curve};
fn main() { point_add::paper_replay_probe(); }
'''
PROBE = r'''
pub(crate) fn paper_replay_probe() {
    std::env::set_var("DIALOG_GCD_FOLD_MAJ1", "1");
    std::env::remove_var("SUB4_PINGPONG_LOW56_FOLD");
    println!("cell,static_toffoli,peak_qubits,workspace,operations");
    for name in ["unfused_inverse", "range_matched_unfused", "fused_inverse", "fused_forward"] {
        std::env::remove_var("SUB4_PINGPONG_LOW56_FOLD");
        if name == "range_matched_unfused" {
            std::env::set_var("SUB4_PINGPONG_LOW56_FOLD", "1");
        }
        let mut b = B::new();
        let source = b.alloc_qubits(N);
        let target = b.alloc_qubits(N);
        let sign = b.alloc_qubit();
        if name == "unfused_inverse" || name == "range_matched_unfused" {
            mod_double_pm(&mut b, &target);
            signed_mod_add_pm(&mut b, sign, &source, &target);
        } else if name == "fused_inverse" {
            signed_mod_double_add_pm_fused(&mut b, sign, &source, &target);
        } else {
            signed_mod_add_pm_halve_fused(&mut b, sign, &source, &target);
        }
        assert_eq!(b.active_qubits, (2 * N + 1) as u32);
        let count = b.ops.iter().filter(|op| matches!(op.kind, OperationType::CCX | OperationType::CCZ)).count();
        println!("{name},{count},{},{},{}", b.peak_qubits, b.peak_qubits - (2 * N + 1) as u32, b.ops.len());
    }
}
'''


def run():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-checkout", type=Path, required=True,
                        help="Existing challenge Git checkout containing the pinned commit")
    parser.add_argument("--work-dir", type=Path, required=True,
                        help="New directory for the temporary instrumented source and Cargo build")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--online", action="store_true", help="Allow Cargo to fetch dependencies")
    args = parser.parse_args()
    work = args.work_dir.resolve()
    work.mkdir(parents=True, exist_ok=False)
    archive = subprocess.check_output(["git", "-C", str(args.source_checkout), "archive", COMMIT,
                                       "Cargo.toml", "Cargo.lock", "src"])
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        for entry in tar.getmembers():
            assert not PurePosixPath(entry.name).is_absolute()
            assert ".." not in PurePosixPath(entry.name).parts
            assert entry.isfile() or entry.isdir()
        tar.extractall(work, filter="data")
    source = work / "src/point_add/pingpong_div.rs"
    original = source.read_bytes()
    source.write_text(original.decode() + PROBE)
    module = work / "src/point_add/mod.rs"
    module.write_text(module.read_text() + "\npub(crate) use pingpong_div::paper_replay_probe;\n")
    (work / "src/bin/paper_replay_probe.rs").write_text(DRIVER)
    env = {k: v for k, v in os.environ.items() if not k.startswith(("SUB4_", "DIALOG_", "KAL_", "ROUND84_", "SQUARE_", "WINDOWED_"))}
    cmd = ["cargo", "run", "--release", "--locked"]
    if not args.online:
        cmd.append("--offline")
    cmd += ["--bin", "paper_replay_probe"]
    output = subprocess.check_output(cmd, cwd=work, env=env, text=True)
    rows = list(csv.DictReader(io.StringIO(output)))
    assert [(r["cell"], int(r["static_toffoli"])) for r in rows] == [
        ("unfused_inverse", 512), ("range_matched_unfused", 446), ("fused_inverse", 393), ("fused_forward", 393)]
    metadata = {
        "source_commit": COMMIT,
        "original_pingpong_div_sha256": hashlib.sha256(original).hexdigest(),
        "scope": "Isolated static emission, before whole-circuit optimization. No input simulation or new full-circuit operating point.",
        "fold_majority_one_toffoli": True,
        "low56_unfused_override": "Enabled only for range_matched_unfused",
        "data_and_sign_qubits": 513,
        "rows": rows,
    }
    text = json.dumps(metadata, indent=2) + "\n"
    path = ROOT / "evidence/replay-cell-probe.json"
    if args.check:
        assert path.read_text() == text
    else:
        path.write_text(text)
    print(output, end="")


if __name__ == "__main__":
    run()
