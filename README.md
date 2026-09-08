# ECDSA.Fail Circuit Evidence

Reader-facing evidence for the September 8, 2026 conservative ping-pong and fresh multi-table study in the ECDSA.Fail manuscript. This repository contains the recorded inputs, outcomes, analysis, and source snapshots needed to inspect the results without running large circuits.

**Version 1.0.0** preserves the original study in a reader-facing layout. See [citation guidance](docs/CITING.md) for versioned references, [the paper map](docs/PAPER_MAP.md) for the corresponding manuscript tables, and [publication checks](VERIFICATION.md). This is a research evidence package, not a challenge submission or an end-to-end Shor implementation.

## Main Result

Three single-call window-selected point-addition circuits were evaluated on the **same 100,000 inputs across nine table strata**. All use a 16-bit window and exact split-address QROM cleanup.

| Circuit | Peak qubits, Q | Mean executed Toffolis, T | Any-channel failures |
|---|---:|---:|---:|
| Original ping-pong | 1,338 | 1,127,527.39827 | 39 / 100,000 |
| Conservative ping-pong | 1,392 | 1,252,854.89397 | 0 / 100,000 |
| Jump-2 | 1,162 | 1,523,121.58073 | 215 / 100,000 |

Means include failed cases. Any-channel failures are the union of classical-output, phase, and ancilla flags, not their sum. [Full results](experiments/02-fresh-windowed/RESULTS.md) include channel counts and uncertainty. The [original analysis](experiments/02-fresh-windowed/analysis.json) retains full-precision values.

**Zero observed failures is not an all-input correctness claim.** A separate post-hoc zero-payload probe found noncanonical zero representations and phase flags in division and multiplication subroutines. Those diagnostics are not full point-addition trials and are not pooled with the frozen random study. Read [what the evidence establishes](docs/INTERPRETATION.md) before using these numbers as correctness or attack-cost estimates.

## Start Here

| Reader task | Where to go |
|---|---|
| Find a paper table or distinguish September 7 from September 8 data | [Paper map](docs/PAPER_MAP.md) |
| Read the numerical summaries | [Results](RESULTS.md) and [summary CSV](experiments/02-fresh-windowed/summary.csv) |
| Understand a ledger row, failure flag, or statistic | [Data dictionary](docs/DATA_DICTIONARY.md) |
| Verify the records or repeat execution | [Reproduction guide](docs/REPRODUCTION.md) |
| Check source identities and the relocation from the original ZIP | [Provenance](docs/PROVENANCE.md) |

## Verify Without Running Circuits

From the repository root, using Python 3.10 or later:

```sh
python3 scripts/verify.py --output .work/verification.json
python3 scripts/results.py --check
python3 scripts/query_case.py --candidate original-pingpong --stratum G-s0 --index 0
```

Default verification uses only the Python standard library. It reconstructs the original layout in temporary storage, verifies the original records, and reruns the frozen analysis. It does not execute circuits or invoke the optional independent classical oracle. Builds and circuit runs are separate, explicit steps and can require about 32 GiB of RAM and hours of runtime.

## Evidence Layout

| Directory | Contents and role |
|---|---|
| [01-development](experiments/01-development/README.md) | All five 16,384-case mixed-addition configurations, including unsuccessful ones. Used for parameter selection. |
| [02-fresh-windowed](experiments/02-fresh-windowed/README.md) | Frozen comparison: 100,000 shared inputs, 300,000 outcome rows, nine strata, three circuits. |
| [03-evaluator-equivalence](experiments/03-evaluator-equivalence/README.md) | Official and auxiliary evaluator records on the same 8,192 mixed-addition cases. |
| [04-coordinate-phase](experiments/04-coordinate-phase/README.md) | Stage trace localizing development case 6828. Diagnostic only. |
| [05-zero-payload](experiments/05-zero-payload/README.md) | Guide to the separate 64-denominator component probe in each direction. |
| [sources/archives](sources/archives/) | Byte-identical original source archives. |
| [sources/trees](sources/trees/) | Browsable copies of archive contents, omitting only recorded cached bytecode. |
| [sources/frozen-tools](sources/frozen-tools/) | Original experiment and analysis scripts. |
| [provenance](provenance/) | Freeze, path map, source hashes, original packaging files, and rebuild receipt. |

The new `scripts/` commands provide relocation, reporting, and reproduction conveniences. They do not replace the frozen scientific analysis. Execution artifacts go under `.work/`, never over the original records. `results.py` regenerates only the derived reader-facing reports.

The older September 7 seven-circuit comparison and its 700,000 outcome rows are **separate evidence**, not included here. The [paper map](docs/PAPER_MAP.md#separate-september-7-evidence) points to pinned releases for those distinct comparisons. No paper PDF or arXiv upload is included. See [attribution and reuse](THIRD_PARTY_NOTICES.md), the [upstream notice](sources/UPSTREAM_NOTICE.txt), and [CITATION.cff](CITATION.cff).
