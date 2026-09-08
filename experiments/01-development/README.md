# 01. Parameter Development

[Repository overview](../../README.md) | [Generated results](RESULTS.md) | [Summary CSV](summary.csv) | [Paper map](../../docs/PAPER_MAP.md)

**Purpose:** choose one conservative ping-pong configuration before generating the fresh evaluation corpus. This is the evidence for manuscript **Table 5 and Section 7.4**.

All five runs use the same 16,384 mixed-addition cases from a dedicated development seed. The addend is classically supplied. Rows are cumulative parameter changes, and all outcomes are retained, including unsuccessful configurations. These are selection data, not held-out reliability estimates.

## Recorded Results

| Run | Rounds | Q | Mean T, rounded | Cls | Pha | Anc | Any |
|---|---:|---:|---:|---:|---:|---:|---:|
| [01-original](runs/01-original/) | 704 | 1,321 | 952,714.306 | 8 | 5 | 0 | 10 |
| [02-more-rounds](runs/02-more-rounds/) | 736 | 1,353 | 975,938.432 | 3 | 2 | 0 | 4 |
| [03-wider-values](runs/03-wider-values/) | 736 | 1,359 | 1,019,114.728 | 0 | 1 | 0 | 1 |
| [04-wider-replay-guards](runs/04-wider-replay-guards/) | 736 | 1,375 | 1,077,978.771 | 0 | 1 | 0 | 1 |
| [05-wider-coordinate-check](runs/05-wider-coordinate-check/) | 736 | 1,375 | 1,078,050.799 | 0 | 0 | 0 | 0 |

Cls, Pha, and Anc count classical-output, phase, and ancilla flags. Any is their union. Mean T includes all cases. Each run's `summary.json` retains full precision.

The wider-value step adds 16 bits before the existing 259-bit cap. The guarded step widens chunk comparisons, replay folds, endpoint folds, and carry-erasure comparisons, without changing the width slopes or unrelated arithmetic. The [original protocol](../../sources/frozen-tools/bounded_qip/PROTOCOL.md) gives exact settings and their meanings.

The first four runs share the phase-only failure at development index **6828**. A [stage trace](../04-coordinate-phase/README.md) localizes it to the initial x subtraction. The fifth run widens the coordinate prefix from 19 to 40 bits, clearing that observed failure for about 72 additional mean Toffolis and no additional peak qubits. A 40-bit prefix check is still approximate.

The fifth configuration was selected for the [fresh windowed study](../02-fresh-windowed/README.md). Its mixed-addition width of 1,375 is not the fresh windowed width of 1,392. These are different interfaces.

## Find the Records

Every run directory contains `summary.json`, `eval.log`, and `checkpoint/` with a manifest, batch totals, and the complete `inputs.tsv.gz` ledger. Unlike the factored fresh data, these ledgers store inputs and outputs together. The [oracle receipt](oracle-check.json) records an independent reconstruction of all 16,384 development input/reference cases with no mismatches.

From the repository root, `python3 scripts/verify.py` checks all five ledgers without executing circuits. See the [data dictionary](../../docs/DATA_DICTIONARY.md) for fields and the [reproduction guide](../../docs/REPRODUCTION.md) for the distinct verification and execution levels.
