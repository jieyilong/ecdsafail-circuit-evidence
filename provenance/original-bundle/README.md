# Frozen Multi-Table Evaluation and Conservative Ping-Pong Study

This release supports the bounded QIP manuscript revision. It is not a challenge submission or an end-to-end Shor implementation.

## Reconstruct the Numerical Evidence

From this directory, run:

```sh
python3 package_evidence.py verify .
```

Python 3.10 or later with its standard library is sufficient. The command losslessly reconstructs all 27 raw final ledgers in a temporary directory and checks their original SHA256 hashes, including the original parallel completion order. It then runs the analysis frozen before the fresh corpus was generated. It checks all 300,000 outcome rows, every batch marginal, all channel unions, the common inputs, and the reported statistics. It also checks the five 16,384-case development ledgers and the 8,192-case official/auxiliary equivalence comparison. It does not execute the circuits.

With the Python `cryptography` package installed, additionally run:

```sh
python3 package_evidence.py verify . --oracle
```

This reconstructs the fresh SHAKE input stream, table-selected points, and expected sums for all 100,000 distinct final cases with OpenSSL secp256k1 scalar multiplication. It independently checks the classical reference data, not the circuit's phases or coherent action.

## Evidence Identity and Scope

- `freeze.json`: source versions, settings, static counts, operation hashes, evaluator and analysis hashes, and the pre-input freeze timestamp.
- `fresh-corpus-spec.json`: subsequently generated master seed, domain-separated stratum seeds, two synthetic public-point scalars, and nine table specifications.
- `analysis.json`: complete per-stratum and pooled summaries, confidence bounds, counted Clifford work, identity checks, and paired discordances.
- `oracle-check.json`: independent final reference reconstruction.
- `corpus/`: one copy of the input and reference columns per stratum.
- `results/`: all outcome columns, batch totals, original checkpoint manifests, execution configurations, logs, and completion receipts.
- `artifacts/code/`: unchanged scripts from the original freeze.
- `artifacts/source.tar.gz`: frozen conservative circuit, official and auxiliary evaluators, trusted core, and lockfile at commit `345c23fcf1073b7559a9d41e113f755259545bf2`.
- `supplementary/pingpong-base.tar.gz`: source at `2e0187c99fef038f079aaf76b6d36f64cce7481e`.
- `supplementary/jump2.tar.gz`: source at `080452804328698214f36655d95c9883be6a3080`.
- `supplementary/development/`: all five development outcomes, including failed configurations, and the development oracle receipt.
- `supplementary/coordinate-phase-trace.log`: diagnostic-only trace of batch 106. Its printed overall shot count is inherited and must not be interpreted as the number of inputs diagnosed. Only its stage phase masks are used.
- `supplementary/representation-probe.tar.gz`: separate post-hoc zero-payload probe, including source instrumentation, fixed inputs, and its report. It exposes noncanonical zero outputs and phase failures at subroutine level. It is not pooled with the random study and does not identify a full point-addition error rate.
- `supplementary/evaluator-equivalence/`: both complete 8,192-case ledgers and batch records.
- `supplementary/operator-reproduction.json`: byte-identical conservative-stream rebuild receipt, accompanied by the build log.

The release packaging and table-rendering helpers were written after the experiment freeze. They do not change the frozen statistical analysis. Equality markers abbreviate exact matching fields, not omitted successful cases. The original raw-file hashes are recovered after expansion.

Confidence bounds model independent pseudorandom inputs and measurement outcomes on the stated nine-stratum allocation. They are not all-input guarantees, coherent-error bounds, or full-Shor success estimates. No failed final inputs were discarded. No circuit parameters changed after final outcomes were inspected.

## Repeat Circuit Execution

The large operation streams and platform-specific binaries are omitted. Their recorded hashes remain in `freeze.json`. A portable rebuild may change the native binary hash even when the decoded operation stream and outcomes agree. Do not overwrite the original freeze or claim that a newly built binary was the originally frozen binary.

Extract each source archive into a separate clean directory. In each directory, build the emitter:

```sh
cargo build --release --locked --bin build_circuit
```

For the conservative source, also build the auxiliary evaluator:

```sh
cargo build --release --locked --bin eval_bounded
```

Add `--offline` only when Cargo dependencies are already cached. The original build used Rust 1.93.0. Emit each stream with the exact settings for its candidate in `freeze.json`, starting from a minimal environment without inherited arithmetic overrides. All three use:

```sh
WINDOWED_MODE=1 WINDOW_BITS=16 SINGLE_CCX_FANOUT_DISABLE=1 \
WINDOWED_QROM_UNLOAD=split ./target/release/build_circuit
```

Only the conservative source additionally sets `QIP_PINGPONG_PROFILE=guarded` and `TLM_MSBS=40`. Check the emitted `ops.bin` hash against its candidate entry. If compression versions differ, also inspect the decoded fingerprint using the bundled `stream_fingerprint.py` before classifying the difference. Do not silently accept a changed instruction stream as the frozen artifact.

For each of the nine strata in `fresh-corpus-spec.json`, place the chosen stream as `ops.bin` in a new case directory. Run the conservative source's `eval_bounded` binary there with these settings, substituting the exact stratum values:

```sh
WINDOWED_MODE=1 WINDOW_BITS=16 WINDOWED_SEQUENCE_CALLS=1 \
WINDOWED_TESTS=<stratum-n> WINDOWED_MAX_ERROR_RATE=1 EVAL_THREADS=8 \
EVAL_SHARED_SEED=<stratum-seed> QIP_TABLE_BETA=<stratum-beta> \
EVAL_CHECKPOINT_DIR=<new-checkpoint-directory> \
<absolute-path-to-eval_bounded> --note frozen-study-reproduction
```

An allowed-error value of one retains all failures and is not an acceptance threshold. Use at least two workers to select the existing checkpointed batch-seeding scheme. The original experiment ran cases sequentially with eight workers because each loaded windowed stream uses substantial memory. Do not use the diagnostic-only evaluator for these totals.

The auxiliary evaluator changes host-side table construction, table-aware checkpoint identity, and output-only bookkeeping. Simulator, counters, error checks, official evaluator, and reference curve source retain the hashes in `core_sha256`. An independent official-versus-auxiliary equivalence check agreed on all 8,192 mixed cases and all integer gate totals before the freeze.

The original `final_campaign.py` is included as an execution record. Its `run` command requires the omitted original binaries and streams and verifies their original byte hashes, so it is not a portable drop-in driver for freshly rebuilt native binaries. The commands above describe the source-based reproduction path without weakening those original checks.
