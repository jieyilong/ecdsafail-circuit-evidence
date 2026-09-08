# Development Study: Results

These are cumulative development configurations, not held-out accuracy estimates. All five results are retained.

| Configuration | N | Q | Mean T | Classical | Phase | Ancilla | Any |
|---|---|---|---|---|---|---|---|
| 01-original | 16,384 | 1321 | 952,714.306274 | 8 | 5 | 0 | 10 |
| 02-more-rounds | 16,384 | 1353 | 975,938.432129 | 3 | 2 | 0 | 4 |
| 03-wider-values | 16,384 | 1359 | 1,019,114.728394 | 0 | 1 | 0 | 1 |
| 04-wider-replay-guards | 16,384 | 1375 | 1,077,978.770630 | 0 | 1 | 0 | 1 |
| 05-wider-coordinate-check | 16,384 | 1375 | 1,078,050.799011 | 0 | 0 | 0 | 0 |

The last profile was selected before fresh input generation. The shared phase-only case is documented in [experiment 04](../04-coordinate-phase/README.md). Settings are explained in the [original frozen protocol](../../sources/frozen-tools/bounded_qip/PROTOCOL.md).
