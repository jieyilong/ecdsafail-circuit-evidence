# Data Dictionary

## Added Mechanism Records

The v1.1.0 additions use separate schemas. [Experiment 06](../experiments/06-resource-accounting/README.md) records allocator ownership at each phase maximum, raw static CCX+CCZ counts, source/configuration controls, and 64-case smoke outcomes. These are not the frozen study's mean executed counts or an equal-error comparison. Its complete schema is demonstrated by [integration-summary.json](../experiments/06-resource-accounting/receipts/integration-summary.json).

[Experiment 07](../experiments/07-boundary-diagnosis/README.md) records raw component/cell traces, measurement masks, and local regression results. Thirty-five pre-release coefficients are nonzero, with fixture 4 individually confirmed as p. This is not an all-35 equality-to-p count. Reset-phase changes combine by XOR and are not added to final phase-failure counts. See the [diagnostic report](../experiments/07-boundary-diagnosis/REPORT.md) before interpreting these fields. Neither new schema is pooled with the fresh-study records below.

[Repository overview](../README.md) | [Reproduction](REPRODUCTION.md)

## Names and Notation

| Reader-facing candidate ID | Key in the original freeze and analysis | Meaning |
|---|---|---|
| `original-pingpong` | `pingpong_base` | Original optimized ping-pong with split-address cleanup |
| `conservative-pingpong` | `pingpong_conservative` | Guarded ping-pong plus the wider coordinate-prefix check |
| `jump2` | `jump2` | Jump-2 with split-address cleanup |
| `zero-payload-probe` | Not a final-study candidate | Separate instrumented component diagnostic |

The public commands and directory names use the first column. Original JSON keys remain unchanged.

The accumulator is $R=(x_R,y_R)$, the selected addend is $A=(x_A,y_A)$, and the intended output is $R'=R+A$. Physical coordinate registers are $X,Y$. The field modulus is $p$ and the subgroup order is $r$. Neither is a success probability. $G$ is the standardized generator and $P_i=[k_i]G$ are the two synthetic public test points.

## Fresh Input and Outcome Files

Each [corpus file](../experiments/02-fresh-windowed/data/corpus/) is a gzip-compressed, header-bearing TSV. It stores input and reference columns once per stratum. Each candidate's `runs/<candidate>/<stratum>/checkpoint/outcomes.tsv.gz` stores every outcome. Join by **stratum and integer `index`**, never physical row position. Indices restart at zero in each stratum.

| Corpus column | Encoding and meaning |
|---|---|
| `batch` | Decimal batch number, `index // 64` |
| `index` | Decimal case index, from `0` through `n-1` |
| `address` | Decimal 16-bit QROM address $j$ |
| `target_x`, `target_y` | Hexadecimal coordinates of input accumulator $R$ |
| `addend_x`, `addend_y` | Hexadecimal coordinates of selected addend $A$ |
| `expected_x`, `expected_y` | Hexadecimal reference coordinates of $R'$ |

| Outcome column | Encoding and meaning |
|---|---|
| `index` | Join key into that stratum's corpus |
| `got_x`, `got_y` | Observed coordinate words in hexadecimal, or `=` for exact equality with the corresponding expected field |
| `got_address` | Observed address word in hexadecimal, or `=` for equality with the decimal input address after conversion to hexadecimal |
| `classical_failure` | `1` when an output coordinate or the returned address differs from its reference, otherwise `0` |
| `phase_failure` | `1` when the simulator reports a residual phase flag for this evaluated case, otherwise `0` |
| `ancilla_failure` | `1` when the evaluator reports nonzero residual ancilla state, otherwise `0` |
| `any_failure` | Boolean OR of the three preceding flags |

`=` is a lossless abbreviation, not a missing value or an omitted successful case. A row with matching coordinate words can still have a phase or ancilla failure. The failure categories overlap.

Original row order records parallel batch completion and need not be sorted. The outcome order is preserved so that expansion recovers each original raw `inputs.tsv` hash. Do not sort frozen files in place. [query_case.py](../scripts/query_case.py) resolves a case without manually joining files:

```sh
python3 scripts/query_case.py --candidate original-pingpong --stratum G-s0 --index 0
```

## Batch and Run Records

`checkpoint/batches.tsv` contains one row for each batch of at most 64 cases. Counts are decimal integers.

| Batch column | Meaning |
|---|---|
| `batch`, `shots` | Batch identity and number of evaluated cases, including a possibly shorter final batch |
| `toffoli`, `clifford` | Total executed work across the cases in that batch, not per-case means |
| `classical_failures` | Sum of case-level classical flags |
| `phase_failure_shots`, `ancilla_failure_shots`, `any_failure_shots` | Sums of the corresponding case-level flags |
| `phase_garbage_batches`, `ancilla_garbage_batches` | `0` or `1` indicating whether this batch contains at least one corresponding flag, not a shot count |
| `inputs_end_offset` | Byte offset after this batch in the original uncompressed `inputs.tsv`, including its header |

`checkpoint/manifest.tsv` is a two-column key/value file without a header. It records `format`, `interface`, `seed`, `window_bits`, `target_shots`, `qubits`, `ops`, `ops_fingerprint`, and, for the auxiliary driver, `qip_table_beta`. `ops` counts serialized operations, not executed Toffolis.

`configuration.json` binds a final run to the frozen candidate, stratum, operation hash, evaluator hash, and worker count. `COMPLETE.json` records elapsed time, original raw ledger hashes, and a per-stratum summary. It is an execution receipt, not a claim of zero failures. `eval.log` is the original console record.

Development and evaluator-equivalence runs instead retain complete `checkpoint/inputs.tsv.gz` ledgers with both the corpus and outcome columns in one file. Their observed outputs are explicit hexadecimal words. Development `summary.json` files report each configuration separately.

## Corpus Specification

In [corpus-spec.json](../experiments/02-fresh-windowed/corpus-spec.json), `freeze_sha256` binds the specification to the freeze and `generated_utc` records generation after that freeze. `master_seed_hex` and stratum `seed` values document the deterministic input streams.

Each stratum has `name`, `base`, `base_scalar`, `shift`, `beta`, `n`, and `seed`. For base $B=[k_B]G$ and shift $i$, `beta` is $k_B2^i$ modulo $r$, so the table is $\mathcal T_B^{(i)}[j]=[j2^i]B=[j\beta]G$. It is host-side reference metadata, not an extra scalar input supplied to the circuit. Names such as `P1-s128` mean base $P_1$ and shift 128.

Address zero selects the identity $\mathcal O$. The stored zero-coordinate payload is an interface convention for that table entry, not an ordinary affine curve point. Use `address == 0` to identify these cases.

## Analysis Fields

[analysis.json](../experiments/02-fresh-windowed/analysis.json) contains per-circuit summaries, their `strata`, and `paired` comparisons. Resource means and products are decimal strings to retain precision. Probability bounds are numeric fractions, not percentages.

| Field | Meaning |
|---|---|
| `n`, `cases_per_circuit` | Number of evaluated cases in the indicated scope |
| `Q` | Peak logical qubit width |
| `total_T`, `mean_T` | Sum of batch Toffoli totals and that sum divided by the case count |
| `QT` | $Q\times T$, computed before rounding |
| `total_Clifford`, `mean_Clifford` | Counted Clifford work and its mean under the evaluator convention |
| `static_toffoli` | Toffoli operations in the emitted stream, distinct from mean executed work |
| `classical_failure`, `phase_failure`, `ancilla_failure`, `any_failure` | Counts of flagged cases, not Boolean fields at summary level |
| `pass_fraction` | Empirical success probability $\hat p=1-\text{any_failure}/n$ |
| `retry_proxy` | $Q\times T/\hat p$, a per-call classical-retry sensitivity proxy, not a Shor success estimate |
| `failure_rate`, `wilson95` | Per-stratum observed any-channel rate and two-sided 95% Wilson interval |
| `exact_one_sided95_upper` | Per-stratum one-sided Clopper--Pearson upper bound |
| `stratified_one_sided95_upper` | Allocation-weighted upper bound using simultaneous stratum bounds with `alpha = 0.05/9` |
| `zero_failure_pooled95_upper` | Tighter bound `1 - 0.05**(1/n)` for a zero-failure circuit, otherwise `null` |
| `identity_rows`, `identity_failures`, `address_failures` | Identity-input count, any-channel failures among those inputs, and returned-address mismatches |
| `extra_generic_exceptions` | Per-stratum list of retained indices where nonidentity input or expected-output x coordinates equal the addend's x coordinate. Pooled summaries store its count. |
| `input_metadata_mismatches` | Count of mismatches in shared input/reference metadata across candidates |

Counted Clifford work includes CX, CZ, SWAP, HMR, and reset under the evaluator's convention, but excludes tracked X and Z operations. Static HMR/reset counts in [freeze.json](../provenance/freeze.json) are not executed measurement counts or feed-forward depth. `null` depth fields mean unmeasured, not zero.

For a paired key `a_vs_b`, `baseline_only` counts failures of **a only**, and `candidate_only` counts failures of **b only**. `both_fail` and `neither_fail` complete the four categories. For example, `jump2_vs_pingpong_base` has 215 baseline-only and 39 candidate-only failures. These labels describe argument order, not a global ranking.

## Diagnostic and Provenance Records

The [phase-trace guide](../experiments/04-coordinate-phase/README.md) explains stage masks and the misleading inherited shot denominator in that diagnostic log. The [zero-payload guide](../experiments/05-zero-payload/README.md) explains the fixture indices, denominator words, and overlapping output/phase counts. Neither log supplies final-study resource totals.

For `freeze.json`, `path-map.json`, `source-trees.json`, and archive identities, see [Provenance](PROVENANCE.md). For the statistical scope of all these fields, see [Interpretation](INTERPRETATION.md).
