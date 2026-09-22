# Frozen Targeted Variant: Independent Follow-Up Audit

Review date: 2026-09-22. This persists the previously delivered read-only review.
The accompanying script now reruns the same independent transcription checks
and writes a fresh receipt. No frozen source is edited or imported by the script.

## Verdict

No implementation defect was found in `zero_into_blocks`, `with_payload_sign`,
or the newly selected exact chunk-carry cleanup. Their local correctness does
not certify the remaining approximate arithmetic or complete point addition.
The reported 48 structured output failures remain decisive counterexamples to
all-input correctness, regardless of the separate fresh-100k study's outcome.

## Reproduction

Run from the workspace root:

```sh
python3 -B research/qip-oral-20260922/limitations/check_followup_transcription.py
```

The script uses only the Python standard library. It writes only
`followup-transcription-results.json` beside itself. Do not use `python -O`.
It verifies all 51 source hashes in the existing frozen manifest before and
after running, without changing the manifest. A source mismatch is a hard
failure, not an invitation to regenerate the freeze. It does not read the
fresh-study outcomes, emit a circuit, rebuild Rust, or inspect/hash the large
operation stream.

The receipt records Python version, script hash, freeze hash, checked source
hashes, case counts, test generation, outcomes, and run time. Repeated runs
produce the same tests and counts, with a new receipt timestamp.

## Checks and Coverage

| Check | Cases | Coverage |
|---|---:|---|
| Blocked zero helper | 5,512 | Widths 1,2,31,32,33,64,255,256; zero, all ones, each single-set-bit word; both initial output bits; measurement seeds 0-3 |
| Carry comparator | 74,896 | Widths 1-5; every operand pair, both incoming carries, every internal measurement assignment |
| Actual-width comparator | 1,024 | 512 cases each at widths 85 and 86; seeded operands/outcomes; equality forced every third case |
| Exact denominator schedule | 3 | Denominators 1,3,2^255, specialized first transition, exact signed sums, margin-20 width checks |

These are independent Boolean/phase gate transcriptions. The simulator tracks
computational-basis bits and the phase contributed by X-basis measurement and
its feed-forward correction. It is not an execution of emitted Rust gates or
a full state-vector simulation. The zero-helper measurement coverage is seeded,
not exhaustive. Actual-width comparator coverage is also sampled. The exhaustive
comparator counts apply only to widths 1-5, with the outer phase condition set
to one; condition zero skips those helper gates.

### Blocked Zero Predicate

The helper toggles `output` by `[value=0]`, preserves `value`, and clears every
block flag and AND-chain ancilla with zero net phase in the tests. Both initial
output values are checked, so the test covers XOR-into semantics rather than
only preparation into a clean output.

At n=256, the transcription uses 39 temporary qubits excluding the input and
output, and 503 CCX per zero test. This is a local helper count, not an integrated
peak or complete candidate cost. The persistent payload flag is one additional
qubit; its construction and erasure are not gate-free.

### Masked Sign

Source inspection confirms forward `h*e` and reverse `h*(1-e)`. The inversion
is performed before the masked AND and undone only after its measurement-based
uncomputation. The original sign and payload flag remain available. Called cells
restore their sign control, including temporary sign flips inside fused cells.

On the input-word-zero branch, the zero coefficient pair stays zero under the
masked seed, ordinary replay, and terminal corrections. On the nonzero branch,
the sign choices are unchanged. The value walk still executes, so this does not
repair denominator width/schedule failures or their phases. This conclusion is
from algebra/source review; the script does not claim separate emitted tests of
`with_payload_sign`.

### Exact Chunk-Carry Cleanup

The carry-in helper implements

```text
[z < a] OR (cin AND [z = a]).
```

It restores both operands, the incoming carry, and clean scratch. The builder
lowers `CZ(q,q)` to Z, so that alias in the comparator is intentional. The unused
`ctrl` parameter in the prefix helper has no effect when `targets=[]`. Reverse
boundary cleanup retains the preceding carry until its equality-dependent phase
correction is complete. The first boundary correctly uses a zero-carry strict
comparison. Scratch supplied by this caller is freshly clean, not arbitrary
dirty workspace despite the helper's borrowed-carries name.

This repairs interior boundary cleanup, not the independent post-fold overflow
predicate. Remaining fold, halving, representation, and final-overflow defects
are not removed by this exact comparator.

## Findings and Caveats

### Actual Output Must Preserve the Zero Predicate

The final payload-flag cleanup leaves

```text
[input word = 0] XOR [actual output word = 0]
```

before reset. It is clean when these actual predicates agree. Ideal field
invertibility is sufficient on a correctly implemented, appropriately encoded
input/output path, but does not by itself establish the invariant for approximate
arithmetic. A nonzero residual flag would be reset with a measurement-dependent
phase in the evaluator. This review found no new concrete bad-flag witness.

The user is qualifying this rationale in the manuscript. Word p is not detected
as zero by this helper; the encoding/range contract must remain explicit.

### Coefficient Release Is Also Conditional

The source's unconditional "proved-zero register" comment overstates the global
status of the approximate implementation. That is not a claim of a newly found
dirty coefficient in the zero fixture: the retained pre-reset reports explicitly
show clean coefficients in both division and multiplication, with zero phase
before and after release. The general caveat applies outside those tested paths.

The next useful instrumentation is a pre-reset check of the payload flag as well
as the coefficient, on failing structured inputs and zero/nonzero paired inputs.
Any future diagnostic changes should be made in a separate copy, not in the
currently frozen source.

### Round and Width Failures Are Not Isolated by the Full-Call Witnesses

The independent exact-integer rerun gives:

| Denominator | Convergence transitions | First tapered sum-width failure, zero-based |
|---|---:|---:|
| 1 | 512 | 177 |
| 3 | 1,135 | 171 |
| 2^255 | 1,239 | 80 |

Thus the latter two denominators violate widths before exhausting 768 rounds.
Their full-call failures cannot be attributed specifically to round exhaustion
without an ablation. A future full-width/tapered versus 768/longer-schedule matrix
would separate the mechanisms; a longer schedule sufficient for these three
witnesses would still not be an all-input bound.

## Manuscript Review

- Section 4's raw/complemented correction clarification resolves the earlier
  kappa ambiguity. The subtraction-frame coefficient is the negative of the
  raw-low-word quotient; the corrected paragraph also lists all parity inputs.
- Section 4's zero-mask discussion accurately describes the sign masking and
  targeted scope, subject to the actual-zero-predicate qualification above.
- Section 5 now assumes phase-correct arithmetic with input-independent branch
  scalars. That fixes the earlier insufficient basis-label hypothesis.
- The conditional trace-distance bound `min(1, 2 sum_i sqrt(q_i))` is sound under
  its stated branch/isometry assumptions and ideal-prefix bad weights. It does
  not turn random affine-input success rates into a coherent error guarantee.
- The targeted-results section separates witness repair from global correctness.
  At review time the fresh-study summary was only a comment placeholder, so no
  premature fresh-100k result was claimed or used in this review.

The retained stream-count receipt reports static T=1,524,503. Q=1,419 is the
reported integrated width. This follow-up did not independently rescan the
large operation stream or rerun the full circuit. Static T must remain distinct
from the eventual fresh-study mean executed T.

## Provenance and Source Anchors

Paths below are relative to the workspace root. Line numbers describe the source
as reviewed, not a proposed modification.

- `ecdsafail-qip-oral-repairs-20260922/src/point_add/pingpong_div.rs:19`: blocked zero helper.
- Same file, line 37: masked sign helper; lines 151-202: payload flag and cleanup.
- Same file, line 192: coefficient-release comment; lines 812-835: boundary cleanup.
- `ecdsafail-qip-oral-repairs-20260922/src/point_add/arith/compare.rs:275`: prefix forward/inverse gates.
- Same file, line 395: carry-in phase helper; line 421: zero-carry phase helper.
- `ecdsafail-qip-oral-repairs-20260922/src/point_add/mod.rs:637`: aliased CZ becomes Z.
- `ecdsafail-qip-oral-repairs-20260922/src/sim.rs:148`: measurement/reset phase semantics.
- `research/qip-oral-20260922/fresh-zero-mask-100k/freeze.json`: source identity.
- `research/qip-oral-20260922/repair-results/masked_chunk-w4/component.stdout`: retained PRERESET/POSTRESET/COMPONENT records.
- `research/qip-oral-20260922/repair-results/masked_chunk_coords-w16/stats.stdout`: retained static count.
- `outputs/ECDSAFAIL_QIP2027_oral_research_revision/sections/04-gate-efficient-circuits.tex:437`: zero-mask rationale.
- `outputs/ECDSAFAIL_QIP2027_oral_research_revision/sections/05-window-selected-addition.tex:82`: strengthened coherence assumption.
- `outputs/ECDSAFAIL_QIP2027_oral_research_revision/sections/13-followup-analysis.tex:20`: structured schedule claims.

The reviewed ping-pong source hash is
`456f7ba6ee90df7cfa65d154b448486548e842a02437838107cf56ad6bab89c9`.
The previous read-only pass matched all 51 frozen source files; the persisted
script repeats that check and records every hash in its new result receipt.
