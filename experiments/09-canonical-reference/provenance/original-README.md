# Canonical-replay correctness reference

This is a **full, single-call, sixteen-bit-window point-addition circuit**,
including the quantum-addressed table lookup and payload cleanup. It is not a
full Shor attack and not an optimized replacement for the earlier low-cost circuit.

## Verified result

- Peak logical width: **1,804 qubits**.
- Static count in the serialized stream: **5,188,043 CCX+CCZ gates**.
- Mean executed Toffoli count: **5,187,616.277587891** on a new 4,096-input pilot.
- Output, phase, and ancilla failures: **0/4,096**.
- Independently reconstructed Python reference outputs: **4,096 matches**.
- Canonical cell grid: **576 passing cases**.
- Zero-payload component tests: **64 division and 64 multiplication cases pass**.
- Supported zero-slope and smoke tests: **all 256 retained lanes pass**, across
  w=4 and w=16. The zero-slope groups contain two points repeated over 32
  measurement lanes each, not 64 independent point samples.

`results.json`, `candidate-freeze.json`, `emitted-counts.json`, and `logs/` retain
the values, hashes, and outcomes. The source and evaluator files named in the
freeze remain unchanged. A read-only stream-counting binary was added afterward.
No circuit parameters were tuned using the fresh pilot. The one-sided 95%
zero-failure bound for this pilot is approximately 0.0731% under the stated
sampling assumptions. It is not a global coherent-error bound.

## What changed

`source/src/point_add/canonical_replay.rs` supplies canonical negation, addition,
halving, doubling, and seed operations. `pingpong_div.rs` selects these under
`QIP_CANONICAL_REPLAY=1`. Payloads remain in `[0,p)` and full-width carry networks
replace the invalid truncated predicates. This deliberately gives up the cheap
fused replay cells.

Replay replacement alone did not fix the complete call. Phase tracing identified
the final y subtraction as a second source of error for zero input. Under
`QIP_CANONICAL_COORDS=1`, both coordinate-subtraction wrappers in
`trailmix_ludicrous/arith.rs` use the inverse of canonical addition. The failed
replay-only attempt is retained in `attempts/replay-only/`.

The 736-round value schedule, shrinking value widths, square, and remaining
coordinate routines are inherited. This is a conditional replay repair and a
tested full-call reference, **not an all-input proof for point addition**.

## Why the cost increased

The original low-cost path uses short corrections and narrow phase comparisons.
The reference uses full-width canonical operations, extra carry workspace, and
explicit zero handling. Its resource point loses the original practical
advantage. The historical 1,392-qubit, 1.253-million mean-Toffoli result remains
unchanged and retains its known limitations. A low-overhead repair remains open.

The builder's `REFERENCE_COUNTS` log is intermediate bookkeeping, not the final
static count: generating three inverse coordinate-subtraction blocks temporarily
constructs and discards 6,144 forward Toffolis. `stats_stream` counts `ops.bin`
directly and gives the authoritative 5,188,043 figure. No discarded operation is
charged to the result reported in the manuscript.

## Reproduction

Rust/Cargo, the pinned Cargo dependencies, a C compiler, and Python 3.11+ are
required. Builds use `--locked --offline`. Native binaries and the approximately
14 GB uncompressed operation stream are omitted. The local runner checks RSS
and time, so process-inspection permission is required. Tested on a 32 GB macOS
machine. Full-window emission uses preallocated capacity and an RSS watchdog.

```sh
cargo build --manifest-path source/Cargo.toml --release --locked --offline --bin build_circuit --bin eval_bounded --bin stats_stream --target-dir target
python3 run.py cells
python3 run.py component
python3 run.py emit --w 16
python3 run.py random --w 16 --n 4096
python3 analyze.py
```

Use a new scratch copy for reexecution. Existing fresh checkpoint directories
are refused. The included original `candidate-freeze.json` is provenance, not
a file to regenerate over the retained record. Native executable hashes may
differ with the local toolchain. The source and operation-stream hashes, actual
outcomes, and integer counts are the relevant reconstruction targets.

The targeted runner and shell trace additionally use the preceding follow-up
diagnostic driver and fixtures. Their historical absolute paths are recorded,
not portable commands. The included fixture TSVs and `targeted-driver.rs` permit
rebuilding that unchanged driver as a separate binary against this package.
Invoke it with `OPS_PATH FIXTURE_TSV -` for an unsegmented run. The two TSVs are
`fixtures/zero-slope.tsv` and `fixtures/smoke.tsv`.

The manuscript and lean Overleaf archive keep this evidence separate. Nothing
in this study changes the public v1.0.0/v1.1.0 releases. No GitHub push was made.
