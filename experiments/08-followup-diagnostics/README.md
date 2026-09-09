# 08. Follow-Up Diagnostics for the 37-Page Manuscript

Published in **v1.2.0**. These post-hoc diagnostics supplement Appendix C.4.
They do not change any frozen circuit, prior validation result, or v1.0.0/v1.1.0
scientific file. The later expensive canonical-replay reference is not included.

## Find a result

| Question | Record |
|---|---|
| Why does smoke input 50 fail? | [Analysis](targeted-analysis.json) and [all inverse-round traces](logs/ablation-pingpong-product-smoke.trace) |
| Do supported zero-slope points expose full-call phase failures? | [Exact fixtures](fixture-proof.json), [inputs](zero-slope.tsv), and [all circuit logs](logs/) |
| How often does the ideal recurrence exceed its budget? | [Ten-million-trial histogram](tail-10000000.json) |
| What happens to the guards on actual frozen corpus states? | [99,997-case guard analysis](guards-11112.json) |
| Which streams and measurement seed were used? | [Run receipts and hashes](targeted-runs.json), [diagnostic driver diff](diagnostic-driver.diff) |
| What was checked? | [Original seven-test receipt](test-results.txt), [publication verifier](verify.py) |

Start with [REPORT.md](REPORT.md) for findings and limits. In particular, the
zero-slope runs use **two points repeated over 32 measurement lanes each**.
They are not 64 independently sampled point pairs. The complete-call tests
have four-bit windows, not the frozen study's sixteen-bit windows. No repair,
population failure rate, or full-Shor success claim follows from them.

## Verify without running circuits

From the repository root:

```sh
python3 -B experiments/08-followup-diagnostics/verify.py
```

This uses Python 3.11+ and the standard library. It verifies package hashes,
the 148 original files (with original README/report archived under provenance),
all retained summaries, six scalar/source regression tests, and recomputes
the 702-round trace correspondence plus 246 final lane comparisons in temporary
storage. It does not rewrite publication files or rerun circuits, the ten-million
study, or the optional GMP/Python crosscheck. Root `scripts/verify.py` includes it.

## Reproduce in scratch space

All stages below write only to a prepared directory under this repository's
`.work/`. The original records and source trees remain read-only.

```sh
python3 experiments/08-followup-diagnostics/reproduce.py prepare
```

Use `--work-dir .work/another-new-directory` consistently to choose another
scratch directory. Existing prepare destinations and symlinked output paths
are refused.

### Exact denominator study

Requires a C compiler and GMP headers/library:

```sh
python3 experiments/08-followup-diagnostics/reproduce.py build-tail
python3 experiments/08-followup-diagnostics/reproduce.py tail --n 10000000
python3 experiments/08-followup-diagnostics/reproduce.py tests
```

The denominator file is regenerated from its documented seed and rejection rule.
It occupies 320 MB and is not included in GitHub. The original native loop took
about 197 seconds. Full reproduction compares every recorded histogram and
numeric field, excluding elapsed time. The 10,000-case pilot is a prefix, not
an additional independent sample. The optional tests include the 1,033-case
independent Python/GMP check.

### Guard model on the frozen corpus

```sh
python3 experiments/08-followup-diagnostics/reproduce.py guards
```

This runs on all nine original corpus strata, preserves noncanonical raw words
and operand correlations, and compares the new analysis to the retained record.
Identity-addend rows bypass replay and remain recorded as skipped. It is a
source-word diagnostic, not quantum circuit execution or a global phase-error
bound. The smaller pilot is a subset, not extra independent evidence.

### Targeted circuit execution

First follow the [experiment 06 rebuild guide](../06-resource-accounting/README.md)
to build both its accounting and ablation streams in a new scratch directory.
Both stages are needed. Then:

```sh
python3 experiments/08-followup-diagnostics/reproduce.py build-driver
python3 experiments/08-followup-diagnostics/reproduce.py targeted --streams-root /path/to/accounting-rebuild/runs
python3 experiments/08-followup-diagnostics/reproduce.py reanalyze
```

The copied diagnostic source, Cargo manifest, and lockfile are included under
`source/`. Cargo builds require cached locked dependencies and use
`--release --locked --offline`. The unchanged simulator/reference are checked
against the repository's conservative snapshot. The four streams, complete
64-lane inputs, phase boundaries, and seed are preserved. The runner compares
segmented and whole-stream execution and requires rebuilt scientific logs to
match. Compiled binaries and large operation streams are not included.

The original `run_*.py` scripts are preserved byte-for-byte for provenance.
Use the wrapper above, not those scripts in the publication directory: the
original scripts write derived outputs beside themselves. Absolute paths in
historical receipts are inert provenance, not reproduction destinations.

## Provenance

`provenance/original-manifest.json` anchors the supplied manuscript supplement.
Only the reader-facing README and report were adapted for publication, with
their originals retained alongside that manifest. Circuit sources, inputs,
logs, numerical results, and original scripts are unchanged. The current
`manifest.json` also covers the new publication/reproduction wrappers.
