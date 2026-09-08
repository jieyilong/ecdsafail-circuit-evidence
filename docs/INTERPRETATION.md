# What the Evidence Establishes

[Repository overview](../README.md) | [Paper map](PAPER_MAP.md)

## Keep the Experiments Separate

| Evidence | Supported conclusion | Not established |
|---|---|---|
| Five development runs | The recorded cumulative parameter changes improved outcomes on the 16,384-case development corpus | Held-out reliability of a selected configuration |
| Frozen fresh study | Measured single-call resources and failure flags on the same 100,000 inputs across nine specified tables | Correctness for every input, public point, or window |
| Evaluator equivalence | Official and auxiliary drivers agreed on all 8,192 recorded mixed-addition cases and integer work totals | Universal evaluator equivalence or independent verification of their shared simulator |
| Independent classical oracle | A separate implementation reproduced the recorded inputs and expected point sums | Circuit phases, coherent correctness, or physical execution |
| Coordinate-phase trace | One development failure was localized to the initial x-coordinate subtraction | An explanation of every historical phase failure |
| Zero-payload probe | Selected component inputs exposed noncanonical outputs and phase flags | A full point-addition failure rate or a replacement for the fresh-study statistics |

## Zero Failures and Boundary Failures

Conservative ping-pong has **0 any-channel failures in 100,000 fresh cases**. Under the stated independent-trial model, its one-sided 95% upper bound on the allocation-weighted failure rate is `1 - 0.05**(1/100000)`, approximately **0.002996%**. This is a bound for the specified nine-table allocation, not a claim that the circuit is exact.

The separate post-hoc zero-payload probe tested 64 selected denominators in each subroutine direction. Division returned the word $p$ instead of canonical zero 28 times and raised 19 phase flags. Multiplication returned $p$ 46 times and raised 26 phase flags. Denominators were restored and no dirty ancillas remained. These output and phase categories overlap.

There is no contradiction between these observations. The fresh study evaluates complete point-addition calls under a specified random-input distribution. The probe deliberately supplies zero component payloads to inspect a boundary condition. Its counts must not be added to the fresh study's denominator or failures.

Although $p$ and zero represent the same field element modulo $p$, they are different register bit strings. Field congruence alone does not justify bitwise duplicate removal or canonical zero cleanup. Correct phase corrections are a separate requirement. The conditional argument in manuscript Section 4.3 assumes correct value operations, modular replay, phase corrections, and canonical coefficient encodings at cleanup. The probe shows why convergence of the Euclidean value walk alone does not establish those assumptions for the implemented subroutines.

Both the original 704-round schedule and the conservative 736-round schedule retain truncated arithmetic and comparisons. "Conservative" describes the tested parameter choices, not a proved all-input bound. "Exact split-address cleanup" describes QROM payload cleanup, not exact arithmetic throughout the circuit.

## Sampling and Confidence Bounds

The source, parameters, operation streams, evaluator, and analysis were frozen before the fresh master seed was generated. No final failed inputs were discarded and no parameters changed after final outcomes were inspected. Development data and the post-hoc probe are reported separately.

The sampler uses pseudorandom 256-bit accumulator scalars and uniform 16-bit table addresses. This is not exact rejection sampling in the subgroup scalar field. It rejects identity accumulators and nonidentity equal-x inputs, while retaining identity table entries. Rejection counts are in the oracle receipt, but rejected-case identities were not stored. Additional generic-domain exceptions are recorded without deleting unfavorable outcomes. The fresh corpus has three identity-table cases and no recorded extra generic exceptions.

Each stratum has its own failure probability. The pooled quantity is the allocation-weighted mean over these nine tables, with eight groups of 11,111 cases and one of 11,112. General pooled upper bounds use simultaneous one-sided Clopper--Pearson stratum bounds with a Bonferroni adjustment. For a zero-failure result, the tighter pooled bound above remains valid under independent trials even when stratum probabilities differ. Bounds are per circuit, not simultaneous across all three circuits.

Pseudorandom inputs and measurement outcomes are modeled as independent trials for these calculations. Per-stratum intervals and paired discordances describe the recorded experiment. They are not coherent-error bounds, and an isolated stratum result should not be treated as a prespecified discovery after many comparisons.

## Interfaces and Resource Claims

Development and evaluator-equivalence runs use mixed addition with a classically supplied addend. The fresh study uses a single-call coherent window-indexed interface implementing $R\mapsto R+A$, with $A$ selected from the supplied table. Those interface distinctions matter even when arithmetic source is shared.

$Q$ is peak logical width and $T$ is mean executed Toffoli count on the stated corpus. Static Toffoli count is different. The score $Q\times T$ is a benchmark work proxy, not a physical spacetime estimate. Depth, routing, error correction, hardware timing, and a complete attack schedule are not measured here.

The reported $Q\times T/\hat p$ uses empirical per-call success $\hat p$ in an independently rerunnable classical-success model. A coherent Shor computation cannot in general detect and retry each internal point addition that way. Do not multiply these pass fractions across a 28-call schedule or describe this study as an implemented full-Shor attack.

The architecture follows the record-and-replay Euclidean approach introduced by Khattar et al. and adapted to ECDLP point addition by Schrottenloher, as attributed in the manuscript. The present evidence package documents particular circuit implementations and experiments, not independent invention of that architecture.
