# Suggested Replacement Wording

These are proposed passages only. The manuscript has not been edited.

## Fused Correction

Let B_0=2^n and F=B_0-p. For unsigned n-bit source and target words y,z, write the exact integer update as 2z+(-1)^sigma y=w+kappa_raw B_0, where 0<=w<B_0. Then kappa_raw is in {0,1,2} for addition and {-1,0,1} for subtraction, and the field result is congruent to w+kappa_raw F modulo p. This congruence alone does not specify canonical encoding or reversible carry cleanup.

The emitted cell performs subtraction in a complemented frame. Write 2z=z0+dB_0 and C_sigma(z0)+y=omega+oB_0, where C_0(v)=v and C_1(v)=B_0-1-v. It folds kappa_frame F into omega, with kappa_frame=o+(-1)^sigma d. For addition kappa_frame=kappa_raw; for subtraction kappa_frame=-kappa_raw. Under a no-escape condition, complementing back gives the intended field value. The retained doubling flag is recovered from corrected-target parity together with source parity, sign, and the addition carry. Correct phase erasure of the addition carry is a separate requirement.

The submitted 56-bit correction is conditional on no carry or borrow escaping that window and on valid carry-erasure predicates. Increasing the window does not by itself establish canonical outputs or exact phase cleanup. Even a full-word wrapped fold needs an additional correction when the corrected integer crosses a word boundary.

## Coherence Proposition Hypothesis

Assume the arithmetic implements the intended coherent map on the valid input subspace, restores each lookup payload before cleanup, and returns other workspace to zero. In particular, after its own measurement corrections, each arithmetic measurement branch must act as the intended isometry multiplied by a scalar independent of the valid input, including an input-independent phase. Assume also that every measured lookup payload and routing ancilla receives its exact phase correction using the required still-available controls. Then each complete corrected branch obeys K_m restricted to H_valid = gamma_m U_T restricted to H_valid, with sum_m |gamma_m|^2=1. Discarding the measurement record therefore gives the intended channel on H_valid.

Correct computational-basis output labels and clean final workspace alone do not establish this hypothesis. An input-dependent diagonal phase can satisfy both conditions while changing interference. The result is an interface-composition statement conditional on coherent arithmetic, not a proof of the approximate arithmetic implementation.

## Canonical Reference

The canonical replay primitives maintain canonical payloads, including zero, under their stated input contracts. Their composition implements division and multiplication conditional on phase-correct computation and uncomputation of the value transcript and terminal signed units. The full-call reference additionally replaces the three coordinate subtractions and passes the retained targeted tests and a separately frozen 4,096-input pilot. It still inherits a 736-round value schedule, finite signed widths, and other square and coordinate routines. These results neither establish all-input correctness of the complete point-addition implementation nor preserve the historical low-cost resource point.

## Round Budget

In 10 million independently sampled nonzero canonical denominators, the exact-integer walk had maximum observed length 743, with six walks exceeding 736 and none exceeding 768. The zero count at 768 gives a pointwise one-sided 95% upper bound of approximately 3.00e-7 for this sampled denominator distribution under the stated independence assumptions. We therefore treat 768 as a candidate engineering budget, not a sufficient all-input bound. This experiment does not certify the shrinking signed widths, modular replay, coherent channel, or a complete Shor computation.
