# 09. Canonical-Replay Correctness Reference

Published in **v1.3.0** for the alternate **34-page correctness-reference
manuscript**. This is not the low-cost 35-page version or an additional row in
the original frozen study.

## Result and scope

| Quantity | Recorded value |
|---|---:|
| Peak logical qubits | 1,804 |
| Static emitted CCX+CCZ gates | 5,188,043 |
| Mean executed Toffolis | 5,187,616.277587891 |
| Fresh pilot inputs | 4,096 |
| Output / phase / ancilla failures | 0 / 0 / 0 |

These describe **one complete sixteen-bit-window point-addition call**, including
lookup and cleanup, not a full Shor attack. The reference deliberately replaces
cheap approximate replay cells with full-width canonical arithmetic and exact
coordinate subtraction. It loses the earlier resource advantage. The original
1,392-qubit, 1.253-million mean-Toffoli operating point and its limitations remain
unchanged.

Finite value widths, the 736-round budget, square, and remaining coordinate
routines are inherited. This is a conditional replay repair and a tested
full-call reference, **not an all-input correctness guarantee**.

## Find the evidence

| Question | Files |
|---|---|
| What are the final resources and uncertainty? | [results.json](results.json), [emitted counts](emitted-counts.json) |
| What was frozen before fresh inputs? | [candidate-freeze.json](candidate-freeze.json), [pilot manifest](emit-window-16/fresh-4096/manifest.tsv) |
| Where are all 4,096 outcomes and work totals? | [Input/output ledger](emit-window-16/fresh-4096/inputs.tsv), [batch totals](emit-window-16/fresh-4096/batches.tsv) |
| Which inputs exposed the original defect? | [Zero-slope fixtures](fixtures/zero-slope.tsv), [smoke fixtures](fixtures/smoke.tsv) |
| Did the final full calls pass? | [w=16 zero-slope outcomes](logs/target-w16-zero-slope-canonical.tsv), [w=16 smoke outcomes](logs/target-w16-smoke-canonical.tsv), all w=4 records under [logs](logs/) |
| What failed before coordinate subtraction was changed? | [Replay-only attempt](attempts/replay-only/), [phase trace](attempts/replay-only/logs/shell-trace.log) |
| What changed in the code? | [Canonical replay](source/src/point_add/canonical_replay.rs), [dispatch](source/src/point_add/pingpong_div.rs), [coordinate wrappers](source/src/point_add/trailmix_ludicrous/arith.rs) |
| What about local boundary tests? | [Cell grid](logs/cells-w4-n1024-canonical.log), [both components](logs/component-w4-n1024-canonical.log) |

The cell grid retains all 700 rows: 576 canonical-domain cases pass, and 124
noncanonical-input rows remain visible outside that contract. Both 64-denominator
zero-payload components pass. The four targeted groups retain 256 outcomes.
Each zero-slope group contains **two points repeated over 32 measurement lanes**,
not 64 independently sampled point pairs.

Replay replacement alone still produced 30 and 38 phase flags in the w=4 and
w=16 zero-slope groups. The complete combined repair passes both. The failed
source and all retained logs remain under `attempts/replay-only/`.

## Why two static counts appear in build logs

`REFERENCE_COUNTS` is intermediate emitter bookkeeping. It includes 6,144
temporary forward Toffolis discarded while generating three inverse coordinate
subtractions. The serialized `ops.bin` does not contain them.
`stats_stream.rs` counted the emitted stream directly and produced the
authoritative **5,188,043**. The PDF and results JSON use this count, not the
intermediate 5,194,187 figure. Verification without `ops.bin` checks this recorded
reconciliation; it does not claim to recount an omitted 14 GB stream.

## Verify records without executing circuits

From the repository root, with Python 3.11+:

```sh
python3 -B experiments/09-canonical-reference/verify.py
```

This checks package hashes, all original supplement files, available frozen
sources, recorded native/stream identity links, complete pilot and batch counts,
all targeted outcomes, the canonical and noncanonical grids, and retained
failed attempts. It also independently recomputes all 4,096 classical curve
outputs in Python. It does not execute a quantum circuit or prove phase
correctness. The root verifier includes this check.

The original `analyze.py` is preserved as provenance. Its original main routine
expects omitted native binaries and streams and writes derived files beside
itself. Use `verify.py` for public read-only checking.

## Rebuild and rerun in scratch space

Requires Rust/Cargo, a C compiler, locked dependencies in the Cargo cache,
approximately 32 GiB of RAM, and substantial scratch disk space. Full w=16
emission stores about 14 GB of uncompressed operation records in memory.
The runner is serial and enforces a 19,000,000 KiB RSS ceiling and a 20-minute
per-process timeout. Process-inspection permission is required. It is not a
sandbox for hostile programs or a concurrently modified filesystem.

```sh
python3 experiments/09-canonical-reference/reproduce.py prepare
python3 experiments/09-canonical-reference/reproduce.py build
python3 experiments/09-canonical-reference/reproduce.py cells
python3 experiments/09-canonical-reference/reproduce.py component
python3 experiments/09-canonical-reference/reproduce.py emit --w 16
python3 experiments/09-canonical-reference/reproduce.py stats --w 16
python3 experiments/09-canonical-reference/reproduce.py targeted --w 16
python3 experiments/09-canonical-reference/reproduce.py pilot --w 16
```

All writes go under `.work/canonical-reference-reproduction/`. Use a new
`--work-dir .work/another-name` consistently for another run. Existing output
logs/checkpoints are refused. Symlinked output paths and hardlinked non-build
files are rejected. The archive records remain read-only.

To repeat w=4 targeted tests, run the emit and targeted stages with `--w 4`.
To reproduce the unsuccessful version, prepare a separate directory using
`--variant replay-only`; its fresh 4,096-input pilot was not run.
The wrapper compares emitted hashes and recorded outcomes. Pilot completion
order can differ, so comparisons use case and batch indices, not physical row
order. Native binary hashes can vary by toolchain. A stream mismatch stops
reproduction rather than silently replacing the original identity.

## Provenance and publication boundary

The supplied manuscript supplement is anchored by
`provenance/original-manifest.json`. Its original README is retained there.
All original inputs, source snapshots, logs, scripts, and numerical records
are unchanged. The new manifest additionally covers publication wrappers.

The original large operation stream and evaluator executable are intentionally
omitted. Their freeze hashes remain receipts. The read-only stream-counter
source was added after the original candidate freeze and does not change the
frozen circuit. No parameters were tuned on the fresh pilot.

All v1.0.0, v1.1.0, and v1.2.0 scientific files and releases remain unchanged.
This separate study is not pooled with the original three-circuit comparison
and is not claimed as a new low-cost record.
