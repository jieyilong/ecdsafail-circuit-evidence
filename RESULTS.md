# Results at a Glance

This repository preserves the September 8, 2026 validation study. It does not replace the paper's older exploratory corpus or establish complete Shor correctness.

| Circuit | Cases | Q | Mean T | Q x T | Pass fraction | Any-channel failures |
|---|---|---|---|---|---|---|
| Original ping-pong | 100,000 | 1,338 | 1,127,527.39827 | 1,508,631,658.88526 | 0.99961 | 39 |
| Conservative ping-pong | 100,000 | 1,392 | 1,252,854.89397 | 1,743,974,012.40624 | 1 | 0 |
| Jump-2 | 100,000 | 1,162 | 1,523,121.58073 | 1,769,867,276.80826 | 0.99785 | 215 |

The conservative circuit adds 54 qubits and 11.12% mean Toffolis relative to original ping-pong. Against Jump-2, it uses 230 more qubits, 17.74% fewer mean Toffolis, and 1.46% lower raw Q x T. These are different empirical accuracy/resource points, not equal-error optima.

See [full results and uncertainty](experiments/02-fresh-windowed/RESULTS.md), [development results](experiments/01-development/RESULTS.md), and the [negative zero-payload findings](experiments/05-zero-payload/RESULTS.md).

## Additive v1.1.0 Mechanism Studies

The following controlled mixed-circuit experiment is separate from the frozen study above. Squaring and post-emission compiler settings are held fixed within each backend contrast.

| Backend | Square | Q | Static Toffolis | Smoke failures |
|---|---|---|---|---|
| Legacy Jump-2 | Karatsuba | 1,150 | 1,357,682 | 5 / 64 |
| Legacy Jump-2 | Product register | 1,287 | 1,349,527 | 5 / 64 |
| Ping-pong | Karatsuba | 1,321 | 1,017,240 | 6 / 64 |
| Ping-pong | Product register | 1,321 | 1,009,077 | 6 / 64 |

At fixed Karatsuba square, the static saving is 340,442 Toffolis. Five smoke inputs have unsupported identity addends and fail in every row. Ping-pong additionally fails one nonidentity case. All failures are retained; these are not equal-error comparisons. [Accounting records and reproduction](experiments/06-resource-accounting/README.md) explain simultaneous peaks and the separate static versus mean counts.

[Structured boundary diagnosis](experiments/07-boundary-diagnosis/REPORT.md) identifies carry-predicate and representation defects that are not fixed by wider comparisons alone. The 35-case pre-release finding measures nonzero coefficients, not equality to p in all 35. A locally tested canonical-negation candidate is not integrated into a full circuit. The original 100,000-case outcomes remain unchanged.

The [external accounting audit](supporting/comparison/report.md) separates published arithmetic costs, window allowances, and measured kernels. No external equal-error or physical-runtime superiority is claimed.
