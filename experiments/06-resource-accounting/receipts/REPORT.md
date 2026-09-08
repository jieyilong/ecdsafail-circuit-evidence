# Bounded source-derived accounting and backend ablation

Status: **completed within bounded scope**, 8 September 2026. No paper, frozen
source, frozen data, simulator, or scoring file was changed. No nonce was searched.
This is exploratory mechanism evidence, not a replacement for the frozen study.

## Integration-ready findings

- Actual allocator peaks reproduce mixed ping-pong **1321**, windowed original
  **1338**, conservative windowed **1392**, and windowed Jump-2 **1162**.
- The original mixed peak is in **special initial/seed payload replay**, not in
  the ordinary 393-Toffoli inverse payload cell. The original windowed circuit
  also reaches **1338 during its controlled product-register square**.
- A source-knob **2x2 backend/square experiment with postcompiler disabled** was
  feasible. With the legacy square fixed, switching the legacy Jump-2 backend to
  ping-pong reduces static Toffolis by **340442**, from **1357682 to 1017240**.
  The square ledger is identical across backends. This is not the historical
  original-parent comparison and does not retrospectively explain that saving.
- All 12 tested instrumented/unchanged emitted stream pairs have identical
  decompressed records (and identical compressed SHA-256). All six 64-input smoke
  evaluations completed, **with failures retained**, as detailed below.

## 1. Method and identity checks

`sources/` holds byte-identical copies of the three requested snapshots;
`source-manifest.json` identifies every source file. `instrumented/` changes only
the emitter, adds `accounting.rs`, and has reproducible diffs in `patches/`.
The paper sections 04, 06a and 12, canonical notation, and the circuit-optimization
skill were read before implementation. No external numerical claims are introduced.

Allocation/free/reacquire events maintain a live-owner map. Duplicate ownership,
unowned frees, and disagreement with `active_qubits` abort. Each phase snapshot
is taken at that phase's actual maximum. Its owner counts sum to its own peak,
never to a sum of separately maximized components. `max_wire_plus_one` agrees
with the live peak in these runs. An owner denotes an **allocator lease and its
allocation site**, not a proof that a reset or reclaimed wire is semantically clean.
In particular, original coordinate wires can later hold transcript or scratch.

Phase Toffolis are counted from the retained operation vector for bounded
emissions, or from the existing counting sink without storing the vector. Both
CCX and CCZ count as one static Toffoli. Initial Jump-2 labels are sidecar metadata:
the operational phase names are preserved because source optimizations inspect
them. Raw phase totals include local arithmetic and phase-cleanup work emitted
within those source boundaries, not a new gate-minimal mathematical decomposition.

The QROM source's fast counting model omitted 84 non-Toffoli operations at w=4
and 327668 at w=16. Its Toffoli and global-peak totals matched, but its operation
count did not. The old results are retained as `*-count`. The final `*-exact-*`
runs use **real QROM gate emission into the counting sink**, selected by the
diagnostic `ACCOUNTING_EXACT_QROM=1`. At w=4, raw operation totals, Toffolis, and
peaks now match actual emission for all three source trees. Full-window counts
use this path. No 200-million-operation vector was allocated.

Full-window stream identity was **not** rerun. The original and conservative raw
totals plus the unchanged 96-X identity tail agree exactly with frozen totals.
Jump-2 accounting is precompiler; its frozen postcompiler totals are kept separate.

## 2. Simultaneous live ownership

| Circuit and witnessed phase | Simultaneously live owners | Q |
|---|---|---:|
| Original mixed, special replay | 704 transcript + 512 payload + 8+8 residual Euclidean operands + 88 carries + 1 flag | 1321 |
| Original windowed, special replay | Same + 16 address + 1 nonzero control | 1338 |
| Conservative windowed, special replay | 736 transcript + 512 payload + 11+11 residual operands + 104 carries + 1 flag + 16 address + 1 nonzero control | 1392 |
| Original windowed, square (tied peak) | 512 restored coordinates + 16 address + 1 control + 256 masked slope + 553 square workspace | 1338 |
| Jump-2 windowed, inverse fold | 512 payload + 13+13 current operands + 585 transcript/pending-symbol allocation pool + 4 GCD controls + 18 fold scratch + 16 address + 1 nonzero control | 1162 |

The Jump-2 transcript pool is the **live partial pool at this fold**, not the
609-qubit terminal transcript. Its 18 fold scratch qubits comprise allocation
groups of 3, 13, 1 and 1. The square's 553-workspace decomposition is
128+1+1+129+256+38. Restored X ownership is spread across initial, reacquired and
reverse-walk allocation sites; those sites are not additional semantic registers.
Complete site/line witnesses are in each run's `owners.tsv`.

| Phase family | Mixed original | Windowed original | Conservative windowed |
|---|---:|---:|---:|
| Euclidean value forward/reverse | 1063 | 1080 | 1128 |
| Ordinary forward payload replay | 1319 | 1336 | 1374 |
| Ordinary inverse payload replay | 1320 | 1337 | 1375 |
| Special initial/seed replay | 1321 | 1338 | 1392 |
| Square | 1287 | 1338 | 1338 |

The windowed QROM walk peaks at 1056, below the arithmetic peaks. Its selected
coordinate payloads do not coexist with the full transcript at the replay peak.

## 3. Static Toffoli ledger

These are **static emitted CCX+CCZ counts**, not the paper's mean executed T.
The following is a convenient grouping of verified source phases, before any
whole-stream compiler. Ordinary ping-pong replay is 702 cells at 393 each in the
original profile, or 734 at 457 each in the conservative profile.

| Raw source-phase group | Mixed original | Windowed original | Conservative windowed |
|---|---:|---:|---:|
| Value forward, both arithmetic calls | 197884 | 197884 | 219782 |
| Value reverse, both calls | 197484 | 197484 | 219414 |
| Initial forward payload cell | 88 | 88 | 104 |
| Forward seed cell | 152 | 152 | 168 |
| Ordinary forward payload cells | 275886 | 275886 | 335438 |
| Initial inverse payload cell | 88 | 88 | 104 |
| Inverse seed cell | 152 | 152 | 168 |
| Ordinary inverse payload cells | 275886 | 275886 | 335438 |
| Endpoint sign/duplicate handling | 348 | 348 | 412 |
| Square including coherent mask where present | 59449 | 64968 | 64968 |
| Coordinate phases | 1660 | 3987 | 4092 |
| QROM-labeled phases | 0 | 167179 | 167179 |
| Initial nonzero-address control | 0 | 29 | 29 |
| **Total** | **1009077** | **1184131** | **1347296** |

Zero-Toffoli setup, restore, register declarations and identity-tail operations
remain present in the full operation ledger. The QROM-labeled total includes the
final address-flag cleanup emitted before leaving the last QROM phase; it should
not be read as only table lookup/unlookup gates. Source boundaries, not inferred
per-case control activity, determine these categories.

| Jump-2 windowed raw source-phase group | Static Toffolis |
|---|---:|
| Initial value phases | 5220 |
| Ordinary value phases | 628774 |
| Initial payload phases | 22526 |
| Ordinary payload phases | 704939 |
| Initial codec | 4 |
| Ordinary codec/decode | 6374 |
| Square | 55668 |
| Coordinates | 3985 |
| QROM-labeled phases | 167179 |
| Initial address control | 29 |
| **Raw total** | **1594698** |
| Frozen postcompiler total, comparison only | **1593346** |

Jump-2's compiler difference is -1352 Toffolis and -808 operations for the
16-bit-window artifact. Those differences are **not apportioned among raw
categories**. In the separately emitted mixed Jump-2 source, raw/final counts
are 1370715/1358316, demonstrating why the compiler distinction matters.

## 4. Controlled 2x2 and its scope

All four cells use **original-pingpong source**, the mixed coordinate shell,
identical explicit defaults, `CONSTPROP_DISABLE=1`, and
`SINGLE_CCX_FANOUT_DISABLE=1`. The latter returns the legacy path before fanout,
dead-gate, bridge, strip and action-mask postpasses. Ping-pong already returns
without these passes. Source-level specialization remains enabled in both.

The switches are `SUB4_LEGACY_POINT_ADD` and `SUB4_LEGACY_SQUARE`, both interpreted
by **presence**, so unset is not equivalent to value 0. Common settings are saved
in `run.py:ablation()` and each `emitter-settings.tsv`. After removing only the
diagnostic output directory, the effective environment difference for a backend
contrast is exactly `SUB4_LEGACY_POINT_ADD`. The square phase's operations, CCX,
CCZ, HMR and reset counts match across backends for either square choice.

| Euclidean backend | Square | Q | Static Toffolis | Mean executed T, 64 smoke inputs |
|---|---|---:|---:|---:|
| Legacy Jump-2 | Legacy symmetric/Karatsuba | 1150 | 1357682 | 1300656.40625 |
| Legacy Jump-2 | Product register | 1287 | 1349527 | 1292819.59375 |
| Ping-pong | Legacy symmetric/Karatsuba | 1321 | 1017240 | 960575.90625 |
| Ping-pong | Product register | 1321 | 1009077 | 952684.21875 |

At fixed legacy square, the backend cost contrast is **340442 static Toffolis**.
At fixed product square it is **340450**. The square itself costs 67612 versus
59449 in both backends, a reduction of **8163**. Ping-pong's total square-switch
effect is exactly 8163. Legacy Jump-2's total reduction is 8155: an **8-Toffoli
downstream payload-phase interaction** remains, also visible as changed HMR/reset
counts. Its precise allocator/call-index cause was not traced. The 2x2 is an
operational source-knob ablation, not four perfectly independent gate streams.

This establishes a matched-square/no-postcompiler **backend cost** comparison
for this snapshot and its approximate settings. It does not establish a universal
GCD algorithm advantage, an equal-error comparison, or a decomposition of the
published original-parent saving. In particular, subtracting the square-only
saving from that historical comparison does **not** make the residual all GCD:
compiler and other source differences remain.

## 5. Approximation and smoke outcomes

Original ping-pong: 704 rounds, width margin 4; width slopes 17/33/40 per 100
rounds, breakpoints 40/304, clamp 8..259. Ordinary replay uses chunk comparison
26, fold 56 and flag comparison 28. Endpoint-fold parameter is 55. The special
halving/doubling correction uses the source helper's actual 88-carry ripple;
the 56-bit ordinary fused correction must not be assigned to those special cells.

Conservative: 736 rounds, margin 20, chunk comparison 40, replay fold 72,
endpoint parameter 71, flag comparison 48, and coordinate `TLM_MSBS=40`.
The final residual operands have width 11; special correction carries increase
to 104. Neither profile is asserted exact on every input. Jump-2 retains the
snapshot's 261-step schedule, finite-width tables and source-specific truncation
and specialization knobs. Exact arrays and all effective environment knobs are
archived rather than replaced by a single nominal precision parameter.

The unchanged conservative `eval_bounded` and its unchanged simulator were used
with shared seed `qip-accounting-smoke-20260908-v1`, `MIXED_WINDOW_BITS=4`,
`EVAL_TESTS=64`, and `EVAL_THREADS=1`. Input and expected-output columns are
verified identical for all six runs. Five addresses are j=0, outside the mixed
generic-affine interface. All six runs fail these five rows (indices 27,30,33,37,55).
Both ping-pong square variants additionally fail nonidentity row 50. Legacy
variants have no other failures in these 59 nonidentity cases. All phase and
ancilla failure counts are zero in this smoke sample. Original-default and
controlled ping-pong smoke outcomes agree. No failed row is excluded from costs.

The permissive error threshold `EVAL_MAX_ERROR_RATE=1` allows the evaluator to
finish and save every outcome; exit code 0 does **not** certify a clean circuit.
`smoke-failures.csv` and `runs/*/smoke/inputs.tsv` preserve all observed failures.
Only batch Toffoli totals divided by the batch's 64 cases are used. **No individual
or identity-subset T is inferred from bit-parallel totals.** The optional repeated
identity cost probe was not run: this evaluator has no direct fixed-address/input
injection option, and changing window width to zero would measure another circuit.

## 6. Failures, limits and reproduction

- macOS rejected an initial address-space rlimit before compilation. A subsequent
  attempt hit sandbox-denied process inspection. The final launcher uses approved
  process-group RSS monitoring and a 11000000-KiB stop threshold.
- A shared Cargo target reused incompatible same-package outputs, causing an
  unresolved `point_add` import for Jump-2. No circuit from those builds was used.
  All sources were rebuilt in separate target directories before experiments.
- The fast QROM count-model operation mismatches remain in `results.json` as
  expected superseded failures. Final `exact` checks pass.
- An initial stream-reader attempt inherited a buffered-file offset and failed
  zstd decoding. The fixed reader opens the file unbuffered and validates framing,
  tags, record count and final decompressor status.
- No large-memory, large-corpus, nonce, full-Shor, or individual-identity-cost run
  was attempted. Static cost and empirical accuracy are intentionally separate.

From the workspace root, a clean reproduction is:

```sh
python3 outputs/qip2027-mechanism-revision-20260908/accounting/prepare.py copy
python3 outputs/qip2027-mechanism-revision-20260908/accounting/prepare.py instrument
python3 outputs/qip2027-mechanism-revision-20260908/accounting/run.py build-original
python3 outputs/qip2027-mechanism-revision-20260908/accounting/run.py bounded-all
python3 outputs/qip2027-mechanism-revision-20260908/accounting/exact_qrom.py
python3 outputs/qip2027-mechanism-revision-20260908/accounting/analyze.py
python3 outputs/qip2027-mechanism-revision-20260908/accounting/verify.py
python3 outputs/qip2027-mechanism-revision-20260908/accounting/test_accounting.py
python3 outputs/qip2027-mechanism-revision-20260908/accounting/finalize.py
```

`prepare.py instrument` intentionally refuses to overwrite existing copies. For
this already populated delivery, use `analyze.py` and `verify.py` to reproduce
the analysis without rerunning experiments. Offline Cargo builds use rustc 1.93.0,
2 Cargo jobs, one codegen unit, LTO disabled, at most 4 configured Rayon/OpenMP
threads, and serial circuit runs. Only one simulator/circuit vector is resident
at a time. `commands.jsonl` records timing, commands, settings and sampled RSS;
`logs/` includes `/usr/bin/time -l` output. No >12-GB run was launched.

## Files

- `results.json`, `summary.csv`: complete resource ledgers, identity/count checks,
  matched-control checks and smoke summaries.
- `integration-summary.json`, `integration-ledger.csv`: selected verified data
  for manuscript integration, with accounting and accuracy scope attached.
- `verification.json`: protected-file audit, frozen/raw accounting reconciliation,
  evaluator hash, and maximum sampled process-group memory.
- `runs/*/{owners,phases,allocator,emitter-settings}.tsv`: allocation-site witnesses
  and source-phase counts. Prefer `*-exact-count` for full-window accounting.
- `runs/*/{ops.bin,stream.json,result.json}`: bounded emitted circuits, stream
  fingerprints and emission status. Count-only runs have no `ops.bin`.
- `runs/*/smoke/`, `smoke-failures.csv`: unchanged-evaluator inputs/outcomes,
  batch counts and all failures.
- `sources/`, `instrumented/`, `patches/`, `source-manifest.json`: own source
  copies, emitter-only instrumentation and provenance.
- `prepare.py`, `accounting.rs`, `run.py`, `exact_qrom.py`, `analyze.py`, `verify.py`:
  reproduction tools. `update_instrumentation.py` records an earlier migration
  and is not needed by the clean-reproduction sequence.
- `commands.jsonl`, `logs/`, `STATUS.json`, `FILE_LIST.txt`: execution history,
  clear result status and complete delivery inventory.
