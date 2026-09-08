"""Run the frozen windowed ping-pong corpus and its development checks."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

REPO = Path(__file__).resolve().parents[2]
SEED = "ecdsafail-windowed-independent-random-100k-v1"
PILOT = "ecdsafail-pingpong-windowed-pilot-20260907"


def clean_environment():
    env = dict(os.environ)
    prefixes = ("WINDOW", "SUB4_", "EVAL_", "MIXED_WINDOW_", "TLM_", "DIALOG_", "POINT_ADD_", "SINGLE_CCX_", "PROFILE_", "RUSTFLAGS")
    for name in list(env):
        if name.startswith(prefixes):
            del env[name]
    return env


def run_logged(command, cwd, env, path):
    start = time.monotonic()
    with path.open("w") as log:
        process = subprocess.Popen(command, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        for line in process.stdout:
            log.write(line)
            log.flush()
            print(line, end="", flush=True)
        code = process.wait()
    if code:
        raise RuntimeError(f"{command} exited {code}; see {path}")
    return time.monotonic() - start


def execute(output, width, tests, calls, seed, threads, tag, mixed=False, emit=True):
    case = output / tag
    case.mkdir(parents=True, exist_ok=True)
    env = clean_environment()
    env.update(EVAL_SHARED_SEED=seed, EVAL_THREADS=str(threads))
    if mixed:
        env.update(MIXED_WINDOW_BITS=str(width), EVAL_TESTS=str(tests), EVAL_MAX_ERROR_RATE="1")
    else:
        env.update(WINDOWED_MODE="1", WINDOW_BITS=str(width), SINGLE_CCX_FANOUT_DISABLE="1",
                   WINDOWED_TESTS=str(tests), WINDOWED_SEQUENCE_CALLS=str(calls), WINDOWED_MAX_ERROR_RATE="1")
    if calls == 1:
        env["EVAL_CHECKPOINT_DIR"] = str(case / "checkpoint")
    settings = {k: v for k, v in env.items() if k not in clean_environment()}
    settings.update(source_commit=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip())
    (case / "configuration.json").write_text(json.dumps(settings, indent=2) + "\n")
    if emit:
        run_logged([str(REPO / "target/release/build_circuit")], case, env, case / "build.log")
    elapsed = run_logged([str(REPO / "target/release/eval_circuit"), "--note", tag], case, env, case / "eval.log")
    (case / "timing.json").write_text(json.dumps({"evaluation_wall_seconds": elapsed}, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["pilot", "full", "mixed"])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--threads", type=int, default=8)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    out = args.output.resolve()
    if args.mode == "pilot":
        for width in range(6):
            execute(out, width, 256, 4, PILOT, 1, f"pilot-w{width}-four-call")
    elif args.mode == "mixed":
        execute(out, 16, 100000, 1, SEED, args.threads, "mixed", mixed=True, emit=not args.resume)
    else:
        execute(out, 16, 100000, 1, SEED, args.threads, "windowed-pingpong", emit=not args.resume)
