# QIP manuscript follow-up diagnostics

This is a new, post-hoc diagnostic study. It does not change the frozen circuits,
the September 8 validation corpus, or evidence releases v1.0.0 and v1.1.0. It is
not yet a published GitHub release. See `REPORT.md` for results and limitations.

## Start here

| Reader question | Evidence |
|---|---|
| Why did smoke input 50 fail? | `targeted-analysis.json`, `logs/ablation-pingpong-product-smoke.trace` |
| Can zero slope occur on supported inputs? | `fixture-proof.json`, `zero-slope.tsv`, `logs/*zero-slope.tsv` |
| How often does the ideal recurrence exceed the round budget? | `tail-10000000.json` |
| What happens to replay guard predicates on actual corpus states? | `guards-11112.json` |
| Which unchanged circuits were executed? | `targeted-runs.json` and their operation-stream SHA-256 hashes |
| What was checked independently? | `test-results.txt`, `test_diagnostics.py` |

The `source/` directory contains a copy of the conservative source tree and one
added diagnostic binary, `src/bin/eval_followup.rs`. That binary retains the
original bounded loader and adds explicit fixture loading and intermediate-state
reads. The simulator, circuit definitions, classical elliptic-curve reference,
original evaluator, and dependency lockfile are unchanged. It never calls the
circuit emitter. Existing gate streams are inputs, not regenerated silently.

## Verify records and scalar correspondence

Python 3.11+ is sufficient for these commands. The second regenerates only the
derived targeted analysis in this directory, never the recorded circuit logs:

```sh
python3 -B verify_records.py
python3 -B analyze_targeted.py
```

## Reproduce circuit tests

Use the public evidence repository at revision
`5607f772d707b2a2f7fd2e0cff43b5716bac744b`. Follow its
`experiments/06-resource-accounting/README.md` to rebuild accounting and ablation
streams in a new scratch directory. Both stages are needed. This provides the
four named run directories used here. No large operation streams or native
executables are included in this supplement.

```sh
python3 -B prepare_inputs.py --evidence-root /path/to/ecdsafail-circuit-evidence
cargo build --manifest-path source/Cargo.toml --release --locked --offline --bin eval_followup --target-dir target
TRACE_ALL=1 python3 -B run_targeted.py --streams-root /path/to/accounting-rebuild/runs
python3 -B analyze_targeted.py
```

Rust/Cargo and the pinned dependency sources in the Cargo cache are required.
The test driver uses the original smoke measurement seed, checks the original
reference sums, rejects trace boundaries crossing classical condition scopes,
and requires segmented and unsegmented final outputs to match exactly. All 64
lanes are retained. Zero-slope tests use **two inputs, each repeated over 32
measurement lanes**, not 64 independent random points. The recorded absolute
command paths are historical metadata. `--streams-root` selects rebuilt inputs.

## Reproduce the denominator study

Requires a C compiler and GMP headers/library. On a system with GMP in the
standard search path:

```sh
cc -O3 round_tail.c -lgmp -o round_tail
python3 -B run_tail.py --n 10000000
```

On Apple Silicon with Homebrew GMP, add `-I/opt/homebrew/include` and
`-L/opt/homebrew/lib` to the compiler command. This run used GMP on macOS and
took approximately 197 seconds after generating the 320 MB denominator file.
That generated file is omitted because its seed, byte layout, rejection rule,
and SHA-256 are recorded. The 10,000-input pilot is a prefix of the same study,
not an additional independent sample. Values are exact signed integers. No
payload, phase, or full Shor execution is modeled by this test.

## Reproduce replay guard diagnostics

```sh
python3 -B run_guards.py --per-stratum 11112 --evidence-root /path/to/ecdsafail-circuit-evidence
ECDSAFAIL_EVIDENCE_ROOT=/path/to/ecdsafail-circuit-evidence python3 -B test_diagnostics.py
```

The full prefix length covers all nine frozen strata. Identity-addend cases are
recorded as skipped because the replay subroutine is not called for them.
The 1,000-per-stratum pilot is a subset, not additional independent evidence.
The model propagates raw 256-bit payload representations and correlated states,
checks the 40-bit chunk predicate, 72-bit ordinary correction range, and 48-bit
overflow predicate, and distinguishes prefix misses from full-width predicate
defects. It also checks signed value widths and endpoint value corrections.
It does **not** certify specialized seed/endpoint phase cleanup, coordinate
arithmetic guards, complete measurement branches, or full-Shor error.
No per-call success probability is inferred from a zero predicate-disagreement
count. This is diagnosis of a previously evaluated corpus, not a fresh circuit
validation campaign.

## Preservation

The publication script creates `manifest.json` over the portable files and
copies this directory into the manuscript supplement. Build directories,
native executables, generated denominator bytes, and QA images are excluded.
The original arXiv manuscript, author list, contributor appendix, and extended
abstract are not changed by this study.
