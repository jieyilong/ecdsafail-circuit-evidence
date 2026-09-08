#!/usr/bin/env python3
"""Build and rerun pinned circuits in .work/ without modifying published evidence."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

from common import ROOT, FRESH, CANDIDATES, FREEZE_SHA256, atomic_write, check_work_tree, ensure_checks_enabled, load_module, read_json, sha, verify_original, verify_sources, work_path
from results import tsv

WORK=ROOT/".work"
ALL=(*CANDIDATES, "zero-payload-probe")


def clean_env():
    return {"PATH":os.environ.get("PATH","/usr/bin:/bin"),"HOME":os.environ.get("HOME","/tmp"),"TMPDIR":os.environ.get("TMPDIR","/tmp"),"LANG":"C","LC_ALL":"C"}


def run_logged(command,cwd,env,log):
    cwd=work_path(cwd)
    log=work_path(log)
    log.parent.mkdir(parents=True,exist_ok=True)
    if log.exists() and log.stat().st_nlink>1:
        raise ValueError(f"Refusing to truncate a hard-linked log: {log}")
    with log.open("w") as f:
        process=subprocess.Popen(command,cwd=cwd,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,bufsize=1)
        for line in process.stdout:
            print(line,end="",flush=True)
            f.write(line)
            f.flush()
        code=process.wait()
    if code:
        raise subprocess.CalledProcessError(code,command)


def source(name):
    return ROOT/"sources/trees"/name


def build_dir(name):
    return work_path(WORK/"build"/name)


def check_build_source(name):
    expected=read_json(ROOT/"provenance/source-trees.json")[name]["files"]
    root=build_dir(name)
    for rel,digest in expected.items():
        path=work_path(root/rel)
        assert path.stat().st_nlink==1 and sha(path)==digest, (name,rel,"working source changed or aliased")
    for extra in ("build.rs", ".cargo/config", ".cargo/config.toml"):
        assert extra in expected or not (root/extra).exists(), f"Unexpected build configuration: {extra}"


def build(name,offline=False):
    version=subprocess.check_output(["rustc","--version"],env=clean_env(),text=True).strip()
    if version.split()[1]!="1.93.0":
        raise RuntimeError(f"Original source used Rust 1.93.0; found {version}. Select that toolchain before building.")
    path=build_dir(name)
    if not path.exists():
        path.parent.mkdir(parents=True,exist_ok=True)
        shutil.copytree(source(name),path)
    check_build_source(name)
    work_path(path/"target")
    command=["cargo","build","--release","--locked"]
    if offline:
        command.append("--offline")
    command += ["--bin","build_circuit"]
    if name=="conservative-pingpong":
        command += ["--bin","eval_bounded"]
    run_logged(command,path,clean_env(),WORK/"logs"/(name+"-build.log"))
    check_build_source(name)
    print(f"Built {name} in {path}")


def binary(name,role):
    path=work_path(build_dir(name)/"target/release"/(role+(".exe" if os.name=="nt" else "")))
    if not path.exists():
        raise RuntimeError(f"Missing {path}. Run the build command first.")
    check_build_source(name)
    return path


def configuration(name):
    return read_json(ROOT/"provenance/freeze.json")["candidates"][CANDIDATES[name]]


def ops_path(name):
    return work_path(WORK/"emitted"/name/"ops.bin")


def emit(name):
    b=binary(name,"build_circuit")
    cfg=configuration(name)
    dest=ops_path(name)
    dest.parent.mkdir(parents=True,exist_ok=True)
    if dest.exists():
        assert sha(dest)==cfg["ops_sha256"], "Existing emitted stream differs. Inspect it before retrying in a clean .work directory."
        print(f"Already emitted and verified: {dest}")
        return
    check_work_tree(dest.parent)
    env=clean_env()
    env.update(cfg["settings"])
    run_logged([str(b)],dest.parent,env,WORK/"logs"/(name+"-emit.log"))
    actual=sha(dest)
    if actual!=cfg["ops_sha256"]:
        raise RuntimeError("Emitted byte hash differs from the frozen artifact. Do not treat it as a reproduction. See docs/REPRODUCTION.md for compression/toolchain investigation.")
    atomic_write(dest.parent/"receipt.json",json.dumps(dict(original_freeze_sha256=FREEZE_SHA256,candidate=name,source_commit=cfg["source_commit"],settings=cfg["settings"],ops_sha256=actual,builder_sha256=sha(b)),indent=2)+"\n")
    print(f"Emitted {name}: byte-identical to the frozen stream.")


def expected_rows(name,stratum,n):
    corpus={int(r["index"]):r for r in tsv(FRESH/"data/corpus"/(stratum+".tsv.gz"))}
    rows={}
    for result in tsv(FRESH/"runs"/name/stratum/"checkpoint/outcomes.tsv.gz"):
        index=int(result["index"])
        if index>=n:
            continue
        r=dict(corpus[index]);r.update(result)
        for got,expected in (("got_x","expected_x"),("got_y","expected_y"),("got_address","address")):
            if r[got]=="=":
                r[got]=hex(int(r[expected])) if expected=="address" else r[expected]
        rows[index]=r
    assert set(rows)==set(range(n))
    return rows


def sample_size(smoke, full_size):
    if smoke is None:
        return full_size
    if smoke<128 or smoke%64 or smoke>full_size:
        raise ValueError("Smoke size must be a multiple of 64, at least 128, and no greater than the stratum size")
    return smoke


def evaluate(name,stratum,threads,smoke=None):
    n=sample_size(smoke,stratum["n"])
    cfg=configuration(name)
    ops=ops_path(name)
    assert ops.exists() and sha(ops)==cfg["ops_sha256"], "Emit and verify the circuit first"
    evaluator=binary("conservative-pingpong","eval_bounded")
    case=work_path(WORK/"evaluations"/name/f"{stratum['name']}-n{n}")
    case.mkdir(parents=True,exist_ok=True)
    check_work_tree(case,allowed_readonly=(case/"ops.bin",))
    config=dict(original_freeze_sha256=FREEZE_SHA256,candidate=name,stratum=stratum,shots=n,threads=threads,ops_sha256=cfg["ops_sha256"],evaluator_sha256=sha(evaluator))
    path=case/"reproduction-config.json"
    if path.exists():
        assert read_json(path)==config, "Existing checkpoint has a different reproduction configuration"
    else:
        atomic_write(path,json.dumps(config,indent=2,sort_keys=True)+"\n")
    # A hard link avoids copying the large read-only stream for each case.
    link=case/"ops.bin"
    if not link.exists():
        os.link(ops,link)
    assert sha(link)==cfg["ops_sha256"]
    env=clean_env()
    env.update(WINDOWED_MODE="1",WINDOW_BITS="16",WINDOWED_SEQUENCE_CALLS="1",WINDOWED_TESTS=str(n),WINDOWED_MAX_ERROR_RATE="1",EVAL_THREADS=str(threads),EVAL_SHARED_SEED=stratum["seed"],QIP_TABLE_BETA=stratum["beta"],EVAL_CHECKPOINT_DIR=str(case/"checkpoint"))
    run_logged([str(evaluator),"--note","public-evidence-reproduction"],case,env,case/"eval.log")
    frozen=load_module("frozen_case_analysis",ROOT/"sources/frozen-tools/bounded_qip/analyze.py")
    actual,_,stats=frozen.read_case(case,dict(seed=stratum["seed"],target_shots=n,window_bits=16,qip_table_beta=stratum["beta"],qubits=cfg["Q"],ops=cfg["static_operations"],ops_fingerprint=cfg["ops_fingerprint"]))
    expected=expected_rows(name,stratum["name"],n)
    assert actual==expected, "Reexecuted outcomes differ from recorded outcomes; retain the new run for diagnosis"
    batch_keys=("shots","toffoli","clifford","classical_failures","phase_failure_shots","ancilla_failure_shots","any_failure_shots","phase_garbage_batches","ancilla_garbage_batches")
    reference={int(r["batch"]):r for r in tsv(FRESH/"runs"/name/stratum["name"]/"checkpoint/batches.tsv")}
    for b in tsv(case/"checkpoint/batches.tsv"):
        assert all(b[k]==reference[int(b["batch"])][k] for k in batch_keys), (name,stratum["name"],b["batch"])
    result=dict(config=config,stats=stats,completed_utc=datetime.now(timezone.utc).isoformat(),matches_recorded_outcomes=True,matches_recorded_gate_totals=True,scope="New execution of frozen inputs; smoke runs are prefixes, not independent accuracy studies")
    atomic_write(case/"reproduction-result.json",json.dumps(result,indent=2,sort_keys=True)+"\n")
    print(f"MATCH: {name} / {stratum['name']} / {n} cases and all batch gate counts.")


def zero_probe():
    name="zero-payload-probe"
    b=binary(name,"build_circuit")
    env=clean_env()
    env.update(QIP_PINGPONG_PROFILE="guarded",TLM_MSBS="40",QIP_ZERO_PROBE_INPUTS=str(build_dir(name)/"probe-denominators.txt"))
    path=WORK/"logs/zero-payload-probe.log"
    run_logged([str(b)],build_dir(name),env,path)
    lines=lambda p:[s for s in p.read_text().splitlines() if s.startswith("ZERO_PAYLOAD ")]
    assert lines(path)==lines(source(name)/"zero-probe.log")
    print("MATCH: both recorded zero-payload diagnostic outcomes reproduced. These are negative subroutine results.")


if __name__=="__main__":
    ensure_checks_enabled()
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest="command",required=True)
    b=sub.add_parser("build"); b.add_argument("--candidate",choices=(*ALL,"all"),required=True); b.add_argument("--offline",action="store_true")
    e=sub.add_parser("emit"); e.add_argument("--candidate",choices=(*CANDIDATES,"all"),required=True)
    r=sub.add_parser("run"); r.add_argument("--candidate",choices=(*CANDIDATES,"all"),required=True); r.add_argument("--stratum",required=True); r.add_argument("--threads",type=int,choices=range(2,9),default=8); r.add_argument("--smoke",type=int)
    sub.add_parser("zero-probe")
    args=parser.parse_args()
    verify_original();verify_sources()
    if args.command=="build":
        for name in (ALL if args.candidate=="all" else (args.candidate,)):
            build(name,args.offline)
    elif args.command=="emit":
        for name in (CANDIDATES if args.candidate=="all" else (args.candidate,)):
            emit(name)
    elif args.command=="zero-probe":
        zero_probe()
    else:
        strata=read_json(FRESH/"corpus-spec.json")["strata"]
        if args.stratum!="all":
            strata=[s for s in strata if s["name"]==args.stratum]
            if not strata:
                parser.error("Unknown stratum")
        for name in (CANDIDATES if args.candidate=="all" else (args.candidate,)):
            for s in strata:
                evaluate(name,s,args.threads,args.smoke)
