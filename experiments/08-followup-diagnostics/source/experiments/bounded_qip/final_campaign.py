"""Freeze actual artifacts, then run fresh research cases with no adaptive tuning."""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import sys

from analyze import read_case, sha

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "experiments/windowed_pingpong"))
from run_cases import run_logged

ORDER = int("FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141", 16)
CORE = ("src/circuit.rs", "src/sim.rs", "src/weierstrass_elliptic_curve.rs",
        "src/bin/eval_circuit.rs", "src/windowed_table.rs", "Cargo.toml", "Cargo.lock")


def write_json(path, data):
    path.write_text(json.dumps(data, indent=2, sort_keys=True)+"\n")


def clean_env():
    return {"PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "HOME": os.environ.get("HOME", "/tmp"),
            "TMPDIR": os.environ.get("TMPDIR", "/tmp"), "LANG":"C", "LC_ALL":"C"}


def prepare(root, candidates_path):
    assert not root.exists(), "Use a new experiment directory"
    source = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip()
    relevant = subprocess.check_output(["git", "status", "--porcelain", "--untracked-files=all", "--", "src", "experiments/bounded_qip", "Cargo.toml", "Cargo.lock"], cwd=REPO, text=True)
    assert not relevant.strip(), "Commit the relevant source/protocol/analysis files before freezing"
    subprocess.check_call(["git", "diff", "--exit-code", "c6ad76006be76711c27405365b3e61e8f0a032b3", "--", *CORE], cwd=REPO)
    root.mkdir(parents=True)
    artifacts = root / "artifacts"
    artifacts.mkdir()
    code = artifacts / "code"
    for rel in ("experiments/bounded_qip", "experiments/windowed_pingpong"):
        dest = code / rel
        dest.mkdir(parents=True)
        for p in (REPO / rel).iterdir():
            if p.is_file() and p.suffix in (".py", ".md"):
                shutil.copy2(p, dest / p.name)
    shutil.copy2(REPO / "target/release/eval_bounded", artifacts / "eval_bounded")
    shutil.copy2(REPO / "target/release/build_circuit", artifacts / "build_circuit")
    recipe = ["Cargo.toml", "Cargo.lock", "src", "experiments/bounded_qip",
              "experiments/windowed_pingpong/run_cases.py", "experiments/windowed_pingpong/static_resources.py",
              "experiments/windowed_pingpong/stream_fingerprint.py"]
    with (artifacts / "source.tar.gz").open("wb") as f:
        subprocess.run(["git", "archive", "--format=tar.gz", source, *recipe], cwd=REPO, stdout=f, check=True)
    candidates = json.loads(candidates_path.read_text())
    frozen = {}
    for name, c in candidates.items():
        ops = Path(c["ops_path"]).resolve()
        manifest = dict(line.split("\t",1) for line in Path(c["checkpoint_manifest"]).read_text().splitlines())
        static = json.loads(Path(c["static_path"]).read_text())
        assert manifest["ops_fingerprint"] == c["expected_ops_fingerprint"]
        assert static["ops_sha256"] == c["expected_ops_sha256"]
        assert static["ops_sha256"] == sha(ops)
        assert int(manifest["ops"]) == static["static_operations"]
        dest = artifacts / (name + ".ops.bin")
        shutil.copy2(ops, dest)
        frozen[name] = dict(backend=c["backend"], profile=c["profile"],
            source_commit=(source if c["source_commit"]=="CURRENT" else c["source_commit"]),
            code_release=c.get("code_release"), Q=int(manifest["qubits"]),
            static_operations=static["static_operations"], static_toffoli=static["static_toffoli"],
            ops_fingerprint=manifest["ops_fingerprint"], ops_sha256=sha(dest),
            ops_file=str(dest.relative_to(root)), settings=c["settings"], static_counts=static)
    assert set(frozen) == {"pingpong_base", "pingpong_conservative", "jump2"}
    files = {str(p.relative_to(root)):sha(p) for p in artifacts.rglob("*") if p.is_file()}
    freeze = dict(format="qip-bounded-freeze-v1", frozen_utc=datetime.now(timezone.utc).isoformat(),
        source_commit=source, candidates=frozen, files_sha256=files,
        core_sha256={p:sha(REPO/p) for p in CORE},
        rustc=subprocess.check_output(["rustc","--version"],text=True).strip(),
        build_command="cargo build --release --locked --offline --bin build_circuit --bin eval_bounded",
        evaluator="artifacts/eval_bounded", rng_scheme="Original shared-input and per-batch SHAKE256 domains, separate seed per stratum",
        final_order=["pingpong_conservative", "pingpong_base", "jump2"], tests_per_circuit=100000,
        note="All candidate selection used development data. Fresh master seed is generated after this freeze file is written.")
    write_json(root / "freeze.json", freeze)
    for p in artifacts.rglob("*"):
        if p.is_file():
            p.chmod(0o555 if p.name in ("eval_bounded", "build_circuit") else 0o444)
    generate_spec(root)
    print("FROZEN", sha(root/"freeze.json"), flush=True)


def generate_spec(root):
    assert (root / "freeze.json").exists() and not (root / "fresh-corpus-spec.json").exists()
    master = secrets.token_bytes(32)
    bases = {"G":1}
    for label in ("P1", "P2"):
        counter = 0
        while True:
            raw = hashlib.shake_256(b"qip-bounded-public-point-v1\0"+master+label.encode()+counter.to_bytes(8,"little")).digest(32)
            k = int.from_bytes(raw,"big")
            if 1 <= k < ORDER and k not in bases.values():
                bases[label]=k
                break
            counter += 1
    strata=[]
    for label, k in bases.items():
        for shift in (0,128,240):
            name=f"{label}-s{shift}"
            digest=hashlib.sha256(b"qip-bounded-stratum-v1\0"+master+name.encode()).hexdigest()
            strata.append(dict(name=name, base=label, base_scalar=hex(k), shift=shift,
                beta=hex((k*(1<<shift))%ORDER), seed="qip-bounded-final-v1:"+digest, n=11111))
    strata[-1]["n"] = 11112
    assert len({s["beta"] for s in strata}) == 9 and sum(s["n"] for s in strata)==100000
    write_json(root / "fresh-corpus-spec.json", dict(generated_utc=datetime.now(timezone.utc).isoformat(),
        freeze_sha256=sha(root / "freeze.json"), master_seed_hex=master.hex(),
        public_base_scalars={k:hex(v) for k,v in bases.items()}, strata=strata))


def run(root, threads):
    assert 2 <= threads <= 8
    freeze=json.loads((root / "freeze.json").read_text())
    spec=json.loads((root / "fresh-corpus-spec.json").read_text())
    freeze_hash=sha(root / "freeze.json")
    assert spec["freeze_sha256"] == freeze_hash
    for rel, digest in freeze["files_sha256"].items():
        assert sha(root / rel) == digest, (rel, "frozen artifact changed")
    assert sha(Path(__file__)) == freeze["files_sha256"]["artifacts/code/experiments/bounded_qip/final_campaign.py"]
    for name in freeze["final_order"]:
        c=freeze["candidates"][name]
        for s in spec["strata"]:
            case=root / "results" / name / s["name"]
            case.mkdir(parents=True, exist_ok=True)
            ops=(root / c["ops_file"]).resolve()
            assert sha(ops)==c["ops_sha256"]
            config=dict(freeze_sha256=freeze_hash, candidate=name, stratum=s,
                        ops_sha256=c["ops_sha256"], evaluator_sha256=freeze["files_sha256"][freeze["evaluator"]], threads=threads)
            config_path=case / "configuration.json"
            if config_path.exists():
                assert json.loads(config_path.read_text())==config
            else:
                write_json(config_path,config)
            op_link=case / "ops.bin"
            if op_link.exists():
                assert op_link.resolve()==ops
            else:
                op_link.symlink_to(ops)
            expected=dict(seed=s["seed"], target_shots=s["n"], window_bits=16, qip_table_beta=s["beta"],
                          qubits=c["Q"], ops=c["static_operations"], ops_fingerprint=c["ops_fingerprint"])
            if (case / "COMPLETE.json").exists():
                read_case(case,expected)
                continue
            env=clean_env()
            env.update(WINDOWED_MODE="1", WINDOW_BITS="16", WINDOWED_TESTS=str(s["n"]),
                WINDOWED_SEQUENCE_CALLS="1", WINDOWED_MAX_ERROR_RATE="1", EVAL_THREADS=str(threads),
                EVAL_SHARED_SEED=s["seed"], QIP_TABLE_BETA=s["beta"], EVAL_CHECKPOINT_DIR=str(case/"checkpoint"))
            print(f"FINAL_CASE_START {name} {s['name']} {s['n']}",flush=True)
            evaluator=root / freeze["evaluator"]
            assert sha(evaluator)==config["evaluator_sha256"]
            elapsed=run_logged([str(evaluator),"--note",f"frozen-{name}-{s['name']}"],case,env,case/"eval.log")
            _,manifest,stats=read_case(case,expected)
            complete=dict(elapsed_seconds=elapsed, stats=stats, freeze_sha256=freeze_hash,
                          ledger_sha256={p.name:sha(p) for p in (case/"checkpoint").iterdir() if p.is_file()})
            write_json(case / "COMPLETE.json",complete)
            print(f"FINAL_CASE_DONE {name} {s['name']} failures={stats['any_failure']} T={stats['mean_T']} Q={stats['Q']}",flush=True)


if __name__ == "__main__":
    p=argparse.ArgumentParser()
    p.add_argument("task",choices=["prepare","run"])
    p.add_argument("--root",type=Path,required=True)
    p.add_argument("--candidates",type=Path)
    p.add_argument("--threads",type=int,default=8)
    args=p.parse_args()
    if args.task=="prepare":
        assert args.candidates
        prepare(args.root.resolve(),args.candidates.resolve())
    else:
        run(args.root.resolve(),args.threads)
