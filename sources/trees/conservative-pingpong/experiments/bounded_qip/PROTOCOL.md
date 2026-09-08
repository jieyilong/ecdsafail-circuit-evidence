# Bounded QIP Validation Protocol

## Purpose

Measure the resource/error trade-off of conservative ping-pong settings and test the two optimized arithmetic families on fresh runtime tables. These are research experiments, not challenge submissions or full-Shor executions.

## Development Profiles

| Profile | Rounds | Value margin | Chunk comparison | Replay fold | Endpoint fold parameter | Carry-flag comparison |
|---|---:|---:|---:|---:|---:|---:|
| base | 704 | 4 | 26 | 56 | 55 | 28 |
| rounds | 736 | 4 | 26 | 56 | 55 | 28 |
| widths | 736 | 20 | 26 | 56 | 55 | 28 |
| guarded | 736 | 20 | 40 | 72 | 71 | 48 |

The value-width slope and all unrelated arithmetic/lookup choices remain fixed. The endpoint-fold argument counts positions after the constant's highest bit, not an absolute register width. No profile is labeled exact or certified. The larger round budget is a development choice, not a proved tail bound.

Development starts with mixed-addition tests on 16,384 inputs from a dedicated development seed. The old shared corpus and its known failures may be used as additional regression evidence and remain exploratory. All development outcomes are retained. Select at most one more conservative profile for the final windowed comparison. If none improves reliability, report that outcome without starting an unbounded search.

## Auxiliary Evaluator

### Bounded Diagnostic Amendment Before Final Freeze

The four development profiles leave the same phase failure at input 6828. A separate stage-boundary trace of unchanged operations localizes it to the initial x-coordinate subtraction, with no later phase delta on that lane. Its 19-bit high-prefix carry check misses a carry supplied by the lower bits. Test one targeted additional setting: guarded plus the existing TLM_MSBS=40 coordinate-comparison option. This is a documented fifth diagnostic candidate, not nonce selection or a new algorithm family. Retain all four original outcomes. No fresh final corpus has been generated at this amendment.

The diagnostic binary runs only a selected batch and must not be used for reported resource/error totals. Its inherited printed target-shot denominator is not the number of diagnosed inputs. Only its stage phase masks are diagnostic evidence.

The targeted guarded-plus-coordinate setting passes all 16,384 development cases and is selected before the final freeze. The windowed version is the selected conservative candidate. The coordinate option is a 40-bit prefix comparison, not an exact comparator. The four original profiles and the diagnostic amendment remain reported separately.

The official evaluator remains unchanged. The experimental eval_bounded binary is copied from it, with only runtime table construction, table-aware checkpoint metadata, and associated tests added. Simulator, error checks, gate counters, circuit parser, reference arithmetic, and dependency lockfile remain byte-identical to the parent. The table multiplier is host-side test data and is never given to the circuit in place of table coordinates.

Auxiliary bookkeeping goes to case-local research-results.tsv and research-score.json, and the banner names the research driver. These output-only changes do not modify the checks or cost formula. The final runner requires at least two requested workers to select the existing checkpointed, batch-seeded evaluation path. It does not use the sequential-RNG or diagnostic-only-batch paths.

Check beta=1 against the original table constructor and against recorded baseline input/output metadata. Independently cross-check sampled table entries and expected points using a separate implementation. Do not accept improved resource counts from evaluator changes.

## Freeze and Fresh Final Data

Freeze source revisions, profiles, binaries, operation hashes, evaluator changes, seed-generation rules, exclusions, and analysis scripts before final outcomes are viewed. Then generate one fresh master seed. Derive two public points P1=[k1]G and P2=[k2]G and independent input/measurement seeds by domain separation.

Use nine strata: bases G, P1, P2, each at shifts 0, 128, and 240. A stratum uses T[j]=[j*2^shift]B with w=16. Allocate 11,111 inputs to each of the first eight strata and 11,112 to the last, totaling 100,000 per circuit. Run the same inputs and expected outputs through baseline ping-pong, selected conservative ping-pong, and optimized Jump-2, all with exact split-address QROM cleanup.

The sampler follows the previous evaluator: pseudorandom 256-bit accumulator scalars, uniform 16-bit addresses, rejection of nonidentity equal-x inputs, and retained identity rows. Record any further generic-domain exceptions separately, without deleting unfavorable circuit outcomes. Report this distribution explicitly, including its distinction from exact rejection sampling in Z_r.

No circuit or parameter changes are permitted after inspecting final outcomes. A required bug fix invalidates that confirmatory freeze and requires a new documented seed and experiment identifier.

## Reporting

Report Q, static and mean executed Toffolis, Q*T, counted Clifford work, each failure channel and its union, identity/address checks, per-stratum and pooled confidence intervals, and paired discordances. Compute products from full-precision batch totals. Q*T/pass-fraction is only a per-call sensitivity proxy. A clean sample supplies an error-rate upper confidence bound, not an all-input or coherent-error proof.

Use pooled comparisons as primary and per-stratum results as diagnostics. Do not interpret isolated significant strata after multiple comparisons as prespecified discoveries. Preserve the full ledgers and all frozen settings. No 28-call attack cost or independent-error composition claim is made.

Each stratum has its own binomial confidence interval. For a pooled allocation-weighted error rate, report a conservative upper bound formed from stratum-specific one-sided Clopper-Pearson bounds with Bonferroni alpha=0.05/9. If the total failure count is zero, additionally report the tighter one-sided bound 1-0.05^(1/N). It remains valid for the allocation-weighted mean under independent inputs with differing stratum probabilities, since the probability of zero failures is at most (1-p_bar)^N by concavity of log(1-p). Neither bound estimates coherent error. Pooled paired discordances are descriptive. Exact paired sign tests, if supplied, state their exchangeability null and are not used to infer a full-Shor error budget.
