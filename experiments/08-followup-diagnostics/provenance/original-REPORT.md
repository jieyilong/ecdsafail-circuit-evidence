# Findings and scope

## 1. Smoke input 50: diagnosed

The original mixed circuit and the no-postcompiler ablation reproduce the same
classical failure. Five other smoke failures are unsupported identity addends.
The intended denominator walks take 616 and 638 rounds and fit the original
shrinking signed widths. Division and squaring return their intended values.

In multiplication, zero-based inverse-replay round 271 adds `2F`, where
`F = 2^32 + 977`. The 56-bit correction drops a carry into bit 56. The emitted
coefficient is exactly `2^56` below its intended value. The raw-word model
matches BOTH coefficient and numerator at all 702 ordinary inverse-round
boundaries and reproduces the final incorrect y coordinate. This is a
cell-level carry diagnosis, not a claim that every elementary gate has been
given an independent specification. The conservative four-bit-window variant
passes the same input. No frozen circuit was patched.

The exact operands and outputs are in `targeted-analysis.json`. Segmented and
unsegmented execution agree for every tested lane. The original smoke outputs
and all three failure channels are reproduced exactly.

## 2. Supported-domain zero slopes: negative result retained

Take the secp256k1 generator `A = G`, a nontrivial cube root of unity `beta`,
and `R = (beta*x_G, y_G)` or `(beta^2*x_G, y_G)`. Both points and their sums are
on the curve. Neither case has `R = +/-A` or `R = -2A`, and both affine
denominators are nonzero. Both have zero slope. Exact values and checks are
recorded in `fixture-proof.json` and `test_diagnostics.py`.

Each input is repeated in 32 simulator lanes with the retained measurement
seed, giving 64 outcomes per circuit. These are NOT 64 independently sampled
point pairs.

| Circuit | Classical failures | Phase flags | Dirty ancilla lanes |
|---|---:|---:|---:|
| Original mixed, no-postcompiler ablation | 0 | 33 | 0 |
| Original mixed, default settings | 0 | 33 | 0 |
| Original windowed, w=4 | 0 | 27 | 0 |
| Conservative windowed, w=4 | 0 | 35 | 0 |

All addend/address interfaces are restored. These are complete single-call
tests at the stated window width, not a rerun of the full w=16 validation.
They refute the claim that exceptional-addition exclusions remove all
zero-slope phase issues. They do not estimate the frequency under random
point sampling. No circuit repair is claimed.

## 3. Exact denominator tail: 10,000,000 trials

SHAKE256 samples nonzero canonical denominators with explicit rejection.
The source's specialized first transition is followed by the exact signed
recurrence. Termination is the first round with both magnitudes equal to one.

| Budget | Exceedances | Observed fraction |
|---|---:|---:|
| 704 | 1,535 | 0.0001535 |
| 736 | 6 | 0.0000006 |
| 768 | 0 | 0 |
| 800 | 0 | 0 |

Mean: **621.533239 rounds**. Maximum: **743**. No outcomes were censored at the
800-round cutoff. Original/conservative signed width misses were **661/0**
within their respective 704/736 budgets. Native runtime was approximately
197 seconds. The generator and data SHA-256 are in `tail-10000000.json`.

A separate Python implementation agrees with the GMP program on 1,033 random
and boundary denominators, including width flags. This is independent code,
not independent authorship or formal verification. The 10,000-case pilot is a
prefix, not additional independent evidence.

Under independent uniform sampling, zero events out of 10 million gives a
pointwise one-sided 95% upper bound near `2.996e-7`, NOT `1e-7`. Six observed
736-round exceedances are not a guarantee of a maximum failure rate of `6e-7`.
The test is denominator-level and does not evaluate modular payloads, phase,
joint point-addition failure, or a full Shor schedule.

## 4. Guard diagnostics on actual frozen point inputs

The full run uses all nine existing corpus strata: **99,997 nonidentity
inputs**, with three identity-addend rows explicitly skipped. Both arithmetic
calls are modeled, retaining raw 256-bit representations and correlated
replay operands. No disagreement was observed for:

- 40-bit chunk-carry predicates, with equality defects distinguished from prefix misses.
- 72-bit ordinary correction ranges.
- 48-bit postcorrection overflow predicates, including full-width predicate defects.
- The signed value schedule and modeled endpoint value corrections.

The whole-cell value model is checked against 246 final emitted lane outcomes
and the 702 inverse-round boundaries above. Positive-control tests expose the
missing equality term and distinguish it from a prefix-only miss. The model
therefore does not simply assume the questioned predicate is correct.

This is a **post-hoc diagnostic**, not another fresh circuit evaluation. It
does not model every specialized seed/endpoint phase reset, coordinate guard,
or measurement branch. No all-input or full coherent error rate follows from
zero modeled triggers. These observations are compatible with the fresh
0/100,000 result and the distinct structured phase counterexamples. The
1,000-per-stratum pilot is a subset, not extra independent evidence.

## 5. Manuscript changes and limits

The abstract and introduction now lead with the measured construction and
correct 25.08% controlled static saving. The mechanism decomposition separates
the 410,567 raw cross-artifact gap from the 340,442 matched ablation. External
comparisons distinguish measured-versus-constructed counts from measured
counts below a published cap. v1.1.0 is the current public entry point, while
v1.0.0 remains the original freeze provenance.

The paper retains its contributor material and the extended abstract remains
untouched. The new findings diagnose a failure and quantify limited tails.
They do not establish an exact circuit, a global error budget, or an oral
acceptance guarantee. Public release of this new supplement remains pending.
