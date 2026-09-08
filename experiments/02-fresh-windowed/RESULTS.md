# Fresh Windowed Study: Results

Generated from the preserved [analysis JSON](analysis.json). Each circuit received the same 100,000 cases across nine table strata. Costs include failed inputs.

| Circuit | Cases | Q | Mean T | Q x T | Pass fraction | Any-channel failures |
|---|---|---|---|---|---|---|
| Original ping-pong | 100,000 | 1,338 | 1,127,527.39827 | 1,508,631,658.88526 | 0.99961 | 39 |
| Conservative ping-pong | 100,000 | 1,392 | 1,252,854.89397 | 1,743,974,012.40624 | 1 | 0 |
| Jump-2 | 100,000 | 1,162 | 1,523,121.58073 | 1,769,867,276.80826 | 0.99785 | 215 |

## Failure Channels

| Circuit | Classical | Phase | Ancilla | Any |
|---|---|---|---|---|
| Original ping-pong | 38 | 18 | 0 | 39 |
| Conservative ping-pong | 0 | 0 | 0 | 0 |
| Jump-2 | 163 | 127 | 0 | 215 |

Channels overlap. All three retained identity-addend cases pass in every circuit. There are no additional generic-domain exceptions.

## Uncertainty and Scope

| Circuit | Stratified upper 95% bound | Zero-event upper 95% bound |
|---|---|---|
| Original ping-pong | 0.00115274145962 | not applicable |
| Conservative ping-pong | 0.000467256918049 | 2.99568740194e-05 |
| Jump-2 | 0.00353452956203 | not applicable |

Bounds above are probabilities, not percentages. They concern each circuit's allocation-weighted error rate under the stated sampling model. They are not simultaneous across the three circuits, all-input guarantees, or coherent-error bounds. `retry_proxy` in the CSV is only a per-call sensitivity calculation.

The [zero-payload probe](../05-zero-payload/RESULTS.md) finds representation and phase limitations on structured subroutine inputs. Its cases are separate from this frozen random study.

## By Table Stratum

| Stratum | Cases | Original ping-pong failures | Conservative failures | Jump-2 failures |
|---|---|---|---|---|
| G-s0 | 11111 | 8 | 0 | 18 |
| G-s128 | 11111 | 2 | 0 | 20 |
| G-s240 | 11111 | 6 | 0 | 27 |
| P1-s0 | 11111 | 6 | 0 | 26 |
| P1-s128 | 11111 | 5 | 0 | 19 |
| P1-s240 | 11111 | 2 | 0 | 19 |
| P2-s0 | 11111 | 6 | 0 | 30 |
| P2-s128 | 11111 | 1 | 0 | 31 |
| P2-s240 | 11112 | 3 | 0 | 25 |

Full precision: [summary.csv](summary.csv), [strata.csv](strata.csv), [paired.csv](paired.csv). The [failure index](failures.csv) identifies every failing case without omitting the successful rows from the underlying data.
