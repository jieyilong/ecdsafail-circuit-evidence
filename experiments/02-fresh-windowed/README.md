# 02. Fresh Multi-Table Evaluation

[Repository overview](../../README.md) | [Full results](RESULTS.md) | [Summary CSV](summary.csv) | [Data dictionary](../../docs/DATA_DICTIONARY.md)

**Purpose:** compare three frozen circuits on shared fresh inputs after parameter selection. This supports manuscript **Section 7.4, Table 6, Table 8, and Appendix B.4**.

Each case is one window-selected point-addition call, $R\mapsto R+A$. All candidates use a 16-bit window and exact split-address QROM cleanup. This is not a complete Shor schedule.

## Results and Allocation

| Candidate | Q | Mean executed T | Cls | Pha | Anc | Any |
|---|---:|---:|---:|---:|---:|---:|
| [original-pingpong](runs/original-pingpong/) | 1,338 | 1,127,527.39827 | 38 | 18 | 0 | 39 |
| [conservative-pingpong](runs/conservative-pingpong/) | 1,392 | 1,252,854.89397 | 0 | 0 | 0 | 0 |
| [jump2](runs/jump2/) | 1,162 | 1,523,121.58073 | 163 | 127 | 0 | 215 |

Each row has 100,000 cases. Failure channels overlap and Any is their union. The 300,000 outcome rows represent three evaluations of the same 100,000 inputs, not 300,000 independently chosen inputs.

For $B\in\{G,P_1,P_2\}$ and shifts $i\in\{0,128,240\}$, each table is $\mathcal T_B^{(i)}[j]=[j2^i]B$. The two public test points and all seeds are fixed in [corpus-spec.json](corpus-spec.json).

| Stratum | Cases | Original Any | Conservative Any | Jump-2 Any |
|---|---:|---:|---:|---:|
| G-s0 | 11,111 | 8 | 0 | 18 |
| G-s128 | 11,111 | 2 | 0 | 20 |
| G-s240 | 11,111 | 6 | 0 | 27 |
| P1-s0 | 11,111 | 6 | 0 | 26 |
| P1-s128 | 11,111 | 5 | 0 | 19 |
| P1-s240 | 11,111 | 2 | 0 | 19 |
| P2-s0 | 11,111 | 6 | 0 | 30 |
| P2-s128 | 11,111 | 1 | 0 | 31 |
| P2-s240 | 11,112 | 3 | 0 | 25 |

All failed cases remain included in the work means and outcome files. The corpus includes three identity-table cases, which pass for all candidates. No extra generic exceptions or returned-address failures were recorded.

## Read and Verify

| File or directory | Use |
|---|---|
| [analysis.json](analysis.json) | Full-precision pooled and per-stratum resources, channel counts, confidence bounds, and paired discordances |
| [corpus-spec.json](corpus-spec.json) | Master seed, public-point scalars, table multipliers, stratum seeds, and case counts |
| [data/corpus/](data/corpus/) | One compressed input/reference table per stratum |
| [runs/](runs/) | All 27 outcome ledgers, manifests, batch counts, configurations, logs, and completion receipts |
| [oracle-check.json](oracle-check.json) | Independent classical reference reconstruction of all 100,000 cases |
| [../../provenance/freeze.json](../../provenance/freeze.json) | Source identities, settings, static resources, and operation hashes frozen before the fresh seed |

From the repository root:

```sh
python3 scripts/verify.py --output .work/verification.json
python3 scripts/query_case.py --candidate original-pingpong --stratum G-s0 --index 0
```

The verifier reconstructs complete raw ledgers and reruns the frozen analysis without executing a circuit. The [reproduction guide](../../docs/REPRODUCTION.md) separately describes oracle checks, builds, smoke tests, and full execution. Derived [strata](strata.csv), [paired comparisons](paired.csv), and the complete [failure index](failures.csv) provide convenient entry points into the original data.

## Limits

The conservative result gives a one-sided 95% upper bound of approximately 0.002996% for the allocation-weighted failure rate under the stated independent-trial model. It is not an all-input or coherent-error guarantee. The [separate zero-payload probe](../05-zero-payload/README.md) exposes component-level representation and phase conditions that this random sample does not certify. Its outcomes are not pooled here.

The September 7 shared-corpus replay/split results are a different dataset, even where circuit streams match. See [the paper map](../../docs/PAPER_MAP.md#separate-september-7-evidence).
