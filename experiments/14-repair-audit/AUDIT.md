# Adversarial Audit: Repairs, Fusion, Coherence, and Round Budgets

Date: 2026-09-22. Scope: `outputs/ECDSAFAIL_QIP2027_eval_rewrite`, retained boundary diagnostics, and the canonical reference source. This is a bounded source/algebra audit. No production circuit or manuscript was modified. All new files are in this directory.

## Findings, Ranked

### P1: The lookup-coherence proposition has an insufficient arithmetic hypothesis

Location: `outputs/ECDSAFAIL_QIP2027_eval_rewrite/sections/05-window-selected-addition.tex:83`, proof at line 97.

Producing the correct basis labels, restoring lookup payloads, and clearing workspace do not exclude an input-dependent arithmetic phase. Correcting every payload/routing measurement phase does not fix a phase already introduced by the arithmetic. For example, compose ideal addition with a diagonal sign on one valid input. Every stated basis-label/restoration condition holds, and lookup cleanup can be exact, but the equal superposition of that input and a phase-zero input has an orthogonal output to the ideal result. This is a counterexample to the proposition as literally stated, not a claim that the lookup decoders themselves are defective.

The proof's assertion that the remaining branch amplitude is input-independent does not follow from its hypotheses. Explicitly assume phase-correct coherent arithmetic, including arithmetic measurements and resets, with a common input-independent branch scalar. Alternatively prove that property from the primitives. The older commented proposition at lines 118-121 actually states the intended coherent-map assumption more clearly.

The conditional arithmetic proposition in `04-gate-efficient-circuits.tex:344` explicitly assumes correct phase corrections and is better scoped. For the canonical-replay proposition in `12-technical-details.tex:68`, clarify that the value circuit computes/uncomputes *coherently and phase-correctly*, not just correctly on basis words. Its proof does explicitly mention exact carry-measurement corrections. No new gate-level counterexample to the canonical replay primitives was found in this pass.

### P1: Cheap repairs are not a composable exactness package

The old replay can emit word `p` from canonical inputs even with no fold escape: inverse cell `z=1, y=p-2, sign=0` computes `2z+y=p`. The raw carry is zero, so folding leaves word `p`. An isolated canonical zero-aware negation has no valid clean action on both words `0` and `p` that merges them to zero. Its zero-flag cleanup depends on preserving the zero predicate, which fails on input `p`.

Thus replacing endpoint negation alone cannot establish the reference's canonical invariant. All producers, including the special seed, ordinary cells, initialization, and shell handoffs, must satisfy the receiving primitive's range contract, or the representation history must remain reversibly encoded. In particular, do not wire a canonical negation or canonical subtraction into a raw-residue path and infer correctness from its local canonical tests.

Sources: canonical `canonical_replay.rs:17`; old `pingpong_div.rs:603,999,1176`; retained `boundary/REPORT.md:240-281`. The local fused witness above is newly scalar-checked. It is not asserted to be a reachable complete point-addition trajectory.

### P1: Exact carry equality does not repair post-fold overflow erasure

For an unsigned chunk, `cout = [z<a] OR (cin AND [z=a])`. Exhaustive small-width testing confirms the identity. The old reverse-order cleanup retains the previous chunk carry long enough to use it, so a repair is structurally plausible, but full equality detection and its phase-controlled application have a cost. A prefix-equality term is not equivalent to full equality. Full-width strict comparison alone still fails.

Separately, signed add `sign=1, source=1, target=0` wraps its complemented sum to zero with carry one. After adding `F`, comparing the corrected target against source gives `[F<1]=0`, even at full width. The original carry is one. Fixing all interior carry equalities leaves this independent phase defect.

Source: old `pingpong_div.rs:737` and final carry cleanup following its signed arithmetic cells. Retained paired-measurement witnesses: `outputs/qip2027-mechanism-revision-20260908/boundary/REPORT.md:140-188`. Reverse cleanup order matters: the incoming carry must not be measured/reset before its equality-controlled phase is applied. Audit first-chunk `cin=0` separately from later chunks.

### P1: A full-width fold is not automatically a correct modular fold

Let `B_0=2^256`, `F=2^32+977`, `p=B_0-F`. With canonical inputs `z=p-1`, `y=2F+1`, `sign=0`, the integer sum is `2B_0-1`. Its raw low word is `B_0-1`, with raw quotient one. A single 256-bit wrapped `+F` produces `F-1`, while the correct field result is `2F-1`. A second escape correction is required. This new scalar witness refutes treating "widen to 256" as a universal repair.

For a short fold of width `ell`, a sufficient no-escape guard is `0 <= (omega mod 2^ell)+kappa_frame*F < 2^ell`. Outside it, the operation loses a carry/borrow into higher bits. Widening 56 to 72 bits removes many observed triggers but is still a guard, not a proof. The retained smoke input 50 demonstrates the actual 56-bit failure at inverse round 271, where `+2F` loses `2^56`.

A coherent escape path needs carry propagation or a proved bounded secondary fold, plus clean flag recovery. Measuring an input-dependent escape flag and routing classically is not a free repair for Shor. Secondary corrections can change output parity, so the existing doubling-overflow parity identity and post-fold phase predicate must be rederived, not copied unchanged. Canonical reduction is another separate obligation: avoiding escape does not prevent output word `p`.

Sources: `04-gate-efficient-circuits.tex:377`; old `pingpong_div.rs:999`; `outputs/qip2027-followup-diagnostics/REPORT.md:3-25`.

### P2: Raw and complemented kappa have the same union of values, not the same meaning

Location: `04-gate-efficient-circuits.tex:368-375` and the commented source-corresponding derivation at lines 387-406.

The stated raw range `{-1,0,1,2}` is **not itself false**. For unsigned n-bit operands, raw addition uses `{0,1,2}` and raw subtraction uses `{-1,0,1}`. The problem is moving directly from that raw-word identity to the emitted selector/parity implementation, which operates in a complemented subtraction frame. On subtraction branches the correction coefficient has the opposite sign.

Define `2z=z0+d B_0`, `C_0(v)=v`, `C_1(v)=B_0-1-v`, and `C_sigma(z0)+y=omega+o B_0`, with `d,o` bits. Then

```
kappa_frame = o + (-1)^sigma d
kappa_raw   = kappa_frame             (sigma=0)
kappa_raw   = -kappa_frame            (sigma=1)
w           = C_sigma(omega)
2z+(-1)^sigma y = w+kappa_raw B_0.
```

Provided the correction does not escape its represented range,

```
C_sigma(omega+kappa_frame F) = 2z+(-1)^sigma y (mod p).
d = (omega+kappa_frame F)_0 XOR sigma XOR y_0 XOR o.
```

Example: `z=B_0/2, y=0, sigma=1` has `kappa_raw=+1` but `kappa_frame=-1`. Do not attach the raw quotient to the emitted `-F,0,F,2F` selectors without explaining the frame. The parity sentence should mention the source parity, sign, and addition carry as well as corrected-target parity. Exhaustive small-prime checks verify both identities and the guarded parity relation.

### P2: Halving underflow needs new flag cleanup, not only a top-bit patch

Old `pingpong_div.rs:1133` subtracts `rF`, where `r=t mod 2`, rotates, and toggles the top bit by `r`. Even with a full-width subtraction, `t=1` gives an error of `2^255`: the wrapped subtraction has already supplied the needed high contribution.

For canonical `t`, let `beta=[t<rF]` and `v=t-rF+beta B_0`. Then the correct scalar rule is

```
half(t) = v/2 + (r-beta) B_0/2.
```

Since `beta<=r`, the required top-bit insertion is `r XOR beta`. But the old cleanup expects the final top bit to reproduce `r`; after this patch it reproduces `r XOR beta`. Retaining a borrow without changing that cleanup leaves garbage. Exact recovery is possible from canonical output `h`:

```
r    = [h >= (p+1)/2]
beta = [(p+1)/2 <= h < B_0/2].
```

These are scalar identities, not measured cheap circuit constructions. Comparators and their cleanup must be costed. The canonical reference instead uses a 257-bit `t+rp`, then divides by two, and loads a 256-bit threshold to clean `r` (`canonical_replay.rs:45`). Both forward and inverse replay, including the specialized first/second rounds, need matched tests.

### P2: Exact coordinate subtraction is a separate repair with shell-live overhead

For input zero and any canonical nonzero subtrahend `a`, the output is `p-a`. Output plus subtrahend equals `p`, which has no carry at `B_0`; it cannot recover the modular borrow. This defect survives canonical replay replacement, as the retained replay-only failed attempt demonstrates.

The reference routes both subtraction wrappers through `mod_sub_qq`, the inverse of canonical addition: `trailmix_ludicrous/arith.rs:1830-1841`, `arith/modular.rs:4-37`. This covers three call sites, not just the final y operation. Replacing only the final call leaves the initial differences exposed. The low-peak wrapper now uses the general exact primitive: loaded table payloads, address/identity controls, and temporary arithmetic workspace must be included when measuring peak width. A local replay peak does not establish the full-call peak.

The other shell routines are inherited, including `mod_add_windowed_lowpeak` with a 64-bit comparison (`trailmix_ludicrous/arith.rs:1760-1763`). Consequently the reference does not prove that *all* shell-to-replay handoffs are canonical on every supported input. This is an outstanding proof obligation, not a newly reproduced full-reference failure.

### P2: 768 rounds is an empirical candidate, not a guarantee

The manuscript currently handles this correctly: `12-technical-details.tex:54` says maximum 743 over 10 million sampled denominators, with 6 exceeding 736 and none exceeding 768/800. Zero of 10 million implies a pointwise one-sided 95% upper bound approximately `2.9957318248e-7` under independent sampling, not zero error and not `1e-7`. No >768 witness was found or searched for here.

The ordinary exact-recurrence lemma proves `3n(n+1)=197,376` rounds at n=256. It does not establish 768, the specialized initialization's total accounting, or the shrinking-width schedule. A 768-round implementation must separately validate active signed input and sum widths before halving, terminal signed units, reverse reconstruction, transcript lifetime, and peak allocation. Adding rounds cannot recover information lost earlier by narrowing. The canonical reference actually retains **736** rounds, not 768.

The denominator experiment is not a field-payload test and does not provide a joint point-addition or coherent-channel bound. Do not exponentiate its rate or basis-state success rates into a 28-call Shor claim. Operator/channel bounds compose differently, and a Shor amplitude distribution is not established by uniform denominator sampling.

## Cost and Guarantee Ledger

| Proposed repair | Established evidence | Hidden cost or unresolved obligation |
|---|---|---|
| Equality-aware chunk cleanup | Exact scalar predicate; retained phase witnesses | Full equality, live incoming carry, phase controls; independent final-overflow defect remains |
| Zero-aware canonical negation | Retained 9,200 local tests; Q=514, T=777 | Local delta +153 qubits, +662 Toffolis versus guarded unary baseline; not an integrated peak delta; excludes word p |
| Borrow-aware halving | New scalar rule and cleanup predicates verified | Borrow storage, two flag recoveries, general/fused/seed consistency |
| Exact coordinate subtraction | Retained reference fixes traced shell failure | Full-width arithmetic overlaps table payloads; inverse-emission bookkeeping differs from stream count |
| Wider or escape-aware fold | Retained 56-bit failing trace; new full-word counterexample | Secondary overflow, canonical range, revised parity/phase cleanup; no measured exact cheap implementation |
| Whole canonical reference | Retained Q=1,804; static T=5,188,043; fresh 0/4,096 | Finite 736 rounds, finite signed widths, inherited square/shell; separate study and configuration |

The reference's mean executed T is 5,187,616.277587891 on its pilot. Do not replace that by the intermediate builder count: constructing then discarding forward blocks for three inverse subtractions adds 6,144 bookkeeping Toffolis that are not in the serialized stream. Neither the historical low-cost resource advantage nor a new cheap repaired resource point follows from the reference.

## New Tests Actually Run

Command: `python3 research/qip-oral-20260922/limitations/check_algebra.py`.

- 174,760 exhaustive chunk cases, widths 1-8; 510 counterexamples to strict comparison alone.
- 8,982 exhaustive fused scalar cases over p=13,29,59; raw/frame identities hold. Guarded parity identity holds in 8,810 cases.
- 4,491 canonical source/target pairs verify reduction-flag predicates; unary doubling/halving and borrow-recovery checks also pass over those fields.
- secp256k1 scalar witnesses verify frame-sign mismatch, noncanonical output from canonical inputs, full-word fold escape, post-fold carry mismatch, halving-one failure, and modular-borrow/ordinary-carry mismatch.
- A two-dimensional diagonal-sign example establishes the coherence-hypothesis gap: basis labels and workspace pass while equal-superposition fidelity is zero.

Results: `algebra-results.json`. These are specification-level checks. No new Rust emission, resource benchmark, full-call simulation, or fresh population study was performed. Retained gate-level outcomes above are cited as historical evidence, not rerun results.

Read-only SHA-256 checks also matched the reference's existing `candidate-freeze.json` for all three inspected repair implementation files:

| File under reference `source/src/point_add/` | SHA-256 |
|---|---|
| `canonical_replay.rs` | `cd6c827cdae01e1746a1589b003c672fd48cc43976abde567ef3a0ca78627eed` |
| `trailmix_ludicrous/arith.rs` | `73419c06ffd8ca577fe463c055a2f8f9bc09368afce36d90a5953a7914e7471a` |
| `arith/modular.rs` | `eabf995082958fdd8b3afbaa09f3c7ea5f6a3a8b5fe79e88206eab07709dcb6e` |

This checks these source anchors only, not the complete freeze or the approximately 14 GB operation stream.

## Useful Next Gate-Level Tests

1. **Isolated carry repair:** exhaust widths 1-8 with both carry-ins and every measurement branch. At actual boundaries 86/171, pair the `0-1` witness with a phase-zero control under identical one-hot randomness. Include prefix ties with unequal low words and exact ties with carry one. Check the original carry register before reset.
2. **Post-fold flag repair:** inject signed add `(sign,source,target)=(1,1,0)` and fused forward `(1,2,0)`. Compare the stored pre-fold overflow with the reconstructed predicate before measurement. Equality-only and full-comparison-only variants are negative controls.
3. **Representation composition:** feed the ordinary inverse cell `(0,p-2,1)` into zero-aware negation. Require exact words, source/sign preservation, pre-reset zero flags, and relative phases. Keep explicit word-p tests as out-of-contract negatives, not silently reduced expected outputs. Test seed only with its documented zero target, then test its actual replay caller.
4. **Halving:** use odd t=1,F-2,F,F+2, plus 0,2,p-1 and both directions; test all recovery flags, not only output value. In the fused cell vary source/sign and force pre-half boundaries. Test full-width and short-window subtraction separately.
5. **Escape:** force low fold words at 0,1,2^ell-1 and correction thresholds for each of -F,0,F,2F, for ell=56,72,256. Include the new `(z,y)=(p-1,2F+1)` witness and retained smoke input 50. Distinguish local fold escape, whole-word overflow, canonical reduction, and phase cleanup.
6. **Coordinate shell:** test `0-a`, `a-a`, `a-0`, both controls, all three call sites, and identity lookup. Repeat the two supported cube-root zero-slope points at w=4 and w=16. Assert canonicality at every handoff to canonical primitives and restored payloads before QROM measurement.
7. **Coherent branches:** for reduced-size cells, explicitly check each corrected Kraus branch satisfies `K_m|x> = gamma_m U|x>` with the SAME gamma for every valid x. Use pair superpositions sharing and differing in address, include identity and nonidentity entries, and reject arithmetic-induced phase defects even when outputs/reset ancillas pass.
8. **Candidate promotion:** freeze the exact combined knobs and stream hash; collect Q, serialized static T, executed T, pre-reset checks, and all failure channels from that same configuration. Run held-out shifted-table inputs only after the targeted suite passes. A 768/width change requires a fresh cost and correctness ledger; do not combine cost receipts from a different variant.

## Source Anchors

All paths below are relative to the workspace root, not this report directory.

- `outputs/ECDSAFAIL_QIP2027_eval_rewrite/sections/04-gate-efficient-circuits.tex`
- `outputs/ECDSAFAIL_QIP2027_eval_rewrite/sections/05-window-selected-addition.tex`
- `outputs/ECDSAFAIL_QIP2027_eval_rewrite/sections/12-technical-details.tex`
- `ecdsafail-qip-oral-repairs-20260922/src/point_add/pingpong_div.rs` (source inspected, not edited)
- `outputs/qip2027-canonical-repair/source/src/point_add/canonical_replay.rs`
- `outputs/qip2027-canonical-repair/source/src/point_add/trailmix_ludicrous/arith.rs`
- `outputs/qip2027-canonical-repair/source/src/point_add/arith/modular.rs`
- `outputs/qip2027-canonical-repair/README.md`, `candidate-freeze.json`
- `outputs/qip2027-mechanism-revision-20260908/boundary/REPORT.md`
- `outputs/qip2027-followup-diagnostics/REPORT.md`, `replay_model.py`
