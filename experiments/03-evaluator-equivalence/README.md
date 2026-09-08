# 03. Evaluator Equivalence Check

[Repository overview](../../README.md) | [Generated results](RESULTS.md) | [Summary CSV](summary.csv) | [Fresh study](../02-fresh-windowed/README.md)

**Purpose:** check that the auxiliary table-aware driver agrees with the official evaluator before using it for the fresh study. This supports **Section 7.4 and Appendix B.4**.

The two evaluators ran the same **8,192 mixed-addition cases** with table $\mathcal T[j]=[j]G$, corresponding to table multiplier `beta=1`. They agreed on all recorded inputs, outputs, failure flags, and integer gate totals. There are two complete ledgers, not 16,384 independent input cases.

## Records

- [runs/official/](runs/official/): official evaluator log, manifest, complete `inputs.tsv.gz`, and batch totals.
- [runs/auxiliary/](runs/auxiliary/): corresponding auxiliary evaluator records.
- [Trusted-core hashes](../../provenance/freeze.json): original evaluator, simulator, counters/parser, reference curve, and lockfile identities.
- [Auxiliary source](../../sources/trees/conservative-pingpong/src/bin/eval_bounded.rs) and [official source](../../sources/trees/conservative-pingpong/src/bin/eval_circuit.rs): browsable source snapshots.

The auxiliary driver changes host-side table construction, table-aware checkpoint metadata, and output bookkeeping. The simulator, error checks, counters, and curve reference remain shared and unchanged as documented in the [frozen protocol](../../sources/frozen-tools/bounded_qip/PROTOCOL.md).

From the repository root, `python3 scripts/verify.py` expands both ledgers, validates their case and batch records, and checks equality by index and summary. Physical completion order can differ between the two files.

This is an empirical evaluator regression check on the recorded cases. It does not prove universal equivalence and is not independent validation of the shared simulator. The [classical oracle check](../02-fresh-windowed/oracle-check.json) provides a separate check of input and reference-point generation, not quantum phase behavior.
