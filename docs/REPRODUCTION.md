# Reproducing the Evidence

## Added in v1.3.0

The [canonical-reference guide](../experiments/09-canonical-reference/README.md)
covers the separate high-cost reference from the alternate 34-page manuscript.
Default verification reconstructs its 4,096 recorded classical outputs and
checks source/record integrity without loading the omitted circuit. Rebuilding,
targeted execution, and the fresh pilot are separate explicit scratch-space
stages. This study is not pooled with the low-cost frozen comparison.

## Added in v1.2.0

The [Appendix C.4 guide](../experiments/08-followup-diagnostics/README.md) maps
the smoke trace, supported zero-slope calls, denominator tail, and guard model
to their retained records. Root verification includes its read-only checks.
Its reproduction wrapper prepares an isolated copy under `.work/` before any
experiment or derived-output command runs. GMP is optional and is needed only
for native denominator reproduction, not the default repository verification.

## Added in v1.1.0

The root `python3 scripts/verify.py` command now also verifies the two added mechanism packages and scalar calculations. Python 3.11 or later is required for this complete check. To verify only the added evidence, run `python3 scripts/verify_mechanism.py`. Both commands are offline unless the optional `--oracle` dependency needs installation, and neither executes circuits.

For rebuilding or replaying the new studies, use the [accounting guide](../experiments/06-resource-accounting/README.md) and [boundary guide](../experiments/07-boundary-diagnosis/README.md). These self-contained packages preserve their original staging receipts and paths as historical metadata. Accounting rebuilds need cached Cargo dependencies. The boundary package vendors its locked dependencies and records an offline rebuild/replay. The root `reproduce.py` commands below still target the original frozen study, not the new ablation or repair hypotheses.

The [local replay-cell guide](../supporting/replay-analysis/README.md) covers the preserved 446-to-393 cell evidence. The [external audit](../supporting/comparison/report.md) can be checked with `python3 supporting/comparison/check_accounting.py --math-only`, without local copies of the cited papers. This arithmetic-only mode does not rerun the source-document audit.

[Repository overview](../README.md) | [Data dictionary](DATA_DICTIONARY.md)

Run the commands below from the root of the versioned repository checkout. Original data and source records are immutable inputs. Build products, emitted streams, new ledgers, and verification receipts belong under `.work/`. The report command regenerates derived `RESULTS.md` and CSV summaries, not the original records.

## Choose a Reproduction Level

| Level | What it establishes | Requirements and cost |
|---|---|---|
| Read and query | Inspect summaries or one recorded case | No circuit execution. Python 3.10+ for queries. |
| Verify and reanalyze | Integrity, lossless reconstruction, ledger consistency, and agreement with frozen analysis | Python 3.10+ standard library. No Rust, oracle, or large operation streams. |
| Independent classical oracle | Reconstruct the fresh inputs, selected addends, and expected sums with a separate implementation | Optional pinned Python dependency. More work than default verification, but no circuit execution. |
| Build and emit | Recreate an operation stream from frozen Rust source and compare its identity | Rust/Cargo, compiler resources, and substantial disk space. |
| Smoke execution | Check the rebuilt circuit and evaluation path on a short prefix | Still loads a large circuit and can need substantial RAM. Not a new accuracy estimate. |
| Full execution | Compare newly executed inputs, outcomes, and batch counts with the frozen records | Budget about 32 GiB RAM and hours. Run candidates/strata sequentially. |
| Zero-payload probe | Repeat the isolated component diagnostic | Separate source entry point, not a fourth final-study circuit. |

## Verify the Recorded Evidence

```sh
python3 scripts/verify.py
python3 scripts/verify.py --output .work/verification.json
python3 scripts/results.py --check
```

The first two commands are alternatives, with the second retaining a JSON receipt. Verification checks the publication manifest and relocated bytes, reconstructs the original bundle layout in temporary storage, and invokes its original verifier. That verifier recovers all 27 raw final ledgers, including their completion order and hashes, and reruns the frozen analysis over 300,000 outcome rows. It also checks the five development ledgers and agreement on 8,192 evaluator-equivalence cases. No circuits run. CI uses standard-library verification, not the optional oracle or large circuit runs.

To regenerate the derived reader-facing reports instead of checking them:

```sh
python3 scripts/results.py
```

Inspect a recorded case using its zero-based index within a stratum:

```sh
python3 scripts/query_case.py --candidate original-pingpong --stratum G-s0 --index 0
```

This is a data query, not a one-case circuit rerun. Development case 6828 belongs to a different corpus and must not be looked up as fresh `G-s0` case 6828.

## Optional Classical Oracle

Default verification checks the saved oracle receipt but does not rerun the oracle. To independently reconstruct all 100,000 fresh input/reference cases:

```sh
python3 -m venv .work/oracle-venv
.work/oracle-venv/bin/python -m pip install -r requirements-oracle.txt
.work/oracle-venv/bin/python scripts/verify.py --oracle --output .work/verification-oracle.json
```

The optional requirements pin `cryptography==50.0.1`. The oracle uses cryptography/OpenSSL secp256k1 scalar multiplication to reconstruct the SHAKE input stream, table-selected points, and expected sums. It checks classical reference data, **not circuit phases or coherent action**. The separate [development oracle receipt](../experiments/01-development/oracle-check.json) records the original 16,384-case reference check.

## Build and Emit

The original builds used **Rust 1.93.0**, and the reproduction wrapper requires that version. Select it before building. Cargo builds use the unchanged archived `Cargo.lock` with `--locked`. Add `--offline` only when the required dependencies are already cached.

```sh
python3 scripts/reproduce.py build --candidate all
python3 scripts/reproduce.py emit --candidate original-pingpong
python3 scripts/reproduce.py emit --candidate conservative-pingpong
python3 scripts/reproduce.py emit --candidate jump2
```

For a narrower or offline build, select `original-pingpong`, `conservative-pingpong`, `jump2`, or `zero-payload-probe`:

```sh
python3 scripts/reproduce.py build --candidate conservative-pingpong --offline
```

All fresh runs use the conservative snapshot's `eval_bounded` binary. Build `conservative-pingpong` even when you only intend to run an original-pingpong or Jump-2 stream. `build --candidate all` already includes this evaluator and the separate probe emitter. `emit --candidate all` is also supported and emits only the three science circuits.

The wrappers build working copies and emit with a minimal environment so inherited arithmetic overrides do not change the circuit. Working destinations must be real directories under `.work/`, not symlinks into evidence or other directories. The authoritative settings are in [freeze.json](../provenance/freeze.json). All three science circuits set `WINDOWED_MODE=1`, `WINDOW_BITS=16`, `SINGLE_CCX_FANOUT_DISABLE=1`, and `WINDOWED_QROM_UNLOAD=split`. Only conservative ping-pong adds `QIP_PINGPONG_PROFILE=guarded` and `TLM_MSBS=40`.

Native binary hashes can differ by platform or toolchain. They are not interchangeable with operation-stream identities. Compare `ops_sha256` and the decoded `ops_fingerprint` with the freeze. A compressed-byte difference with matching decoded operations should be reported distinctly from a changed instruction stream. Never replace the original freeze with a new binary hash or silently accept different operations as the frozen circuit.

## Run a Smoke Test

After building and emitting the selected candidate:

```sh
python3 scripts/reproduce.py run --candidate conservative-pingpong --stratum G-s0 --smoke 128 --threads 8
```

This tests 128 cases, not the reported 100,000-case result. Smoke sizes must be multiples of 64, at least 128, and no larger than the stratum's case count. A short run still needs to load the full windowed stream, so it is not a low-memory substitute for verification.

## Repeat the Full Fresh Study

After emitting all three streams, an explicit full run is:

```sh
python3 scripts/reproduce.py run --candidate all --stratum all --threads 8
```

Valid individual strata are `G-s0`, `G-s128`, `G-s240`, `P1-s0`, `P1-s128`, `P1-s240`, `P2-s0`, `P2-s128`, and `P2-s240`. Select a single candidate and stratum to limit the workload.

The wrapper accepts two through eight evaluator workers to select the original checkpointed, batch-seeded randomness path. The recorded runs used eight workers. The allowed-error setting of one retains all failures, rather than terminating early. It is not a scientific acceptance threshold.

The reproduction driver compares new ledger inputs, outputs, flags, and batch counts with the originals and reports mismatches without rewriting them. Parallel completion order and elapsed time can differ. Compare cases by index and work by batch, not by the physical order of a newly produced file. A completed run is not sufficient evidence of reproduction if the comparison reports a mismatch.

## Repeat the Zero-Payload Diagnostic

```sh
python3 scripts/reproduce.py build --candidate zero-payload-probe
python3 scripts/reproduce.py zero-probe
```

This invokes the isolated emitter's diagnostic dispatch on the recorded fixtures. It is not a `cargo test --lib` result and is not included in `run --candidate all`. See [the diagnostic guide](../experiments/05-zero-payload/README.md) for expected observations and limits.

## Historical Commands and Troubleshooting

- Archived scripts and logs can contain local paths from the original machine. Use the new root-level commands above. Do not edit frozen files to make those paths portable.
- The original `final_campaign.py` checks the omitted original binaries and streams by byte hash. It is an execution record, not a portable driver for newly compiled binaries.
- A missing Cargo dependency in offline mode requires populating the dependency cache or rebuilding without `--offline`, not changing `Cargo.lock`.
- A hash or ledger mismatch stops the command and should remain visible in its error output and retained new files. Check the source snapshot, Rust version, emitted settings, stratum, and worker count before interpreting it. A success receipt is written only after its comparisons pass.
- Verification requires `provenance/publication-manifest.json`. A missing manifest means the checkout is incomplete for publication verification, not that the original experiment failed.
- Coordinate-phase diagnostic totals must never replace full-run counts. The selected-batch trace has an inherited, incorrect total-shot denominator.

The underlying analysis and experiment methods remain in [sources/frozen-tools](../sources/frozen-tools/). The new wrappers only make their evidence accessible in this layout.
