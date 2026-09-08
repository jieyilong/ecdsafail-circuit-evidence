# 07. Bounded Boundary Diagnosis

Portable evidence package for `experiments/07-boundary-diagnosis`.

**Finding:** zero-to-`p` representation changes, carry-erasure phase errors, and
nonzero coefficient resets are established in raw emitted cells and isolated
probe components. This is **not** an entire-kernel zero-error claim or a general
zero-payload repair. The local canonical-negation candidate is not integrated.
See [REPORT.md](REPORT.md) for the detailed mechanisms and exact gate witnesses.
The [wording addendum](WORDING_ADDENDUM.md) corrects the pre-release observation
to **35 nonzero registers, with fixture 4 confirmed as `p`**, not 35 words proven
equal to `p`.

## Verify Offline

From this directory, using Python 3.11 or newer:

```sh
python3 -B verify.py
```

This is read-only and uses only Python's standard library. It needs no network,
Rust installation, original workspace, repository checkout, or absent frozen
source tree. The directory may be relocated or renamed without editing paths.
Verification checks the package manifest, copied-source hashes, preserved patch,
simulator/reference/evaluator identity, nine retained final raw logs, local
boundary/negative findings, exact value-walk prechecks, and dependency coverage.

`metadata/stage-verification.json` is the new staging receipt. It is separate
from the original eight-test diagnosis receipt in
`provenance/original/test-results.json`. The portable verifier reports **seven
check groups**, not a fresh execution of the old workspace-dependent tests.

## Rebuild And Replay Offline

Prerequisites: Python 3.11+, installed Rust/Cargo (tested with Rust 1.93.0), a
native C compiler/linker for `zstd-sys`, and enough RAM for the approximately
411 MB isolated-component operation vector plus normal process/build overhead.
No preexisting Cargo registry cache is needed. Locked third-party sources,
including their licenses and Cargo checksums, are bundled in
`dependencies/vendor.tar.gz`.

Choose a **new directory outside this package**:

```sh
python3 -B rebuild.py --work-dir /tmp/qip07-offline-rebuild
```

The directory must not already exist. The runner verifies this package, copies
its source, expands the vendored dependency archive, starts with an empty
`CARGO_HOME`, and builds with `--frozen --offline` and one Cargo job. It then
runs all nine retained diagnostics sequentially and requires their raw logs to
match byte-for-byte. It never calls the default full-circuit emitter: every
execution supplies the diagnostic entrypoint variable explicitly.

The original and staged source trees remain untouched. Compiled binaries,
expanded dependencies, temporary files, new logs, and `rebuild-verification.json`
stay in the external work directory. No `target/` or compiled `bin/` output is
included in this release. `source/src/bin/` contains the **required Rust source
entrypoints**, including unchanged evaluator sources, not compiled executables.

## Provenance Versus Staging

- `provenance/original/` contains verbatim original manifests, protocol, report,
  runtime, and the eight-test receipt. These are historical records, not new
  claims that the portable verifier has reread the external frozen repository.
- `provenance/original-run-receipts/` preserves all nine final run receipts
  byte-for-byte. Their absolute paths are **historical metadata only** and are
  never followed or executed by the portable scripts.
- `provenance/lineage.json` records SHA-256 anchors for the original manifests
  and the mapping from original artifacts to staged copies. New stage files are
  hashed independently in `manifest.json`.
- `provenance/upstream-files/` includes the original versions of all modified
  source files, plus the conservative replay file. The verifier reconstructs
  `patches/diagnostic-source.diff` from these bundled files and the staged source.
  Unmodified source files are checked directly against recorded frozen hashes.
- The simulator, circuit definitions, field/curve reference, evaluator sources,
  Cargo manifest, and lockfile remain byte-identical. The diagnostic Rust tree
  itself is also byte-identical to the verified original diagnosis snapshot.
- The original report is retained under `provenance/original/REPORT.md`. Its P2
  wording correction is documented in `WORDING_ADDENDUM.md`,
  `provenance/editorial-correction.json`, and
  `patches/scientific-wording-correction.diff`. The corrected scientific report
  is preserved under `provenance/corrected/REPORT.md`; subsequent packaging
  paths/instructions are recorded separately in `patches/portable-report.diff`.
- `metadata/rebuild-verification.json` and its input manifest record the offline
  rebuild performed before the editorial correction. Source, dependencies, and
  all nine raw logs remain identical; no new circuit experiment was run for the
  wording change. Current staging verification is regenerated after correction.

These checks establish artifact integrity and recorded byte-hash lineage. They
do not authenticate a remote publication or silently substitute the staged
verification for independent verification of an external upstream checkout.

## Contents

| Path | Purpose |
|---|---|
| `source/` | Complete copied diagnostic source and original input fixtures |
| `patches/` | Diagnostic source diff and portable-report adaptation |
| `logs/` | Nine final raw logs only, including negative findings |
| `cell-summary.csv`, `cell-summary.json` | Recomputed summaries of the three final cell grids only |
| `component-summary.json`, `trace-excerpts.log` | Component/reset counts and selected gate traces |
| `value-walk.json` | Exact fixture prechecks and rejected small-denominator prechecks |
| `verify.py`, `rebuild.py` | Standalone offline verification and rebuild/replay |
| `analyze.py`, `summarize_component.py`, `value_walk.py` | Portable analysis derivations; running these rewrites their derived outputs |
| `dependencies/` | Compressed, locked dependency sources and vendor metadata |
| `provenance/` | Original evidence anchors, run receipts, and upstream patch bases |
| `metadata/` | New staging/rebuild verification receipts |
| `manifest.json` | New package integrity manifest |

Earlier intermediate logs, original workspace-dependent runners/tests, build
outputs, and executables are deliberately omitted. Original diagnosis files
were retained outside this package. The manifest excludes only itself and the
self-referencing stage-verification receipt. No public push was performed.
