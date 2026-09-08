# Results at a Glance

This repository preserves the September 8, 2026 validation study. It does not replace the paper's older exploratory corpus or establish complete Shor correctness.

| Circuit | Cases | Q | Mean T | Q x T | Pass fraction | Any-channel failures |
|---|---|---|---|---|---|---|
| Original ping-pong | 100,000 | 1,338 | 1,127,527.39827 | 1,508,631,658.88526 | 0.99961 | 39 |
| Conservative ping-pong | 100,000 | 1,392 | 1,252,854.89397 | 1,743,974,012.40624 | 1 | 0 |
| Jump-2 | 100,000 | 1,162 | 1,523,121.58073 | 1,769,867,276.80826 | 0.99785 | 215 |

The conservative circuit adds 54 qubits and 11.12% mean Toffolis relative to original ping-pong. Against Jump-2, it uses 230 more qubits, 17.74% fewer mean Toffolis, and 1.46% lower raw Q x T. These are different empirical accuracy/resource points, not equal-error optima.

See [full results and uncertainty](experiments/02-fresh-windowed/RESULTS.md), [development results](experiments/01-development/RESULTS.md), and the [negative zero-payload findings](experiments/05-zero-payload/RESULTS.md).
