# 06. Bounded Resource Accounting

Portable staging for `experiments/06-resource-accounting` in the evidence repository.
The directory is self-contained and may also be placed anywhere else. No publication
or push is performed. Original experiment receipts are preserved byte-for-byte.

## Verify Offline

From this directory:

```sh
python3 -B verify.py
```

Requires **Python 3.11 or newer, standard library only**. It does not need Rust,
zstd, network access, executables, the original workspace, or the parent evidence
repository. It is read-only and does not rewrite the recorded `verification.json`,
freeze, ledgers, or checksums. A successful run prints JSON with `status: PASS`.
`PORTABILITY_TEST.json` records the exact tested command and relocation test.

To verify from another working directory, supply the package path to `--root`.
`--root` also recognizes an evidence repository containing
`experiments/06-resource-accounting`. `ACCOUNTING_RELEASE_ROOT` is an alternative.
The default is always the verifier's own directory, not the shell's current directory.

The verifier checks package hashes, all 521 ZIP members, 259 original-source file
hashes, the emitter-only modification boundary, phase/owner sums, common inputs,
all smoke failures, matched backend settings, and equality of reconstructed results
with the recorded results. It reconciles the full-window counts with the **copied,
unchanged** `provenance/freeze.json`.

**Stream hashes are receipts here, not a fresh stream verification.** The 12
instrumentation identity comparisons are checked for consistency with their
recorded hashes/counts. `ops.bin` and compiled executables are deliberately omitted,
so neither full gate streams nor historical executable hashes are remeasured.
No individual identity-address cost is inferred from the 64-shot batch totals.

## Results and Inputs

- `receipts/integration-summary.json` and `receipts/integration-ledger.csv`: selected
  resource/ablation data for integration, with scope and caveats.
- `receipts/results.json`, `receipts/summary.csv`: complete recorded analysis.
- `receipts/runs/`: phase ledgers, simultaneous allocation-site ownership, effective
  configurations, stream fingerprints, emission receipts, and all small smoke rows.
- `receipts/REPORT.md`: original scientific report, preserved unchanged. Its
  workspace-specific commands describe the historical execution; use **this README's
  commands**, not that archived command block, for portable verification/rebuilds.
- `receipts/logs/`, `receipts/commands.jsonl`, `receipts/patches/`: historical logs and
  diffs, including superseded failures. Embedded absolute paths are inert provenance
  strings, never resolved by the verifier or used to choose rebuild destinations.
- `source-snapshots.zip`: all three original and final instrumented source snapshots,
  Cargo manifests/locks included. ZIP timestamps and permissions are deterministic.
- `source-archive-manifest.json`, `receipt-copy-manifest.json`: complete member/source
  hashes and receipt copy hashes. `package-manifest.json` seals the portable payload.

The original/conservative window peaks are 1338/1392 and Jump-2 is 1162. Mixed
ping-pong peaks at 1321. The matched legacy-square/no-postcompiler backend contrast
is 1357682 versus 1017240 static Toffolis. The full 2x2 and its 8-Toffoli downstream
interaction are retained. All six smoke runs have failures; a successful verifier
means the evidence is internally consistent, **not that the circuits are exact**.

## Optional Rebuild

Source rebuilds require a compatible Rust toolchain (tested original experiment:
rustc 1.93.0), C/C++ build tools, and all `Cargo.lock` dependencies already in the
local Cargo cache. Dependency sources are **not vendored** in this compact package.
Cargo uses `--locked --offline` and never falls back to downloading. A missing
dependency causes a clear build failure. The launcher accommodates macOS and Linux
`time` flags. The original experiments were built on macOS; portable source
extraction is tested, but a fresh Rust compilation through this staged launcher
has not been rerun. Linux execution is not claimed tested.

Create a new scratch directory and inspect/extract the verified sources:

```sh
python3 -B rebuild.py prepare --work-dir ./_work/reproduction
```

Both source trees per backend come from the bundled ZIP, so no frozen snapshot is
rewritten. When placed in the evidence repository, `prepare` automatically checks
the parent `sources/trees` against the bundled source hashes, read-only. An explicit
`--evidence-root` can supply that check in another layout. All later writes go to
`--work-dir`; existing prepared destinations and existing run receipts are refused.

Build the original and instrumented emitter binaries plus unchanged evaluator:

```sh
python3 -B rebuild.py build --work-dir ./_work/reproduction
```

Run the four mixed-interface ablation cells and their 64-common-input smoke checks:

```sh
python3 -B rebuild.py ablation --work-dir ./_work/reproduction
```

Run the baseline and full-window counting ledgers, with real-QROM counting and
small-window emission crosschecks (full 16-bit streams are never materialized):

```sh
python3 -B rebuild.py accounting --work-dir ./_work/reproduction
```

Alternatively, after `prepare`, `rebuild.py all` performs build, ablation and
accounting in that order. Do not invoke `all` after the individual stages in the
same scratch directory. Use a fresh scratch directory for another run.

Rebuild stages preserve the current experiment's source settings, fixed identity
tails, permissive smoke completion threshold, and all failures. They make no nonce
search. Launches are serial, with two Cargo jobs, one codegen unit, four configured
Rayon/OpenMP threads, and one simulation thread. An RSS watchdog stops a process
group above 11000000 KiB, below the original 12-GB notification boundary. Process
inspection permission is required. No watchdog bypass is provided.

For an independently rebuilt small circuit, remeasure its decompressed fingerprint
and static operation counts (this separate command requires the `zstd` CLI):

```sh
python3 -B check_stream.py ./_work/reproduction/runs/ablation-pingpong-product/ops.bin
```

Compare this output to
`receipts/runs/ablation-pingpong-product/stream.json`. Compiler executable hashes
may differ across hosts. A stream discrepancy must be reported, not repaired by
editing the frozen receipts. The default verifier always verifies **the shipped
receipts**, not newly emitted scratch results.

## Size and Limitations

`STAGING.json` gives staged bytes and exclusions. No bins, targets, build caches,
operation streams, or large intermediates are included. No new simulation, nonce
search, full-corpus validation, or public push is part of this staging task.
Offline verification is fully self-contained; offline rebuilding additionally
depends on an already populated Cargo cache. Historical reports and logs retain
their original paths as provenance only.
