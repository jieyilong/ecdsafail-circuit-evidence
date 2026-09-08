# Paper-to-Evidence Map

[Repository overview](../README.md) | [Results](../RESULTS.md) | [Citation guidance](CITING.md)

This map follows the **30-page September 8, 2026 manuscript**. Section titles and LaTeX labels are included because table numbers can change between drafts. It does not describe the numbering of the earlier August manuscript.

## Evidence in This Repository

| Paper location | Subject | Evidence |
|---|---|---|
| Section 7.4, "Conservative Parameters and Fresh Multi-Table Validation" (`sec:bounded-validation`) | Parameter selection followed by a frozen fresh-corpus comparison | [Development](../experiments/01-development/README.md), [fresh study](../experiments/02-fresh-windowed/README.md), and [frozen protocol](../sources/frozen-tools/bounded_qip/PROTOCOL.md) |
| Table 5 (`tab:bounded-development`) | Five cumulative development configurations on 16,384 mixed-addition cases | [All five runs and summaries](../experiments/01-development/runs/) |
| Table 6 (`tab:fresh-operating-points`) | Resources, failures, and upper bounds for three fresh-study circuits | [Analysis JSON](../experiments/02-fresh-windowed/analysis.json), [outcome records](../experiments/02-fresh-windowed/runs/), and [freeze](../provenance/freeze.json) |
| Table 8 (`tab:fresh-strata`) | Any-channel failures in each of the nine table strata | [Corpus specification](../experiments/02-fresh-windowed/corpus-spec.json) and each circuit's `strata` entries in [analysis.json](../experiments/02-fresh-windowed/analysis.json) |
| Section 7.4, coordinate diagnosis | Development case 6828 and the wider coordinate-prefix check | [Coordinate-phase diagnostic](../experiments/04-coordinate-phase/README.md) |
| Section 7.4, evaluator and reference checks | 8,192-case evaluator agreement and independent classical reference reconstruction | [Evaluator equivalence](../experiments/03-evaluator-equivalence/README.md), [fresh oracle receipt](../experiments/02-fresh-windowed/oracle-check.json), and [development oracle receipt](../experiments/01-development/oracle-check.json) |
| Section 7.4, "Structured boundary check" | Post-hoc zero-payload division and multiplication | [Zero-payload diagnostic](../experiments/05-zero-payload/README.md) |
| Section 4.3, "Comparison-Free Ping-Pong Dialog-GCD" (`sec:ping-pong-dialog-gcd`), Proposition 1 | Conditional arithmetic argument, including canonical encodings and correct phase corrections | [Interpretation](INTERPRETATION.md) and [zero-payload diagnostic](../experiments/05-zero-payload/README.md). The tests are not a proof of the proposition's implementation assumptions. |
| Section 8, "Limitations and Outlook" (`sec:limitations`) | Finite-sample scope, approximate arithmetic, and incomplete Shor integration | [Interpretation](INTERPRETATION.md) |
| Appendix B.4, "Fresh Frozen Study" (`app:fresh-artifacts`) | Frozen artifacts and reconstruction | [Provenance](PROVENANCE.md) and [reproduction guide](REPRODUCTION.md) |

Only the three fresh-study rows of Table 7's external comparison derive from this bundle. The other rows have separate sources and nonuniform resource or error conventions.

## Separate September 7 Evidence

**The September 8 study is the primary evidence here. The following external links are historical comparisons, not alternative primary results.** Tables 1, 2, 3, and 4 are not reconstructed by this repository. Table 1 contains local replay-cell accounting. Tables 2 through 4 concern the older shared-corpus resources, cleanup effects, and full-channel outcomes. Retain those separate sources where a distinct comparison or ablation requires them. Do not mix their observations into the fresh nine-stratum study.

The September 7 shared corpus uses seed `ecdsafail-windowed-independent-random-100k-v1`. Its seven complete circuit ledgers contain 700,000 outcome rows on 100,000 common inputs. This repository does not include those seven ledgers. A source snapshot or historical README that mentions them is not a substitute for their data release.

The manuscript's September 7 artifact index identifies these public release commits in `jieyilong/ecdsafail-challenge`. Start with the pinned repository, then use the listed relative directory:

| Earlier artifact | Pinned data release | Relative directory in that release | Circuit source revision |
|---|---|---|---|
| Jump-2 replay, also called archived version 2 | [7664bc208a5c0d8e3074af8588a501b41560e851](https://github.com/jieyilong/ecdsafail-challenge/tree/7664bc208a5c0d8e3074af8588a501b41560e851) | `experiments/windowed_pingpong/` | `15a29ac9b1e97fc21eb81b9a6f0f6d9c4dc7a92e` |
| Ping-pong replay | [7664bc208a5c0d8e3074af8588a501b41560e851](https://github.com/jieyilong/ecdsafail-challenge/tree/7664bc208a5c0d8e3074af8588a501b41560e851) | `experiments/windowed_pingpong/` | `a1373a0582c9554d66633b13c76300d0ecdf81c4` |
| Ping-pong split | [c6ad76006be76711c27405365b3e61e8f0a032b3](https://github.com/jieyilong/ecdsafail-challenge/tree/c6ad76006be76711c27405365b3e61e8f0a032b3) | `experiments/exact_qrom/` | `2e0187c99fef038f079aaf76b6d36f64cce7481e` |
| Jump-2 split | [a3565aa30e4234342f28093185c29dce883599d8](https://github.com/jieyilong/ecdsafail-challenge/tree/a3565aa30e4234342f28093185c29dce883599d8) | `experiments/jump2_exact_qrom/` | `080452804328698214f36655d95c9883be6a3080` |

Useful entry points into this external historical evidence:

- [Shared-corpus summary at 7664bc2](https://github.com/jieyilong/ecdsafail-challenge/blob/7664bc208a5c0d8e3074af8588a501b41560e851/experiments/windowed_pingpong/results/SUMMARY.md): the older mixed and windowed replay comparison.
- [Archived Jump-2 replay manifest at a3565aa](https://github.com/jieyilong/ecdsafail-challenge/blob/a3565aa30e4234342f28093185c29dce883599d8/experiments/jump2_exact_qrom/references/jump2_replay/manifest.tsv): the replay reference retained alongside the Jump-2 split experiment, not the split candidate's manifest.
- [Shared-corpus records retained at c6ad760](https://github.com/jieyilong/ecdsafail-challenge/tree/c6ad76006be76711c27405365b3e61e8f0a032b3/experiments/windowed_pingpong/results): includes `corpus`, `mixed_jump2`, `mixed_pingpong`, `windowed_jump2`, and `windowed_pingpong` records. The split experiment is separately under [experiments/exact_qrom](https://github.com/jieyilong/ecdsafail-challenge/tree/c6ad76006be76711c27405365b3e61e8f0a032b3/experiments/exact_qrom).

These links do not import or pool any older data into this repository.

The `7664bc2` release also identifies the Jump-2 mixed and ping-pong mixed comparison records. The source-parent mixed ledger is identified in the manuscript's older artifact index as a separate Experiment 1 archive, not as a public release in this bundle. Its public data location must be supplied by that separate evidence package. Likewise, cite the separate local replay-cell accounting evidence for Table 1, not this repository's fresh-run verification.

The September 8 original-pingpong and Jump-2 candidates reuse the split circuit streams, but their fresh inputs, table allocation, and outcomes differ from September 7. Identical circuit source does not make two datasets interchangeable.

## Resolving Historical Paths

The paper and original bundle may refer to `fresh-corpus-spec.json`, `results/`, or `supplementary/`. In this repository these are relocated, not missing scientific records. Use [provenance/path-map.json](../provenance/path-map.json) for exact file mappings and [the provenance guide](PROVENANCE.md) for common translations.

A public reference should identify a versioned repository release or full commit **before** giving a relative directory. Do not cite an author's `outputs/...` directory as though it were a public location. See [CITING.md](CITING.md) for the `v1.0.0` reference format. This documentation does not supply or imply a paper arXiv identifier.
