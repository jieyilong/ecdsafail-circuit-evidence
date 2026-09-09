# ECDSA.Fail Circuit Evidence

Reader-facing evidence for the ECDSA.Fail point-addition manuscripts, including the September 8, 2026 frozen study and a separately identified correctness reference. This repository contains recorded inputs, outcomes, analysis, and source snapshots for inspection without running large circuits.

**Version 1.3.0** adds a separately identified [canonical-replay correctness reference](experiments/09-canonical-reference/README.md) for the alternate 34-page manuscript. It is more expensive than the low-cost circuits and is not a new benchmark record. All v1.0.0, v1.1.0, and v1.2.0 scientific files remain unchanged. The 35-page low-cost manuscript can continue to cite v1.2.0. See [citation guidance](docs/CITING.md), [the paper map](docs/PAPER_MAP.md), [release changes](CHANGELOG.md), and [publication checks](VERIFICATION.md). This is a research evidence package, not a challenge submission or an end-to-end Shor implementation.

## Main Result

Three single-call window-selected point-addition circuits were evaluated on the **same 100,000 inputs across nine table strata**. All use a 16-bit window and exact split-address QROM cleanup.

| Circuit | Peak qubits, Q | Mean executed Toffolis, T | Any-channel failures |
|---|---:|---:|---:|
| Original ping-pong | 1,338 | 1,127,527.39827 | 39 / 100,000 |
| Conservative ping-pong | 1,392 | 1,252,854.89397 | 0 / 100,000 |
| Jump-2 | 1,162 | 1,523,121.58073 | 215 / 100,000 |

Means include failed cases. Any-channel failures are the union of classical-output, phase, and ancilla flags, not their sum. [Full results](experiments/02-fresh-windowed/RESULTS.md) include channel counts and uncertainty. The [original analysis](experiments/02-fresh-windowed/analysis.json) retains full-precision values.

**Zero observed failures is not an all-input correctness claim.** A separate post-hoc zero-payload probe found noncanonical zero representations and phase flags in division and multiplication subroutines. Those diagnostics are not full point-addition trials and are not pooled with the frozen random study. Read [what the evidence establishes](docs/INTERPRETATION.md) before using these numbers as correctness or attack-cost estimates.

The newer [follow-up study](experiments/08-followup-diagnostics/README.md) also records phase failures in complete four-bit-window calls on two supported zero-slope points. These structured outcomes are distinct from both the earlier component probes and the frozen random study. No circuit repair is claimed.

## Start Here

The separate correctness reference uses **1,804 qubits and 5,188,043 static
Toffolis**, with mean 5,187,616.277587891 and 0 detected failures in a new
4,096-input pilot. These are full single-call window-selected resources, not
full-Shor costs. Its [source, failed attempt, and pilot](experiments/09-canonical-reference/README.md)
remain separate from the original table above.

| Reader task | Where to go |
|---|---|
| Find a paper table or distinguish September 7 from September 8 data | [Paper map](docs/PAPER_MAP.md) |
| Read the numerical summaries | [Results](RESULTS.md) and [summary CSV](experiments/02-fresh-windowed/summary.csv) |
| Understand a ledger row, failure flag, or statistic | [Data dictionary](docs/DATA_DICTIONARY.md) |
| Verify the records or repeat execution | [Reproduction guide](docs/REPRODUCTION.md) |
| Check source identities and the relocation from the original ZIP | [Provenance](docs/PROVENANCE.md) |
| Inspect the matched backend ablation and live resource ledgers | [Resource accounting](experiments/06-resource-accounting/README.md) |
| Reproduce the boundary witnesses and inspect failed repair hypotheses | [Boundary diagnosis](experiments/07-boundary-diagnosis/README.md) |
| Inspect Appendix C.4: smoke outlier, zero-slope calls, round tail, and guard checks | [Follow-up diagnostics](experiments/08-followup-diagnostics/README.md) |
| Inspect the alternate 34-page high-cost reference and its pilot | [Canonical reference](experiments/09-canonical-reference/README.md) |

## Verify Without Running Circuits

From the repository root, using Python 3.11 or later:

```sh
python3 scripts/verify.py --output .work/verification.json
python3 scripts/results.py --check
python3 scripts/query_case.py --candidate original-pingpong --stratum G-s0 --index 0
```

Default verification uses only the Python standard library. It reconstructs the original layout, reruns the frozen analysis, and verifies the added mechanism packages and scalar calculations. It does not execute circuits or invoke the optional independent classical oracle. Builds and circuit runs are separate, explicit steps and can require about 32 GiB of RAM and hours of runtime. See the individual experiment guides for the smaller diagnostic runs.

## Evidence Layout

| Directory | Contents and role |
|---|---|
| [01-development](experiments/01-development/README.md) | All five 16,384-case mixed-addition configurations, including unsuccessful ones. Used for parameter selection. |
| [02-fresh-windowed](experiments/02-fresh-windowed/README.md) | Frozen comparison: 100,000 shared inputs, 300,000 outcome rows, nine strata, three circuits. |
| [03-evaluator-equivalence](experiments/03-evaluator-equivalence/README.md) | Official and auxiliary evaluator records on the same 8,192 mixed-addition cases. |
| [04-coordinate-phase](experiments/04-coordinate-phase/README.md) | Stage trace localizing development case 6828. Diagnostic only. |
| [05-zero-payload](experiments/05-zero-payload/README.md) | Guide to the separate 64-denominator component probe in each direction. |
| [06-resource-accounting](experiments/06-resource-accounting/README.md) | Controlled 2x2 backend/square experiment, live allocation and static phase ledgers, retained smoke failures, portable source snapshots. |
| [07-boundary-diagnosis](experiments/07-boundary-diagnosis/README.md) | Representation and phase witnesses, failed widening hypotheses, local negation regression, and offline source replay. |
| [08-followup-diagnostics](experiments/08-followup-diagnostics/README.md) | Smoke-failure diagnosis, supported-domain full-call witnesses, 10-million-denominator tail, and 99,997-case replay-guard model. |
| [09-canonical-reference](experiments/09-canonical-reference/README.md) | Separate high-cost correctness reference, failed replay-only attempt, targeted regression, and 4,096-input pilot. |
| [supporting/comparison](supporting/comparison/report.md) | Primary-source resource-boundary audit and exact sampling-bias calculations. |
| [supporting/algebra](supporting/algebra/check_value_replay.py) | Exact small-prime value/replay identity checks, not circuit validation. |
| [supporting/replay-analysis](supporting/replay-analysis/README.md) | Preserved local 446-to-393 replay-cell evidence and scalar fusion checks. |
| [sources/archives](sources/archives/) | Byte-identical original source archives. |
| [sources/trees](sources/trees/) | Browsable copies of archive contents, omitting only recorded cached bytecode. |
| [sources/frozen-tools](sources/frozen-tools/) | Original experiment and analysis scripts. |
| [provenance](provenance/) | Freeze, path map, source hashes, original packaging files, and rebuild receipt. |

The new `scripts/` commands provide relocation, reporting, and reproduction conveniences. They do not replace the frozen scientific analysis. Execution artifacts go under `.work/`, never over the original records. `results.py` regenerates only the derived reader-facing reports.

The older September 7 seven-circuit comparison and its 700,000 outcome rows are **separate evidence**, not included here. The [paper map](docs/PAPER_MAP.md#separate-september-7-evidence) points to pinned releases for those distinct comparisons. No paper PDF or arXiv upload is included. See [attribution and reuse](THIRD_PARTY_NOTICES.md), the [upstream notice](sources/UPSTREAM_NOTICE.txt), and [CITATION.cff](CITATION.cff).
