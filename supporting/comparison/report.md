# External Resource Accounting Audit

Audit date: 2026-09-08. Target: `outputs/ECDSA_Fail_QIP2027_github_linked/sections/06a-resource-evaluation.tex`, external table, lines 55-78. Canonical notation and the Craig Gidney feedback memo were read. This is a source and accounting audit, not a circuit replication or literature survey. All new files are confined to this comparison directory. The paper, circuits, parameters, and frozen corpora are unchanged.

## Review Findings

| Priority | Location | Finding | Proposed change |
|---|---|---|---|
| High | Lines 63-66, 74 | The Google rows exclude the window allowance while the Schrottenloher rows include it. A shared W label hides different resource boundaries. | Separate published arithmetic resources from measured window kernels. Give the same optional window-model transformation for both external papers. |
| High | Lines 61, 65-66 | The canonical symbol T means average executed work. Schrottenloher's reported construction counts are not documented as means over the cited tests. | Use a neutral Work heading and identify the count convention per source. Do not assert that these are either runtime means or verified static instruction totals. |
| High | Lines 65-66 | The reported epsilon statement has no stated confidence level. A clean 10,000-case test is not by itself a 95% bound of 2^-13.3. Its simulator also substitutes classical functions for exact arithmetic blocks. | Lead with the reported test and simulation level, retain epsilon only as an attributed claim, and prohibit confidence-level normalization. |
| Medium | Lines 67-68 | The cited TrailMix values are approximate author reports, not exact decimals or independently reproduced ledger totals. | Add approximately signs and label the clean FS result as author-reported. Keep these rows mixed-interface only. |
| Medium | Lines 74, 78 | A generic nonuniform-accounting caveat does not say which costs are absent. The explicit threshold warning is correct and should remain. | Name lookup, unlookup, CCZ/AND, mean/static, and depth boundaries. Never turn a threshold difference into an improvement over Google's hidden actual circuit. |
| Low | Line 32 and bounded-study sampler description | The lack of exact uniform subgroup sampling is real, but unquantified wording can suggest a material statistical defect. | State the exact prefilter TV distance, preserve the existing corpus, and retain the stronger limitations about conditioning, selection, and coherent composition. |

No challenge-row numeric transcription error was found. The important changes concern accounting boundaries and evidence labels.

## Primary Source Ledger

Page numbers below are printed pages and also one-based PDF pages for the two arXiv papers. Local PDFs and extracts were reused. Public arXiv pages and full texts were checked on the audit date. Source hashes are in `audit_checks.json`. No external circuits or ZK proofs were executed and no authors were contacted.

### G: Google / Babbush et al., v2

[Version record](https://arxiv.org/abs/2603.28846v2), [Appendix A, pp. 54-57](https://arxiv.org/pdf/2603.28846v2#page=54).

- A.1-A.2, pp. 54-55: arithmetic caps (Q, work) are (1175, 2,700,000) and (1425, 2,100,000), with 9,024 circuit-dependent FS successes, attested through ZK.
- A.3, pp. 55-56: work is mean executed CCX+CCZ, not static count. Equations A1-A3 add w qubits and 3*2^w lookup work, use w=16 and 28 additions. Unlookup and Fourier costs are separately described as small.
- A.5-A.6, pp. 56-57: support and measurement randomness derive from the circuit-seeded XOF. The attestation is not an independent error-rate estimate.
- II.B, pp. 7-10 (HTML II.2), and A.3: full-attack estimates exist, but the disclosed verification target is point addition, not an independently inspected end-to-end schedule.

Use v2, not the superseded v1 attestation: the version record identifies a soundness-bug repair. No exact hidden cost or comparable per-kernel depth is disclosed by these resource statements.

### S: Schrottenloher, v1

[Version record](https://arxiv.org/abs/2606.02235v1), [Table 1 / Eq. 1, p. 3](https://arxiv.org/pdf/2606.02235v1#page=3), [Table 2, p. 4](https://arxiv.org/pdf/2606.02235v1#page=4).

- Table 1: arithmetic Q=1192/1446 and work approximately 2^21.19/2^20.83. Counts group CCX, CCZ, and AND. Window allowance is excluded.
- Section 2, pp. 7-8, Algorithm 1: w=16, three lookups and three unlookups. Each lookup costs about 2^w. Measurement unlookup is treated as nearly free. Table 2 supplies a full-Shor resource model, not complete execution evidence.
- Table 1 and Section 3.1, p. 10: 10,000 successful random tests and reported epsilon<=2^-13.3. Parameters are informed by experiments, with no independently frozen test provenance specified.
- Implementation, pp. 5-6: exact arithmetic blocks are replaced by classical functions in simulation. Section 2, p. 6, groups Toffoli and AND despite different Clifford+T decompositions.

Runtime averaging and a common confidence level are unspecified. The paper supplies no matched depth measurement. Its linked [Qarton project](https://gitlab.inria.fr/capsule/qarton-projects/ec-point-addition) did not load in this audit, so no stronger source-code accounting claim is made.

### TM: Optional, Only the Two Already-Cited Points

[Author README, The circuits and Quick start](https://github.com/trailofbits/trailmix#the-circuits), [author circuit summaries, opening table and Section 0.3](https://github.com/trailofbits/trailmix/blob/main/kmx_circuit_summaries.md).

The existing Jump (1169, approximately 2.09M) and shrunken-PZ (1050, approximately 32.3M) values match the author summary. The addend is classical per shot. Work is mean executed CCX+CCZ. The authors report validation on 9,000 FS shots. Neither a coherent window lookup nor a full-Shor implementation is established by these two rows. The harness caps are different numbers and must not replace the approximate operating costs. This audit did not establish that the rounded work values were measured on precisely the same 9,000-shot support. The citation is a mutable branch, not a pinned run manifest. Keep the results explicitly author-reported or omit them for space.

### E: Current Frozen Challenge Evidence

[Pinned study](https://github.com/jieyilong/ecdsafail-circuit-evidence/tree/da2dfdeff554adb6773852c9cd7767f8a4f00ef6/experiments/02-fresh-windowed), [analysis](https://github.com/jieyilong/ecdsafail-circuit-evidence/blob/da2dfdeff554adb6773852c9cd7767f8a4f00ef6/experiments/02-fresh-windowed/analysis.json), [freeze manifest](https://github.com/jieyilong/ecdsafail-circuit-evidence/blob/da2dfdeff554adb6773852c9cd7767f8a4f00ef6/provenance/freeze.json). These public locators come from the manuscript and local release. Numeric checking here used the local release, not a fresh download of all remote ledgers.

| Frozen single-call kernel | Q | Mean executed T | Static CCX+CCZ | Any failures / 100,000 |
|---|---:|---:|---:|---:|
| Windowed Jump-2, split | 1162 | 1,523,121.58073 | 1,593,346 | 215 |
| Windowed ping-pong, split | 1338 | 1,127,527.39827 | 1,184,131 | 39 |
| Conservative ping-pong, split | 1392 | 1,252,854.89397 | 1,347,296 | 0 |

These means include failures and the implemented lookup/unlookup paths. The address register and live scratch are included in Q. Do not add another 16 qubits or 196,608 Toffolis to these measured kernels. The freeze manifest has `toffoli_depth: null` and `feed_forward_rounds: null` for each. Static HMR counts are not depth. The nine-table allocation has three identity-addend cases, all retained. Do not substitute the older shared-corpus results, which had two such cases and different failure counts.

## Accounting Reconciliation

### One Explicit Window Allowance

Let C_core denote an external paper's pre-window arithmetic count, without redefining canonical T. Applying the papers' leading-order model at w=16 gives

    Q_model = Q_core + 16
    C_model = C_core + 3*2^16 = C_core + 196608.

| External row | Published core (Q, work in M) | Same window-model transformation (Q, work in M) | Status |
|---|---|---|---|
| Google low-Q | <=1175, <=2.70 | <=1191, <=2.896608 | Derived model caps only |
| Google low-gate | <=1425, <=2.10 | <=1441, <=2.296608 | Derived model caps only |
| Schrottenloher low-Q | 1192, approximately 2^21.19/10^6 | 1208, approximately 2.59 | Derived from rounded source count |
| Schrottenloher low-gate | 1446, approximately 2^20.83/10^6 | 1462, approximately 2.06 | Derived from rounded source count |

The inequalities in the model column apply to the displayed model terms, not a certified all-in window circuit. Neither 196,608 nor the transformed totals are a demonstrated exact lookup-plus-unlookup bill. Additional small costs are not quantified there. The current Schrottenloher numbers are supported as these approximations, not as measured complete-kernel means. Google's original thresholds are supported, but not under an all-in W interpretation. Source S's rounded re-expression of Google must not supersede Google's primary caps.

The supplied `draftcomparison.tex` takes the conservative presentation route: show original external core numbers in their own block, measured W kernels separately, and give this optional transformation in the notes. This avoids false precision and a claim of fully matched accounting.

### Count and Scope Boundaries

CCX and CCZ differ by Hadamards on the target, so unit weighting is a declared logical convention, not a physical-runtime equivalence. Temporary AND construction/erasure has another resource convention. A Clifford+T or magic-state conversion needs specified decompositions and feed-forward assumptions. Do not read T here as a count of single-qubit T gates.

A static instruction count counts emitted CCX/CCZ entries. An executed mean counts only firing classical conditions across the stated inputs and measurement outcomes. A quantum control evaluating to zero is not, by itself, permission to omit a physically executed gate. Shared gate names do not equalize these counting bases.

The 28-addition model uses 32 conceptual windows, direct initialization instead of the first addition, and classical postprocessing instead of three terminal additions. It is not 28 independent classical retry opportunities. Single-call errors, local coherence checks, and four-call pilots do not validate correlated accumulator distributions, all shifted tables, Fourier processing, or complete ECDLP success. The source-backed external models may be contextualized, but no measured full-Shor speedup or physical spacetime dominance follows. Q*T omits depth, feed-forward latency, routing, large Clifford costs, and error correction.

### Error Evidence Is Not Exchangeable

Keep three separate labels: circuit-selected FS acceptance, author-reported random-input testing with uncertain selection/simulation provenance, and the frozen fresh stratified challenge study. None licenses assigning the external circuits an empirical success probability from the challenge corpus. In particular, selected 0/9024 and fresh 0/100000 neither establish comparable error nor rank the circuits' actual error rates.

For orientation only, an independently fixed circuit with zero failures in 10,000 independent equal-distribution tests has one-sided 95% upper bound 1-0.05^(1/10000), approximately 2.9953e-4, not 2^-13.3 (approximately 9.9152e-5). This does not assign a confidence interval to S's experiment. For the fresh all-zero challenge row, the allocation-weighted one-sided bound is approximately 2.99569e-5 under the study's independent-trial model, including its fixed nine strata. It is per circuit, not simultaneous over three circuits, not over all public points/windows, and not a coherent-error bound. Preserve the separate zero-payload diagnostic and its adverse outcomes.

## Exact Scalar-Sampling Audit

### Before Filtering

The [SEC 2 parameters, Section 2.4.1, printed p. 9 / PDF p. 13](https://www.secg.org/sec2-v2.pdf#page=13) specify subgroup order n, denoted r here:

    r = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
    N = 2^256
    d = N-r = 432420386565659656852420866394968145599.

Model the 32 XOF bytes as a uniform integer X in [0,N). Since N=r+d with 0<d<r, a=X mod r has probability 2/N for 0<=a<d and 1/N for d<=a<r. Thus the exact total variation distance from uniform Z_r is

    delta = (1/2) sum_a |Pr[a]-1/r|
          = d*(r-d)/(N*r)
          = (2^256-r)*(2*r-2^256)/(2^256*r)
          = 3.73445534504013415275958254801764716...e-39.

The wrap probability d/N is very close but is NOT the exact TV distance. Use r, not the coordinate-field modulus p. Scalar multiplication a -> [a]G is a bijection onto the subgroup, so the same prefilter TV applies to R. An independent uniform 16-bit address does not change it. For any fixed failure indicator, including averaging over identical measurement randomness, the prefilter failure-probability difference is at most delta. For 100,000 independent draws the product-law TV is at most 100000*delta, approximately 3.73446e-34. This is not a failure-count estimate for the circuit.

### Conditioning and the Frozen Corpus

The actual [driver, generate_window_cases, lines 557-626](https://github.com/jieyilong/ecdsafail-circuit-evidence/blob/da2dfdeff554adb6773852c9cd7767f8a4f00ef6/sources/trees/conservative-pingpong/src/bin/eval_bounded.rs#L557) consumes 32 bytes for R=[a]G, rejects R=O, samples j by a power-of-two mask, and rejects nonzero-address cases with R=+/-A. These are input-domain conditions, not discards selected using circuit outcomes. R=-2A is not separately filtered. Its absence in the corpus does not remove the arithmetic precondition.

Rejecting only R=O gives exact TV from uniform nonzero subgroup scalars

    delta_nonzero = (d-1)*(r-d)/((N-2)*(r-1)).

For the single-call joint distribution, let C be the implemented acceptance event and W=65536. For each fixed nonzero table base [beta]G, A=[j*beta]G. Under the uniform scalar/address proposal,

    Pr_uniform[C^c] = (3-2/W)/r.

The biased proposal assigns at most 2/N to a scalar, so Pr_biased[C^c] <= 2*(3-2/W)/N < 6/N. An elementary conditioning bound therefore gives

    TV(P(.|C), U(.|C)) <= 2*delta/min(P(C),U(C))
                       <= 2*delta/(1-2*(3-2/W)/N)
                        < 7.469e-39.

This is a conservative bound, not the exact postfilter TV. It compares the same acceptance domain and fixed tables. It does not compare the accepted distribution to an unconditioned full-Shor state. The proposal address is uniform, but the accepted address need not be exactly uniform because j=0 has fewer exclusions. Fixed stratum weights preserve the bound, and the 100,000-trial bound remains below 7.469e-34. Pseudorandomness is the study's modeling assumption, not information-theoretic randomness of a frozen deterministic seed.

**Disposition of the proposed sampling-bias concern:** keep the factual nonuniformity disclosure, add its negligible magnitude, and do not regenerate or replace the historical corpus. Exact rejection sampling can be specified for a separately named future corpus. Rejected-case identities were not archived, so do not invent a rejection ledger or assert there were no rejected proposals. Preserve the distinction between earlier exploratory shared data and fresh post-freeze data. Conditioning, table coverage, outcome selection, and coherent composition remain substantive limits even though modulo bias is negligible.

## Feasible Revision Limits

1. Now: replace the table with the supplied blocks/notes, attribute the error claims, and pin Google v2 and Schrottenloher v1. No new experiments are needed for these corrections.
2. Now: retain mean and static challenge counts side by side in evidence, with explicit null depth/feed-forward fields. Do not turn static HMR counts into latency.
3. Later, separate artifact: evaluate nearby window widths with the actual lookup/unlookup implementation and peak-live allocation. Google's w=16 optimum does not establish that w=16 is optimal for the shorter kernels. Partial windows and initialization must be modeled explicitly.
4. Later, if pursued: a dependency-aware depth model must include measurement/classical-control dependencies and state its hardware abstraction. An arithmetic-only depth claim would be incomplete.
5. Beyond this audit: common-protocol external accuracy evaluation and full-Shor integration require additional accessible artifacts and validation. Their absence is a limit, not a reason to extrapolate from selected supports or published caps.

## Checks and Deliverables

- `conventions.json`: compact source conventions, original rows, derived allowances, unsupported-claim flags, and exact TV expression.
- `draftcomparison.tex`: replacement fragment only. It changes no manuscript files and reuses existing citation keys/macros.
- `check_accounting.py` / `audit_checks.json`: exact rational calculations, 247 exhaustive small-modulus checks of both TV formulas, original-source hashes, and read-only fresh-ledger extraction. No circuits are run.
- `source-google-55.png`, `source-google-56.png`, `source-schrottenloher-p3.png`: inspected local-PDF page renders resolving formulas and table boundaries. Web PDF screenshots were unavailable, so local Poppler rendering was used.
- `tex_check.tex`, `tex_check.log`, `tex_check.xdv`: offline fragment compilation against the manuscript's `llncs.cls` and fresh macros. The final log has no undefined commands/references or overfull/underfull boxes. This is a fragment syntax/box check, not a rebuilt or visually reviewed full manuscript PDF. The temporary isolated TeX cache was removed.

Final consistency checks passed: all 13 input hashes remain unchanged, both Google model transformations agree with the declared allowance, and the three fresh rows agree with the local means, any-channel unions, and static CCX+CCZ sums. Both JSON files parse successfully. The delivered text/code files use ASCII.

The source and arithmetic audit does not independently validate the external ZK proof, Qarton implementation, TrailMix circuits, or all raw challenge outcome ledgers.
