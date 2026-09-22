# 768-Round Schedule Audit

Date: 2026-09-22. Scope: exact denominator recurrence and source width schedule.
All new files and compiler outputs are confined to this directory. No source
circuit was patched, emitted, or simulated. No ten-million-input job was run.

## Decision

**768 rounds is not sufficient for all nonzero canonical field denominators.**
The exact, untruncated source recurrence first reaches a signed-unit pair at
round **1,135 for d = 3**, and at round **1,239 for d = 2^255**. These counts
include the specialized first transition. They agree across a new signed Python
model, an unsigned average/difference model, the frozen Python model, and the
frozen GMP recurrence with only its loop/histogram bounds extended to 4,096.
The complete integer traces are retained as `trace-d3.csv` and
`trace-d2pow255.csv`. These are valid field inputs, not claimed sampled curve
pairs or estimates of their frequency in a Shor computation.

**Termination within 768 also does not imply safety of its proposed taper.**
For d = 1, exact termination occurs at round 512, but the margin-20 taper first
overflows the pre-halving sum at zero-based k = 177, width 225. The first
margin-4 miss is k = 128. See `trace-d1.csv` and `structured_witnesses.json`.
This is a violated exact-width precondition, not a simulated final output or
phase failure. Full width removes this particular approximation, not the round
limit or the other circuit defects.

## Source and Exact Schedule

The inspected source is
`ecdsafail-qip-bounded-validation/src/point_add/pingpong_div.rs`:
`bounded_profile()` at line 20, `value_width()` at line 193, and `value_walk()`
at line 500. The SHA-256 and before/after immutability check are in
`run_receipt.json`. Relevant frozen inputs are checked against the published
experiment-08 manifest in `frozen_audit.json`.

| Existing profile | Rounds | Margin | Chunk comparison | Replay fold | Endpoint fold | Flag comparison |
|---|---:|---:|---:|---:|---:|---:|
| base | 704 | 4 | 26 | 56 | 55 | 28 |
| rounds | 736 | 4 | 26 | 56 | 55 | 28 |
| widths | 736 | 20 | 26 | 56 | 55 | 28 |
| guarded | 736 | 20 | 40 | 72 | 71 | 48 |

These are raw source parameter values, not interchangeable effective bit widths
for every helper. In particular, `replay_fold_target()` depends on
`SUB4_PINGPONG_LOW56_FOLD`, and endpoint helpers have their own window semantics.
The audit does not infer a complete circuit configuration from this table.

**There is no 768-round `bounded_profile()` option in this source.** The proposed
extension evaluated here means guarded settings with rounds changed to 768,
retaining margin 20. It is an integer-model candidate only. The source's
margin-20 simulator selfcheck expects terminal width 11 and would need updating
for a 768-round extension, whose terminal width is 8.

For zero-based k, margin m, and clamp to [8,259], the exact schedule is

```text
                      256 + m - floor(17 k / 100),                 k < 40
w_m(k) = clamp[8,259]( 250 + m - floor(33 (k-40) / 100),      40 <= k < 304
                      163 + m - floor(40 (k-304) / 100) ),         k >= 304.
```

Each floor is applied separately, as in Rust's nonnegative integer divisions.
`width_schedule.csv` gives every k = 0,...,767, with inactive cells blank for
shorter profiles. The actual Rust declarations were extracted verbatim and
compiled in isolation. All 3,200 widths across the four profiles and k < 800
agree with the Python formula. No Cargo build was needed.

| k | w_4(k) | w_20(k) |
|---:|---:|---:|
| 0 | 259 | 259 |
| 39 | 254 | 259 |
| 40 | 254 | 259 |
| 303 | 168 | 184 |
| 304 | 167 | 183 |
| 703 | 8 | 24 |
| 735 | 8 | 11 |
| 736 | 8 | 11 |
| 742 | 8 | 8 |
| 767 | 8 | 8 |

## Exact Integer Contract

Let p = 2^256 - 2^32 - 977 and 1 <= d < p. Initialize u = p, v = d.
At k = 0 the source performs

```text
a0 = d mod 2; a1 = floor(d/2) mod 2
v = floor(d/2) - p + a1*p + a0*(p+1)/2.
```

For k >= 1 the target is u at odd k and v at even k, with the other value
as source s. Let e = bit1(s) XOR bit1(t), using signed two's-complement low
bits. Set z = t + (-1)^e s and t' = z/2. This is exact integer division:
z = 2 mod 4, so t' is odd and nonzero. The gcd is preserved. Retaining e
permits inversion by t = 2t' - (-1)^e s. The specialized initial tape bit is
a0, not the sign from an ordinary step.

The new initialization is independently implemented as the ordinary update
on the odd lift d* = d for odd d, or d-p for even d. It is checked against
the fused expression above. First termination is the number of completed
transitions when |u| = |v| = 1. Signed-unit pairs are fixed points, so stopping
the scalar diagnostic there is equivalent for later width checks to padding
with any of the schedules above, whose widths are at least 8.

At each active round the model checks both incoming operands, and at ordinary
rounds also the pre-halving sum, against [-2^(w-1), 2^(w-1)-1]. A miss does
not change the exact walk. This detects where the emitted wrapping arithmetic
or high-wire release loses its integer justification. It does not emulate the
resulting finite-word circuit. The specialized first cell is modeled by its
exact expression, not by its individual gates or internal carry workspace.

## Frozen and Fresh Evidence

The frozen `tail-10000000.json` is reused, **not reproduced in full**. This audit
verified its file hash, sample total, weighted round sum, mean, maximum, and
all four tail counts. It did not regenerate the 320 MB denominator stream or
recompute that stream's recorded hash. A hash anchored to a local manifest is
an integrity check, not independent authentication of the original execution.

| Evidence | n | >704 | >736 | >768 | >800 | Maximum |
|---|---:|---:|---:|---:|---:|---:|
| Frozen study, reused | 10,000,000 | 1,535 | 6 | 0 | 0 | 743 |
| Frozen pilot, reproduced | 10,000 | 0 | 0 | 0 | 0 | 704 |
| New independent-seed sample | 10,000 | 2 | 0 | 0 | 0 | 713 |

Frozen mean: 621.533239. New sample mean: 621.6725. Neither random sample is
censored at 800. The pilot is a prefix of the frozen ten-million study and
adds no independent evidence. The structured regressions are not random and
are not pooled into any of these rate estimates.

The frozen study reports 661 margin-4 width misses through round 704 and zero
margin-20 misses through round 736. **It did not check margin-20 widths through
768.** Six trajectories still had not terminated at 736, and their individual
late states were not retained in the histogram. The histogram therefore cannot
recover a 768-width miss count. `frozen_audit.json` records that value as null.

The new sample uses seed `qip-oral-schedule-independent-20260922-v1`, distinct
from the historical seed. Both use SHAKE256(seed || uint64_le(block)), 1,000
big-endian 256-bit words per block, rejecting zero and values >= p. The new
sample size and settings were fixed before drawing it. Its 320 KB data file
and SHA-256 are retained. All 10,000 Python results match the original GMP
histogram and both original width counts. There is one base704 width miss and
zero guarded736 or proposed-taper768 misses. The unsigned model and frozen
Python model additionally cross-check the first 128 new inputs. This is
independent code and a separate pseudorandom sample, not independent authorship.

The 36 structured inputs are 1,...,32, p-1, p-2, floor(p/2), and 2^255. GMP's
original 800-step censoring agrees with Python, and the 4,096-step extension
agrees on every exact terminal count. It changes only the loop limit, histogram
capacity, and censor sentinel. Exhaustive signed coprime pairs with magnitudes
at most 63 cover 3,300 pairs, with maximum 17 ordinary rounds. These small
tests are regression evidence, not the proof for 256-bit inputs.

Under independent uniform sampling and for a fixed event, zero events in n
trials gives the exact one-sided 95% bound 1 - 0.05^(1/n). Thus the frozen
zero >768 count supports a pointwise bound approximately 2.995731825e-7,
**not 1e-7**. The new zero count alone gives approximately 2.995283598e-4.
SHAKE with a fixed seed is deterministic. The statistical interpretation
assumes its draws behave as independent uniform samples. Because 768 is a
post-hoc candidate, the frozen pointwise calculation is not an automatically
selection-valid guarantee for the chosen schedule. The six >736 observations
are an observed frequency, not a certified upper bound of 6e-7.

## Proven Full-Width Bound

**Proposition (range, not 768-round termination).** For every canonical d in
1,...,p-1, every stored value of the exact recurrence has magnitude at most p,
and every ordinary pre-halving sum has magnitude at most 2p. Signed 257 bits
hold the states. Signed 258 bits hold states and ordinary sums. Therefore
keeping the source's full 259-bit value registers throughout eliminates
signed-value truncation for any number of rounds, provided the exact update
and its inverse are implemented correctly.

**Proof.** Initially u = p and v = d. In the four d mod 4 cases, the specialized
v is respectively d/2-p, (d-p)/2, d/2, and (d+p)/2. Each has magnitude < p
and is odd. Thereafter |t'| <= (|t|+|s|)/2 <= p by induction, and
|z| <= |t|+|s| <= 2p < 2^257. Since p < 2^256, the stated signed ranges
follow. The reverse walk retraces the same states if it uses the recorded
bits and correct inverse operations. This proves a width bound without any
assumption of convergence by 768. The number 258 is a scalar arithmetic
sufficiency result, not a tested drop-in source configuration: round zero
currently asserts `VALUE_WIDTH = 259`.

This proposition does **not** justify the empirical taper, prove quantum
uncomputation, or validate the finite-window modular payload corrections,
comparators, special seed/endpoint cells, or coordinate phase corrections.

### A Simple Termination Bound

For completeness, the existing manuscript's elementary argument can be used
with full width. On magnitudes a,b, an ordinary step replaces the target by
(a+b)/2 when a = b mod 4, otherwise by |a-b|/2. The maximum never grows.
If a = b, coprimality implies both are 1. Otherwise Delta = |a-b| is a positive
even integer. Consecutive average steps halve Delta. With max(a,b) < 2^n,
at most n-1 average steps precede a difference step. That difference step and
the following alternating-target step reduce the maximum to at most 3/4 of
its previous value. To see this, write the old maximum/minimum as M,m. Updating
the larger value leaves both values <= M/2 after the next step. Updating the
smaller leaves both <= 3M/4.

A block of at most n+1 rounds therefore contracts the maximum by 3/4 unless
termination happens sooner. Three blocks contract by more than a factor two.
After 3n blocks a nonterminal positive maximum would be < 1, a contradiction.
Thus 3n(n+1) ordinary rounds suffice. At n = 256 this is 197,376 ordinary
rounds, or conservatively 197,377 total including a separately counted fused
first transition. This is a deliberately loose all-input existence bound,
not an executable job requested or run here. Combined with full width it gives
an exact integer specification, not a practical or verified quantum circuit.

### Primary-Source Check

Brent, Kung, and Luk's [Algorithm PM, Section 3.1](https://www.eecs.harvard.edu/~htk/publication/1983-information-processing-brent-kung-luk.pdf)
uses a size-difference control and swaps, and chooses the sign so that the
halved result is even before further stripping. The present recurrence instead
keeps both values odd and alternates the target. Its iteration bound cannot
be imported into this schedule merely because both use low-bit sign choices.

The [libsecp256k1 safegcd implementation notes](https://github.com/bitcoin-core/secp256k1/blob/master/doc/safegcd_implementation.md)
describe 741 divsteps from Bernstein and Yang's theorem for the original
256-bit setting, and 590 for a modified initial delta. Those are distinct
delta-controlled recurrences. They do not bound this fixed-alternation walk.
Replacing the walk would require a new reversible specification and resource
accounting. No sharper theorem for this exact recurrence is established here.
In particular, the explicit d = 3 witness precludes a 3n = 768 bound.

## Resource Assumptions

No Q or T was measured for a new 768-round circuit. Published 704/736-round
costs must not be attached to it. The model omits payload arithmetic, lookup,
phase, measurement branches, and full point-addition execution.

Under the current source's uncompressed one-bit-per-round tape, a 768-round
walk has 768 live tape qubits at replay, 32 more than guarded736. Its endpoint
taper holds two 8-bit values rather than two 11-bit values. At the point where
both 256-bit coefficient/payload registers are present, the following are
simultaneously live, before other scratch and interface state:

| Hypothetical/current allocation pattern | Values + tape + two payloads |
|---|---:|
| guarded736 taper | 2*11 + 736 + 512 = 1,270 |
| proposed768 taper | 2*8 + 768 + 512 = 1,296 |
| proposed768 constant width259 | 2*259 + 768 + 512 = 1,798 |

These are source-architecture live-subset lower bounds, **not total Q**. The
denominator is already included in the value registers and is not counted
again. Full width prevents lending discarded high-value wires to tape and
scratch, so the old low-qubit result does not survive unchanged. A different
tape/recomputation architecture could change these assumptions.

As a width-only work proxy, sum_k w(k) is 112,099 for guarded736, 112,365 for
the proposed768 taper, and 198,912 for 768 full-width259 rounds. These are
bit-round sums, **not Toffoli counts**. The specialized first transition and
seed mean 766 ordinary payload cells per direction for a 768-round version,
versus 734 for 736. Two arithmetic calls also each perform a forward and
reverse value walk. Neither the tape increase nor a rounds ratio suffices to
predict total T, peak Q, depth, or physical fault-tolerant cost.

## What May Be Said

> The frozen ten-million-denominator experiment observed no exact-recurrence
> termination count above 768, and a separate ten-thousand-denominator check
> found no 768-budget or proposed-width violations. Nevertheless, 768 is not
> an all-input termination bound: denominator 3 requires 1,135 exact rounds.
> Constant full-width value arithmetic has a simple range proof, whereas the
> shrinking schedule is empirical and has explicit width counterexamples.

No joint two-denominator point-addition error rate, coherent phase-error bound,
worst-case channel bound, or full-Shor success probability follows. Even a
union bound needs bounds under the actual marginal input distributions of
each call. Correlated calls do not require independence for a valid union
bound, but a uniform-field empirical tail is not automatically such a bound.
The frozen experiment's supported zero-slope phase counterexamples are
separate defects which more rounds alone do not repair.

## Reproduction

From the workspace root, using Python 3, Rust, Clang, and Homebrew GMP:

```sh
python3 -B research/qip-oral-20260922/schedule/audit.py
python3 -B research/qip-oral-20260922/schedule/test_audit.py
```

`audit.py` has a fixed 10,000 fresh sample cap, an 800-round random-study cap,
and a 4,096-round structured-only cap. It rebuilds two tiny native probes and
one extracted Rust function harness locally. Compiler temporary/cache paths
are redirected here. The observed execution receipt is in `run_receipt.json`.
The 12-test result is in `test-results.txt`. Original input hashes are checked
before and after the run. Generated files can be inspected without rerunning
any experiment.
