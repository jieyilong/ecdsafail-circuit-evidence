# Structured-Zero-Payload Diagnosis

Date: 2026-09-08. Status: rigorous bounded diagnosis, no general coherent repair.

## Conclusions

The published 64-denominator observations reproduce exactly. There are distinct
representation, carry-erasure phase, and nonzero-reset mechanisms. The zero
payload findings are not explained by value-walk nonconvergence. Simply widening
comparisons or correction windows does not fix them.

These results concern raw emitted cells and the published isolated probe
components. The optimized entire point-addition kernel was not reevaluated.

1. Conditional negation and the specialized seed create the word `p` from `0`.
   Both words represent field zero, but they are different computational-basis
   states. This alone is not evidence of a complete point-addition failure.
2. Chunk-carry erasure uses a strict comparison that omits an incoming-carry
   equality case. Narrow prefixes add another failure, but full-width comparison
   does not repair the equality case.
3. Overflow erasure compares the already corrected word with the source. At the
   boundary this predicate need not equal the pre-correction carry, even with all
   256 bits compared.
4. Multiplication releases a coefficient register containing `p` in 35/64 cases.
   The emitted resets make final ancillas zero but introduce additional sampled
   phase changes. This qualifies the source comment claiming a proved-zero release.
5. Boundary payload `1` exposes a separate halving underflow/parity assumption.
   Full-width subtraction still leaves a field-value error in this case.

A canonical-input negation candidate passes a separate 9,200-evaluation local
regression at `Q=514`, `T=777`. It is not inserted into either replay. It is not a
repair of arbitrary `p` representations, multiplication, division, or point addition.

## Scope And Integrity

Read before diagnosis: `ECDSAFAIL_PAPER_NOTATION.md`, the circuit optimization
skill, current paper `06b-bounded-validation.tex` and `12-technical-details.tex`,
and the published `experiments/05-zero-payload` records. The frozen arithmetic
source is `ecdsafail-circuit-evidence/sources/trees/conservative-pingpong`; the
published diagnostic is `sources/trees/zero-payload-probe`, derived from source
`345c23fcf1073b7559a9d41e113f755259545bf2` according to its retained README.

All new files and copied-source changes are inside this `boundary/` directory.
`frozen-sha256.json` and `integrity.json` verify both frozen trees are unchanged.
The copied simulator, circuit definitions, field/curve reference, library, all
three evaluator entrypoints, Cargo manifest, and lockfile remain byte-identical.
The original zero-probe helper and production selfcheck assertions remain intact.
`source.diff` contains all diagnostic additions and explicitly gated hypotheses.

The only runs are individual cells, local negation regression, and the original
single multiplication/division components. Each component operation vector is
about 411 MB and is dropped before the next direction. No full point-addition,
windowed, full-Shor, or serialized `ops.bin` stream was generated. Larger-width
component variants were not run because their cell hypotheses already failed.
No nonce search, new 100,000-input study, promotion, paper edit, commit, or push.

## Reproduced Component Results

The original SHAKE seed is `qip-posthoc-zero-payload-probe-v1`; knobs are exactly
`QIP_PINGPONG_PROFILE=guarded`, `TLM_MSBS=40`, with unrelated override variables
removed by the runner.

| Direction | Output word p | Phase flags | Denominator mismatches | Final dirty ancillas | Nonzero coefficient before release |
|---|---:|---:|---:|---:|---:|
| Divide | 28/64 | 19/64 | 0 | 0 | 0/64 |
| Multiply | 46/64 | 26/64 | 0 | 0 | 35/64 |

All observed component outputs are either `0` or `p`, so every output remains
field-congruent to zero. Representation and phase overlap in 11 division cases
and 26 multiplication cases. Their unions are 36 and 46, respectively, not the
sums of the two columns. These are component diagnostics, not point-addition
failure rates or held-out accuracy estimates.

| Direction | Peak Q | Executed Toffoli sum over 64 lanes | Mean executed T | Operation count |
|---|---:|---:|---:|---:|
| Divide | 1,375 | 32,579,736 | 509,058.375 | 7,346,835 |
| Multiply | 1,375 | 32,580,368 | 509,068.25 | 7,351,237 |

These costs are for the raw isolated emitter before whole-circuit optimization,
not replacements for the paper's point-addition resource figures. No `Q*T`
comparison or promotion is inferred from these component costs.

The exact signed precheck independently reproduces all 64 convergence rounds,
with maximum 667, and checks the shrinking widths including pre-halving sums.
An auxiliary precheck of denominators `1..256` and `p-1` finds width violations
for every one. For `d=1`, the first violation is a 225-bit pre-halving sum at
round index 177, despite eventual exact convergence in 512 rounds. Those small
denominators were not used as coefficient-only component witnesses. Small
*payloads* in individual cells have no such value-walk confound.

## Representation Path

Here `p=2^256-f`, `f=2^32+977`. Source-level `sign=0` means addition and `sign=1`
means subtraction; this is a replay control, not a new point-addition notation.

In frozen `pingpong_div.rs:583`, `conditional_mod_negate` complements all payload
bits and subtracts `f-1` under the control. When the control is one,

```
~0 - (f-1) = (2^256-1) - (f-1) = p.
```

The specialized `seed_round_one` at line 1132 has the same zero-to-`p` behavior
when its source is zero and sign is one. Calling these operations canonicalizers
without a nonzero/range qualification is therefore too strong.

The first published fixture with a division output word `p` is index 2:

```
d = 0x5bbcc8237074168eead8444272fb5e8fce310594ce4d154685d8fa746addeeec
```

Its terminal value registers are both `-1` (11-bit word `0x7ff`). Its replay
ends at coefficient/payload `(0,0)`. The two terminal negations turn that into
`(p,p)`, and XOR cleanup then leaves `(0,p)`. In this sampled lane the final
phase is zero. This is a clean example of representation failure without a
field-value or phase failure.

Fixture index 4 provides an early internal zero-representation path:

```
d = 0x8c61e060920d1b20be1238ba6a0951bf54d718035e8bf07aebd6bfb086d81279
round 1: seed sign 1 creates coefficient/payload (p,0).
round 2: source p, target 0, sign 0 produces (p,p).
round 3: source p, target p, sign 0 reaches phase-sensitive carry erasure.
```

Round 3 is phase-sensitive even when its particular sampled outcomes cancel.
Do not confuse the first phase-sensitive cell with the first nonzero sampled
phase flag. `trace-excerpts.log` retains exact operation offsets and states;
`logs/component-final.log` contains the complete selected-lane trace.

## Exact Phase Witnesses

Operation and randomness-event indices below are zero-based in the isolated
cell. Source line numbers refer to the unchanged conservative tree. Final copied
source line numbers are also printed by `TRACE_OP_SITES` in the witness logs.

The smallest-valued phase-only example retained here is signed modular add with
`sign=1, source=1, target=0`. The output is the correct canonical `p-1`, but three
measurement outcomes have uncancelled phase dependence. This is a small witness,
not a claim of a globally minimal witness over every possible cell/input.

| Erasure | Cell op index | Random draw index | Qubit | Classical bit | Frozen gate path |
|---|---:|---:|---:|---:|---|
| Carry at bit 171 | 2799 | 506 | 599 | 253 | `signed_mod_add_pm -> add_chunked_measured -> hmr`, line 742 |
| Carry at bit 86 | 3285 | 589 | 514 | 294 | same, line 742 |
| Final overflow | 4530 | 880 | 513 | 439 | `signed_mod_add_pm -> hmr`, line 1078 |

The standard chunk partition is `[0,86), [86,171), [171,256)`. The complemented
input target is `2^256-1`. Adding source `1` gives raw target zero and carry one
at both interior boundaries and the register boundary.

For a chunk with source `a`, incoming carry `c`, and output `z`, the correct
carry-out predicate is

```
(z < a) OR (c == 1 AND z == a).
```

The implemented cleanup at lines 738-744 uses only a strict comparison of the
top 40 bits. For the bit-171 carry, `a=z=0` and incoming carry is one, so even
comparison of the complete 85-bit chunk returns the wrong predicate. For the
bit-86 carry, the full words are `z=0, a=1`, but their 40-bit prefixes are equal.
Full-width comparison fixes the latter, not the former.

After the final carry-one correction, the complemented-frame target is `f`.
The overflow cleanup compares `f < 1`, which is false even at full width,
although the stored overflow is one. Thus it needs a correction-aware predicate
or access to the pre-fold relation, not merely more comparator bits.

The main forward replay has the equally direct phase-only witness
`signed_mod_add_pm_halve_fused(sign=1, source=2, target=0)`. Its correct output is
also `p-1`. It has the same two chunk erasures, followed by overflow `Hmr` at
op 4959, draw 821, qubit 513, classical bit 408 (frozen line 938). For the
zero-representation state `sign=0, source=p, target=p`, the same three draws
are uncancelled. The latter is reached in the actual fixture-4 replay above.

Each witness uses the unchanged simulator with an auxiliary XOF reader that sets
one randomness draw to one and all others to zero. All randomness positions are
tested, not just the suspected draws. Paired lanes receive the same measurement
assignment: 32 lanes have source/target zero and 32 have the witness. The observed
phase mask is `0xffffffff00000000`, demonstrating input dependence rather than
a common global phase. The resulting XOR phase rule also matches eight SHAKE
seeds of 64 lanes for each of the six witnesses and all three width settings.
These local checks are not a full-circuit coherent simulation or a proof for all
measurement branches of arbitrary inputs.

## Nonzero Coefficient Reset

Frozen `pingpong_div.rs:130` calls `B::free_vec`, which calls `B::free`
(`mod.rs:501`). `free` emits `R`; it does not assert that the wire is zero.
The unchanged simulator's `R` handling (`sim.rs:157`) XORs the old qubit value
times a random outcome into the phase, then clears the qubit.

In multiplication, the pre-release nonzero mask is `0xef1798b3b5ea5690` (35
lanes). Fixture 4's coefficient is specifically `p`, not canonical zero.
Across the release alone the phase changes by `0xcc151032b5a24610` (23 lanes).
The subsequent denominator restoration changes no phase in this 64-lane run.
The final phase count is 26, not the sum of the replay and reset counts.

Division has zero coefficient before release in every fixture and no phase
change across release. Its phase defects are already present earlier. Therefore
the reset finding must not be generalized to both directions.

## Boundary Value Failure

The guarded `mod_halve_pm(1)` and fused-halving `(source=0,target=1,sign=0)`
both fail field congruence, unlike the component's zero-word outputs. These
are separate local boundary counterexamples, not newly claimed point-addition
failures.

In `mod_halve_pm` (frozen line 1091), the low odd-bit flag selects subtraction
of `f`, followed by the bit rotation and a flag-controlled top-bit toggle.
The guarded endpoint borrow chain stops short of 256 bits. But even expanding
it to full width does not suffice: for input one, subtraction wraps to
`2^256+1-f`. After the right rotation the value is already the desired
`(p+1)/2`. The retained odd-bit flag then toggles bit 255, producing an answer
that differs from the desired one by `2^255`. A borrow-aware parity correction
or a differently proved halving implementation is required at this boundary.

## Hypotheses And Local Costs

Three bounded correction hypotheses were tested. No gate-changing hypothesis
was installed into a component run.

1. `full_compare`: compare the full 86/85-bit chunks and all 256 overflow bits.
   Rejected as a general fix: the carry-in equality and post-fold overflow
   counterexamples remain. For the signed-add `(1,1,0)` witness, two of the
   original three uncancelled draws remain.
2. `full_width`: additionally expand fused folds, endpoint corrections, and
   seed corrections to full 256-bit coverage. Rejected: the halving-underflow
   counterexample and phase failures remain. Original full-width negation still
   sends zero to `p`. Widening even creates an overflow-phase defect for fused
   halving `(sign=0,source=p,target=0)`, which has no such phase defect under the
   original prefix check. That negative result is retained.
3. `canonical_negate_exact`: separately compute a zero flag, use
   `control AND nonzero` for a full-width `p-x` operation, then uncompute the
   controls and zero flag. On canonical inputs, negation preserves zero/nonzero,
   justifying this local cleanup. Its scope does not include input word `p`.

The cell grid is `{0,1,2,f-1,f,f+1,floor(p/2),p-2,p-1,p}` with both signs.
The specialized seed is tested only with its required zero target. The unary
cells have an unused source register solely for common harness layout. Records
separate canonical inputs from cases involving word `p`; none are discarded.
Each two-input canonical slice contains 162 rows. Its field/phase counts are:

| Cell | Guarded field / phase | Full compare field / phase | Full width field / phase |
|---|---:|---:|---:|
| Signed add | 5 / 30 | 5 / 15 | 0 / 23 |
| Fused halve | 24 / 26 | 24 / 23 | 14 / 32 |
| Fused double-add | 3 / 17 | 3 / 18 | 0 / 23 |

Counts use the stated SHAKE fixture and are not statistical error estimates.
Changing gates changes the measurement schedule, so these phase counts are not
paired-measurement improvements. The one-hot witnesses establish the mechanism.
All cell runs retain exact-word, field, source/control preservation, phase, and
final-ancilla results in `cell-summary.csv` and raw `cells-final-*.log` files.

| Raw two-input cell | Guarded Q / emitted Toffolis | Full compare Q / emitted Toffolis | Full width Q / emitted Toffolis |
|---|---:|---:|---:|
| Fused halve | 600 / 457 | 772 / 756 | 775 / 940 |
| Fused double-add | 601 / 457 | 771 / 756 | 777 / 940 |

The local canonical-negation regression uses 575 distinct canonical values,
both control values, and eight measurement seeds, totaling 9,200 evaluations.
It includes `0`, `1`, `p-1`, small integers, `f` boundaries, powers of two, and
their complements modulo `p`. All exact-word, field, control, phase, and final
ancilla checks pass. The dedicated one-register circuit measures `Q=514` and
exactly 777 executed Toffolis per input, 7,148,400 in total. The original
guarded negation's corresponding width is 361 (617 minus the unused 256-bit
harness source), with 115 Toffolis: the local change costs +153 qubits and
+662 Toffolis. These are not integrated peak or total-cost deltas.

Input word `p` is an explicit negative test for this local candidate: its zero
predicate need not uncompute cleanly after mapping `p` to `0`. The sampled
phase failure is retained. A context-free clean map taking both `0` and `p`
to `0` would merge distinguishable inputs and cannot be a reversible unitary.
Normalizing the *reported* component output modulo `p` would hide every word
mismatch but would leave all phase flags unchanged. No such postprocessing is
used to alter acceptance or claim repair.

## Reproduction

Run from this directory. The runner records exact subprocess commands, sanitized
knobs, elapsed time, return code, and final binary/source SHA-256 hashes in the
matching JSON receipts. Build dependencies are already cached; build is offline
and single-job. These commands generate only local diagnostics.

```sh
python3 run.py build --tag reproduce-build
python3 run.py baseline --tag baseline-final
python3 run.py component --tag component-final
python3 run.py cells --tag cells-final-baseline
python3 run.py cells --variant full_compare --tag cells-final-full_compare
python3 run.py cells --variant full_width --tag cells-final-full_width
python3 run.py witnesses --tag witnesses-final-baseline
python3 run.py witnesses --variant full_compare --tag witnesses-final-full_compare
python3 run.py witnesses --variant full_width --tag witnesses-final-full_width
python3 run.py local_regression
python3 value_walk.py
python3 analyze.py
python3 summarize_component.py
python3 run.py verify
python3 test_receipts.py
```

`frozen-sha256.json` is the initial immutable-source receipt; do not regenerate
it as a substitute for verification. Earlier instrumentation logs are preserved
alongside the `*-final*` records. `test-results.json` records the receipt tests.
All eight receipt tests pass. `runtime.json` records the local toolchain, and
`artifacts-sha256.json` hashes the retained sources, logs, scripts, and report
(excluding generated build/cache directories). Run `python3 finalize.py` after
reproduction to refresh that local artifact manifest.

## Integration-Ready Finding

The structured-zero diagnostic reproduces the previously reported division and
multiplication observations and identifies mechanisms in the raw emitted
subroutines. Zero-to-`p` seed/negation behavior preserves field congruence but not
canonical encoding. Small gate-level witnesses expose missing carry-in equality
and correction-aware overflow conditions in measurement-based cleanup. In the
64-case multiplication probe, 35 coefficient registers are nonzero immediately
before reset despite zero final ancilla values. These are emitted-cell and
component findings, not new failure counts for the optimized point-addition
kernel. A separately tested canonical-input negation does not establish a
complete zero-payload repair.

## Stop Decision And Claim Boundaries

Stop here. A general coherent repair would need a representation contract
through the seed, both replay directions, endpoint negation, and coefficient
cleanup, plus carry-in-aware and correction-aware phase predicates and a proved
boundary-safe halving path. The isolated canonical-negation success does not
establish this composition. Further integration or a new parent comparison
requires a separately authorized bounded task.

These findings do not alter the frozen random study, its zero-failure result,
or the paper sources. They sharpen the mechanism behind the existing structured
boundary caveat. They neither prove that all zero payloads fail nor that all
zero cases can be repaired by normalization. They do not establish a failure
count for complete point addition or correlated windowed Shor execution.
