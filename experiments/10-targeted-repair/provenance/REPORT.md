# QIP revision results, September 22, 2026

## What was completed

The revision adds an implemented targeted zero-payload repair, a completed frozen 100,000-input validation, a state-dependent coherent-error argument, explicit schedule/width counterexamples, and complete reversible safegcd references. It does not establish an all-input low-cost circuit or a complete-Shor error guarantee.

## Targeted repaired circuit

Source branch: `codex/qip-oral-repairs-20260922`, local commit `b8ccdd6` in `ecdsafail-qip-oral-repairs-20260922`.

| Quantity | Result |
| --- | ---: |
| Mixed peak width, matched arithmetic | 1,402 |
| Windowed peak width, w=16 | 1,419 |
| Windowing width overhead | 17 |
| Serialized static CCX+CCZ | 1,524,503 |
| Mean executed Toffolis, fresh study | 1,356,324.32985 |
| Q x T | 1,924,624,224.05715 |
| Fresh cases across nine tables | 100,000 |
| Output / phase / ancilla failures | 0 / 0 / 0 |
| Identity-addend rows retained | 4 |
| Other generic-domain exceptions found | 0 |
| One-sided 95% sampled failure upper bound | 0.00300% |

The 17 extra qubits are the 16 address qubits and nonzero-address flag. The arithmetic change from conservative windowed Q=1392 to Q=1419 is separate: 32 additional tape bits, six fewer terminal value bits, and the zero-payload flag give +27. The new mixed peak was measured by emission and the original evaluator, not inferred by subtracting 17.

The repair masks replay and endpoint signs using a reversible word-zero predicate, fixes full-width chunk carry recovery including its equality term, and uses canonical subtraction in the coordinate shell. It retains guarded ordinary replay and the empirical width taper. The zero-flag erasure is conditional on the actual input/output words preserving zero.

Both 64-denominator zero components pass, including pre-reset coefficient checks. Full w=4 and w=16 calls pass the two retained zero-slope points over 32 lanes each and the 64-case smoke set. The new source and operation stream were frozen before a new seed was generated. The study took about 37 minutes. All outcomes, batches, table specifications, source hashes, and driver identity remain in `fresh-zero-mask-100k/`. `verify_fresh.py` checks all 100,000 affine reference outputs independently in Python and reconciles counts, unique indices, addresses, and failure unions. This is not an independent quantum-phase proof.

The builder's 1,530,647 bookkeeping count includes 6,144 temporary gates discarded while emitting inverse coordinate subtraction. The authoritative 1,524,503 count is from the serialized stream. Do not mix the two.

## Important negative findings

768 rounds is not a sufficient all-input bound. Exact denominator 3 requires 1,135 transitions and 2^255 requires 1,239. Denominator 1 terminates in 512 rounds but violates the margin-20 sum-width bound at round177. Six supported affine pairs with these denominators fail all48 classical lanes in the new w=4 circuit; 25 phase flags also occur. These are six structured inputs, not 48 independent random samples. Their failures do not isolate horizon exhaustion from width overflow, since the latter can occur earlier.

The isolated generic replay cells also retain nonzero boundary defects. Fixing zero payloads and the interior carry predicate does not prove canonicality or correct post-fold carry erasure for every input. Successful frozen random tests are presented alongside these failures, not as their replacement.

## Coherent error analysis

The lookup proposition now explicitly requires phase-correct arithmetic with input-independent corrected branch amplitudes. Basis labels and clean workspace alone were insufficient hypotheses.

For a certified good projector Pi with K_m Pi = gamma_m U Pi, a state with bad weight q has trace-distance error at most min(1,2 sqrt(q)). The standalone note gives the sharper bound and a proof including entangled references. Ideal-prefix hybrid composition gives min(1,2 sum_i sqrt(q_i)) without requiring independence between calls. Actual Shor prefix distributions, not random affine sampling, determine these q_i.

The first accumulator after direct initialization from a 16-bit window has only 2^16 possible values. The next call's R=O,A!=O weight is 65535/2^32 for the stated ascending G schedule. The full arithmetic bad set is unknown. Thus the theorem supplies a conditional route to a guarantee, not a numerical full-Shor bound. Matrix tests, phase counterexamples, and prefix checks are retained in `coherence/`.

## Safegcd comparison

The complete reversible DIV/MUL references use the same canonical payload primitives and full-width layout conventions:

| Reference | Rounds | Q | Static Toffolis per DIV or MUL | Failures on 128 common cases per direction |
| --- | ---: | ---: | ---: | ---: |
| Safegcd | 741, proved bound | 3,300 | 7,501,932 | 0 |
| Ping-pong | 768, conditional | 2,320 | 6,289,400 | 12 |
| Ping-pong | 1,536, conditional | 3,088 | 12,574,712 | 0 |

Small-prime exhaustive tests cover 5,196 cases per direction for each construction, with coherent checks on four small primes. Full point-addition w=4 integration also passes 64 common cases, but that shell test uses different arithmetic lowering in its two callbacks and cannot isolate the recurrence. All references are deliberately unoptimized. The favorable and unfavorable orderings are retained. No advantage over an optimized safegcd implementation is established.

## Status of the four requested priorities

1. Low-cost boundary repair: targeted repair implemented and validated. General boundary-safe arithmetic remains unresolved.
2. Coherent-error analysis: conditional theorem, proof, and prefix analysis completed. Certified complete bad-set weights remain unresolved.
3. 768-round justification: candidate implemented and evaluated; an all-input sufficiency claim is disproved by explicit counterexamples. Full-width range bound is proved, but its allocation is more expensive.
4. Reversible safegcd baseline: complete components, matched primitive comparison, and shell integration implemented. An optimized accuracy-matched comparison remains open.

## Deliverables

Manuscript source: `outputs/ECDSAFAIL_QIP2027_oral_research_revision/`.
Final PDF and lean Overleaf ZIP are in `outputs/` with the same prefix.
The separate `ECDSAFAIL_QIP2027_oral_evidence.zip` retains scripts, source, ledgers, proofs, and negative results. Large gate streams and native binaries are omitted with hashes and regeneration commands.

The earlier public evidence v1.3.0 and original frozen studies are unchanged. This new supplement has not been published to GitHub. The extended abstract remains separate.
