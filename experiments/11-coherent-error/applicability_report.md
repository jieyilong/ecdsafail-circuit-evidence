# Coherent Error and Shor-Prefix Applicability

Date: 2026-09-22. Scope: theory, executable checks, and applicability assessment only. No manuscript or circuit changes.

## Executive Conclusion

The standalone theorem is proved. For a measured circuit with **common corrected branch amplitudes on a certified good basis subset**, bad-subspace weight `epsilon` implies

\[
 d_{\rm tr}\leq d_{\rm pur}\leq
 b(\epsilon)=\sqrt{1-\max(0,1-2\epsilon)^2}.
\]

For `epsilon <= 1/2`, this is the sharp bound `2 sqrt(epsilon (1-epsilon))`. The corresponding norm distance between explicit output purifications is at most `2 sqrt(epsilon)`. For a sequence of calls, `min(1, sum_i b(epsilon_i))` bounds output trace and purified distance, with **every `epsilon_i` evaluated on the ideal pre-call state**. Correlations between calls are allowed.

These are useful conditional results, not a full-Shor certificate for the current artifacts. The missing premises are an all-branch arithmetic proof on a defined good set, certified weights for its entire complement, and a frozen complete schedule. The sharp square-root behavior also rules out a generic conversion from a basis failure fraction to a same-size algorithmic error probability.

## Inputs and Sources

The canonical notation and Craig Gidney feedback memo were read first. The baseline files inspected were sections 02, 05, 07, and 12 of `outputs/ECDSAFAIL_QIP2027_eval_rewrite`. Section 4 is not in scope and was not edited. The single-call `WindowTable` constructor and the published canonical-reference README were also read. Input hashes are in `check_results.json`.

Primary sources and their precise roles:

| Source | Used For | What It Does Not Establish Here |
|---|---|---|
| [Kretschmann, Schlingemann, Werner](https://arxiv.org/html/quant-ph/0605009), Stinespring representation and information-disturbance | Environment-aware formulation | A good set or error rate for these circuits |
| [Fuchs and van de Graaf](https://arxiv.org/abs/quant-ph/9712042) | Trace distance and fidelity comparison | The measured circuit's premises |
| [Tomamichel, Colbeck, Renner](https://arxiv.org/html/0907.5238), Definition 4, Lemmas 5-8 | Purified distance, triangle inequality, contractivity, purification interpretation | Independence of arithmetic failures |
| [Bennett, Bernstein, Brassard, Vazirani](https://arxiv.org/abs/quant-ph/9701001) | Historical hybrid-method attribution | Novelty of the present elementary hybrid proof |
| [Gidney](https://arxiv.org/html/1905.07682), Section 2 | Corrected X-basis lookup uncomputation | Coherence of the arithmetic that consumes the payload |
| [Schrottenloher](https://arxiv.org/html/2606.02235v1), Section 2, equations 3-5 and Algorithm 1 | Window decomposition, generic arithmetic interface, identity row, call-count convention | An emitted ordered schedule for this workspace |
| [Babbush et al.](https://arxiv.org/html/2603.28846v2), Appendix A.3-A.4 | Direct initialization, omission of three calls, recycled controls, MBUC | A transferable statistical or coherent guarantee for the ECDSA.Fail artifacts |
| [Litinski](https://arxiv.org/html/2306.08585), Section 1 | Alternative known-point initialization and a circuit with exceptional-case handling | Permission to assume a uniformly distributed early accumulator |
| [SEC 2 v2](https://www.secg.org/sec2-v2.pdf), secp256k1 parameters | Field, group order, generator | Implementation correctness |
| [libsecp256k1 scalar implementation](https://raw.githubusercontent.com/bitcoin-core/secp256k1/master/src/scalar_impl.h), endomorphism constant and explanation | Scalar `zeta` associated with the cubic endomorphism | Any arithmetic or measurement claim about the benchmark |

The theorem and prefix-count derivations are supplied explicitly rather than attributed wholesale to these sources. Source-specific point names are translated to canonical `G`, `P=[k]G`, `R`, `A`, and `R'=R+A`. The endomorphism scalar is called `zeta`, not `lambda`, which remains the affine slope.

## 1. Correct Hypothesis

### Short Manuscript Result and Placement

Use `manuscript_short_result.tex` as a proposed replacement for the conditional-coherence proposition and its proof in section 05. It states the explicit corrected-branch premise, gives the state-dependent bound and ideal-prefix composition, and includes a short proof. Keep the full sharpness examples and prefix analysis in the supplementary note. No manuscript file has been changed here.

Immediately after the result, retain a short scope sentence: **This is a conditional good-subspace certificate, not a certificate of the complete point-addition circuit or of Shor's algorithm. Its hypotheses require a proved arithmetic good set and its weight on the ideal intermediate states.** Do not insert a numerical full-Shor error bound or an empirical per-call rate into the theorem.

Report the new repair separately from the published canonical reference, and retain the explicit counterexamples to 768-round sufficiency. The completed 100,000-input study is reconciled in the parent report and `fresh-zero-mask-100k/verified-results.json`.

Let `Pi` project onto the proposed good basis subset, including clean input workspace. Use an ideal isometry `U` defined on the full input space and an implementation channel `E`. The required condition is

\[
 K_\mu\Pi=\gamma_\mu U\Pi,
 \qquad \sum_\mu|\gamma_\mu|^2=1,
\]

where `mu` indexes complete corrected branches, refined to include any discarded quantum environment. Each `gamma_mu` is independent of the good basis input. Equivalently, a Stinespring isometry satisfies

\[
 V\Pi=(U\otimes|\gamma\rangle_E)\Pi.
\]

All environment information matters: measurement records, reset qubits, routing garbage, arithmetic garbage, and variable branch lengths. A physically retained register used later must instead be part of the modeled system. Hidden memory accessed by later calls cannot be silently discarded between channels.

Equality of computational-basis density outputs is weaker. Even identical measurement probabilities for every input are weaker, because input-dependent phases of branch amplitudes can remain. Correct clean coordinates do not certify relative phase. This condition is also necessary for exact channel equality on the whole good subspace, as proved in the note.

For a mathematical specification, complete group translations on all valid points, including the identity and exceptional additions, and extend the resulting permutation to unused encodings. This defines the ideal comparison without claiming a free physical implementation of exception handling. If the actual kernel is unproved there, those inputs belong to the conservative bad set. Physical dirty workspace must likewise remain visible or be included in the environment, never silently declared clean.

### Section 05 Assessment

The proposition at lines 71-109 identifies the right target equation, `K_m |psi> = gamma_m U_T |psi>`. However, the statement's arithmetic premise is expressed as correct coordinates, restored payloads, and clean workspace. Those facts alone do not prove the assertion at line 90 that the remaining amplitude is input-independent.

There are two legitimate interpretations:

1. If “required phase correction” includes a proved exact correction for every arithmetic measurement, every routing measurement, every reset, and any remaining deterministic phase, then the desired condition is effectively an additional hypothesis. State it explicitly.
2. If it covers only the QROM/routing wrapper, the inference is incomplete. Correct arithmetic basis outputs still allow a hidden `Z` or measurement-induced dephasing.

The standalone theorem makes the premise explicit without editing the manuscript. It does not declare the wrapper proof false under a stronger coherent-arithmetic assumption.

### Why Exact QROM Cleanup Helps

For a restored `d`-bit payload `c_j`, the uncorrected branch factor is `2^(-d/2) (-1)^(m dot c_j)`. The correct diagonal feedback cancels this phase on every address, leaving a common scalar. This local argument is rigorous when the payload is actually restored and the controls retain the required values. It composes with an arithmetic block satisfying the same branch condition; it cannot repair an arithmetic phase defect that lies outside its correction function.

The executable 12-dimensional system example checks all four payload-measurement branches and all split-address phase selections. Corrected branches equal `U/2`. Omitting correction gives trace distance `0.75` on a uniform four-address input. This is an abstract coherent lookup/use/unlookup check, not an execution of the production gate stream.

## 2. Error and Composition

For any input entangled with a reference, split a purification into good and bad components. Both dilations share the good component. Isometry forces each bad component to be orthogonal to that shared component. Thus the two output purifications have overlap

\[
 1-\epsilon+c,\qquad |c|\leq\epsilon.
\]

This proves the sharp bound, including the constant and the saturation at `epsilon >= 1/2`. A phase flip on the bad subspace attains `2 sqrt(epsilon (1-epsilon))` below one half. Above one half, a rotation inside a two-dimensional bad subspace can make the outputs orthogonal. In particular, extending the nonmonotone expression `2 sqrt(epsilon (1-epsilon))` to all `epsilon` would be incorrect.

For composition, let `sigma_{i-1}` be the ideal pre-call state, including all controls and reference correlations. Define

\[
 \epsilon_i=\operatorname{tr}[(I-\Pi_i)\sigma_{i-1}].
\]

Insert ideal prefixes and implemented suffixes. Each local discrepancy is evaluated at `sigma_{i-1}`, and the suffix is contractive. This gives `sum_i b(epsilon_i)` without needing to estimate the erroneous implementation's later accumulator distribution. Exact Fourier and classical postprocessing can be included as common channels. Errors in initialization, Fourier gates, or other supposedly exact operations require separate terms.

The theorem concerns unconditional output distributions. Postselecting a rare Fourier transcript can amplify error and requires a separate conditional analysis. Likewise, a certificate for an ideal algorithm that computes the full probe does not automatically certify a shortened phase-estimation algorithm with three omitted windows. Choose the correct ideal algorithm and include its postprocessing success probability.

### No Numerical Full-Shor Bound

Only the symbolic ideal-prefix composition bound is proposed for the manuscript. No numerical aggregate Shor-error estimate is supplied. The `10^7`-denominator study in section 12 gives empirical information under its own denominator distribution. It neither proves an all-branch arithmetic good set nor establishes the ideal Shor-prefix measure of that set. `hat p^28`, `28(1-hat p)`, and an empirical round-tail frequency cannot replace this theorem's premises.

## 3. The Bad Set Is Not Two Points

Section 12's two structured inputs are witnesses for `A=G`. They show a supported-domain phase problem, not an exhaustive classification. For a fixed nonidentity secp256k1 addend `A`, the two zero-slope points are

\[
 R=\phi(A),\ \phi^2(A),\qquad \phi(x,y)=(\beta x,y).
\]

They occur because `y_R=y_A` gives `x_R^3=x_A^3`; the third solution is `R=A`, already excluded by the generic denominator condition. On secp256k1 the two other points are distinct and have nonzero input and output affine denominators. The code verifies this for the documented `A=G` witnesses and exhaustively on the small curve used for regression.

For a current row `A=[a]G`, a conservative geometry-plus-zero-slope set is

\[
 \{0,a,-a,-2a,\zeta a,\zeta^2a\}\subset\mathbb Z_r.
\]

These are scalar representatives of six accumulator points for each nonidentity row, not six points independent of the row. A real certified bad superset must also account for the following obligations:

| Component | Required Good-Set Obligation | Existing Limitation |
|---|---|---|
| Generic affine addition | Valid points and both invertible affine denominators | `R=O,A,-A,-2A` excluded for nonidentity `A` |
| Identity table row | All executed arithmetic cancels, with common corrected branch amplitudes | Disabling square/negation alone is not a proof, especially at `R=O` |
| Value recurrence | Both calls reach the correct endpoint within the frozen round budget | Finite-tail sampling is not a universal bound |
| Shrinking value registers | Exact integer trajectory fits every signed width | Width misses are a separate event |
| Replay arithmetic | Correct canonical words, carries, reductions, halving, and inverses | Section 12 contains noncanonical zero and nonzero-payload boundary failures |
| Measured carry cleanup | Exact predicate for the actual carry, including equality and correction history | Strict-prefix ties and postcorrection predicates can leave phases |
| Coordinate wrappers and square | Correct output, flags, and phase on all asserted good inputs | Replay-only repair did not fix final `y` subtraction |
| Whole call | Common branch amplitudes, clean live workspace, restored payloads | Passing finitely many lane assignments cannot prove all branches |

A good-set definition should be a conjunction of sufficient arithmetic and branch invariants. Its complement can then be bounded by a union bound over events **inside each ideal pre-call distribution**. Events need not be independent. Known failing examples only supply a subset of the bad set; their small measure supplies no upper bound on the full bad mass.

The published canonical reference removes identified replay and coordinate defects and passes its recorded targeted tests and fresh pilot. It still inherits the finite value schedule, the 736-round budget, the square, and remaining arithmetic. Its `Q=1804`, static `T=5,188,043` belong to that separate reference. This analysis does not transfer its conditional guarantees to the lower-cost operating points or to the new repair candidate.

### New Repair and Schedule Evidence, September 22

The current repair combines a zero-payload sign mask, exact chunk-carry cleanup, and canonical coordinate subtractions under the `guarded768` profile. The parent task reports passing full `w=4` and `w=16` calls on both zero-slope fixtures with 32 measurement lanes per point, and on the 64-case smoke set. The four retained `zero-slope.stdout` and `smoke.stdout` tables under `repair-results/masked_chunk_coords-w4/` and `masked_chunk_coords-w16/` are checked by this note's runner: 64 records per group, zero classical/phase/ancilla flags, and valid interfaces. These are targeted regressions, not 64 independent zero-slope point pairs and not an all-branch good-subspace proof.

The separate schedule audit establishes a stronger limitation than an unproved 768-round guarantee: the exact untruncated recurrence reaches its first signed-unit pair at round **1,135 for denominator `d=3`** and **1,239 for `d=2^255`**, including the specialized first transition. Thus 768 rounds is definitely not sufficient on all nonzero canonical denominators. For `d=1`, termination at round 512 still does not justify the margin-20 taper: its pre-halving sum first violates the signed width at zero-based round index 177, width 225. These records are in `schedule/structured_witnesses.json` and `schedule/REPORT.md`. They concern field denominators and exact integer preconditions, not measured frequencies or established reachable point-pair failures in Shor prefixes.

The frozen 100,000-input **single-candidate** study subsequently completed with zero detected output, phase, or ancilla failures. Its freeze, nine-stratum plan, and independently reconciled results are under `fresh-zero-mask-100k/`. This remains finite sampled evidence, not an all-input guarantee, proof of the branch condition, or a full-Shor error bound.

Suggested concise evidence wording: “The combined boundary repair passes the two supported zero-slope fixtures with 32 measurement assignments per point and the 64-case smoke set at both window widths. These targeted regressions do not establish coherent correctness on all inputs. Separately, exact recurrence witnesses requiring 1,135 and 1,239 rounds rule out universal sufficiency of the 768-round schedule.” Add the frozen-study results only after completion and audit.

## 4. Actual Ideal Prefix Support

### General Ordered Schedule

For unsigned disjoint windows, let `a_i=2^(s_i)` for a `G` window and `a_i=k 2^(s_i)` for a `P` window. With initial offset `C=[c]G`, the ideal pre-call accumulator is

\[
 R_i=\left[c+\sum_{\ell<i}a_\ell j_\ell\right]G,
 \qquad A_i=[a_i j_i]G.
\]

Independent Hadamard-prepared exponent bits give independent uniform digits, but **do not give a uniform accumulator**. The exact bad weight is the fraction of labeled prefixes whose `(j_i,R_i)` lies in the bad set, counting multiplicities. It is computable by the scalar-residue convolution in the theorem or by direct point accumulation. The formula's use of `k` is mathematical shorthand, not a requirement to know the discrete logarithm: sampling actual points uses only `G`, `P`, and the table schedule.

If exponent preparation is uniform on `[0,r)` rather than all `n`-bit strings, the top windows are correlated and the product-digit formula must be replaced by the actual preparation probabilities. Signed recodings, joint windows, offsets, and unequal-width final windows likewise require their own digit law and tables. A bit-position-shifted table `[j 2^s]G` is not an additively offset table `C_i+[j 2^s]G`.

### Low-To-High G Windows, No Additive Offset

The reproducible production-size calculation fixes `w=16`, `L=65536`, all `G` windows before the `P` windows, and direct initialization from `j_0`. Before the next call,

\[
 R=[j_0]G,\quad A=[Lj_1]G,
 \quad 0\leq j_0,j_1<L.
\]

`R` is uniform on only 65,536 points. Exhaustive current-address scanning gives exactly 65,535 pairs in the geometry-plus-zero-slope set, all of them `R=O, A!=O`. Their weight is `65535/2^32 = 1.5258556231856346e-5`. The unproved `(O,O)` pair contributes another `1/2^32` if conservatively excluded. No `2/r` or `6/r` estimate describes this prefix.

After `t` initialized/processed low `G` windows, for `1 <= t <= 15`, the prefix is exactly uniform on the scalar interval `[0,L^t)` because `L^t < r`. For every nonzero current address, the code checks membership of all six scalar targets in that interval. Results:

| Current Shift | Prefix Support | Counts in the Six-Point Set |
|---|---:|---|
| 16,32,...,224 | `2^shift` | 65,535 identity-accumulator pairs at each shift |
| 240 | `2^240` | 65,535 identity pairs, one `R=-A` pair, one pair for each of the two zero-slope branches |

The late zero-slope pairs confirm that these points need not be absent from real dyadic prefix support. These scans are exact integer membership checks on specified mathematical tables. They do **not** show that every such pair fails, or that all other pairs pass the emitted circuit.

These counts identify only the geometry/zero-slope subset and the separately unproved `(O,O)` case. They are not substituted into a numerical aggregate circuit-error estimate: additional arithmetic bad inputs remain unbounded.

### Once the Full G Scalar Has Been Accumulated

Let `N=2^256`, `d=N-r`. For `u` uniform in `[0,N)`, the exact number of representatives of a residue is two when `0 <= s < d`, and one otherwise. Here

\[
 d=432420386565659656852420866394968145599.
\]

The total-variation distance from the uniform group distribution is `d(r-d)/(Nr)`, approximately `3.73446e-39`. Thus “nearly uniform” can be derived for this stage, but it must not be assumed for earlier prefixes. The maximum atom is exactly `2/N`.

After a contiguous low prefix `v_<t` of the `P` scalar, the distribution is

\[
 \nu_t(s)=\frac{1}{NL^t}\sum_{v=0}^{L^t-1}
 \left(1+\mathbf1[(s-kv)\bmod r<d]\right).
\]

This is a mixture of translations of the actual dyadic distribution, so its maximum atom is at most `2/N`, for every fixed public key. Its distance to uniform is no larger than the preexisting bias. The six-point set therefore has weight at most `12/N`, about `1.03634e-76`, at a subsequent independent address. This is a bound on the six-point set only. It says nothing comparable about a potentially much larger carry/round/phase bad set. The `(O,O)` case needs an extra term or a proof.

### Ordering, Offsets, and Recycling

Reversing the window order produces sparse modular progressions rather than the initial low interval. Interleaving `G` and `P` windows makes early collisions depend on the public point. For example, after initializing `[j_0]G`, a next unshifted `P=G` table has `R=A` whenever `j_0=j_1!=0`, with weight `(L-1)/L^2`. There is no public-key-independent uniform-accumulator shortcut.

Known-point initialization is also not randomization. Litinski starts with a known point and handles exceptional additions. Shifting every prefix by a fixed offset can move particular hazards, but does not by itself make the accumulator uniform. A truly uniform independent random group offset would uniformize the *averaged* prefix distribution, subject to its preparation, compensation, and cost being specified. That would be a different algorithmic design, not a premise supplied by this workspace.

The fully coherent implementation retains orthogonal exponent labels, so duplicate accumulator points contribute probabilities with multiplicity rather than amplitudes that should be naively merged. For standard semiclassical recycling, the unconditional diagonal recursion survives: each fresh window has equal basis magnitudes, phase-only Fourier feedback does not change them, controlled translation shifts the accumulator, and averaging the subsequent window measurement produces the same diagonal mixture. A particular conditioned transcript can have nonuniform support and different probabilities. A rigorous bound with the transcript retained uses the ideal joint classical-quantum state or its correctly averaged local weights, not a claim that every conditional state is a uniform group eigenstate.

### What the 28-Call Count Leaves Unspecified

The primary sources support replacing the first addition by a lookup and omitting three late additions with different classical postprocessing. They do not provide a frozen ordered 28-call ECDSA.Fail program in the artifacts inspected here. The source `WindowTable::new` constructs the single-call table `[j]G`. The nine-table validation and the canonical-reference pilot are not such a schedule.

Accordingly, this report proves general prefix formulas and gives exact counts for a fully declared schedule. It does not label that schedule as an implemented attack. To apply the theorem to a specific 28-call construction, freeze window order, table contents, preparation, identity encoding, offsets, direct initialization, omitted windows, recycled-control logic, and postprocessing. Then recompute the ideal prefixes of that construction. For a schedule that does all 16 `G` windows first and omits three subsequent `P` windows, the early `G` counts above are unchanged, but the exact later `P` prefix law still depends on which windows remain and their order.

## 5. Executable Evidence

Run `run_checks.py` with NumPy. It writes only `check_results.json` next to itself. `prefix_support.py` can also run with the standard library alone. The runner records script hashes, input hashes, interpreter identity, and NumPy version.

Passed checks:

- Correct basis outputs with a deterministic `Z` nevertheless give trace distance one on `|+>`.
- Uniform `I/Z` branches, each with probability one half for every state, dephase `|+>` with trace distance one half and purified distance `1/sqrt(2)`.
- Ten small-matrix examples attain the sharp piecewise bound, including its upper-half saturation.
- 150 seeded random Stinespring pairs with a three-dimensional entangled reference satisfy the purified, trace-distance, and vector-norm bounds.
- All four corrected payload-measurement branches implement the common `U/2` Kraus factor in the small lookup example.
- A five-call noncommuting rotation/reflection example verifies adjacent hybrids and records different ideal and implemented bad-weight sequences. Final trace distance is approximately `0.119712`, below the ideal-prefix certificate `0.596408`.
- The secp256k1 endomorphism relation and the two `A=G` geometric witnesses are verified by exact elliptic-curve arithmetic.
- All 39,402 ordered pairs with nonidentity addend on `y^2=x^3+7` over `F_211` agree between coordinate geometry and the scalar six-point description. This small curve has prime order 199.
- Three small-curve schedules compare convolution multiplicities with independent exhaustive labeled-prefix enumeration.
- All nonzero current addresses are scanned for each of the 15 post-initialization `G` windows on secp256k1.

Matrix calculations are floating-point regression checks, not the proof. Prefix and curve checks use exact integers. None of these scripts executes a production arithmetic circuit, reconstructs every measurement branch of its gate stream, or runs the complete Shor Fourier/postprocessing pipeline.

## 6. What Is Needed for a Nonvacuous Certificate

1. **Freeze the artifact and ideal algorithm.** Include the complete schedule and distinguish every kernel version and its costs. Complete the ideal map on exceptional/unused encodings without asserting free physical support.
2. **Prove a checkable good predicate.** It must imply coordinate, representation, workspace, and common-branch correctness. Local exact arithmetic proofs can establish it compositionally. A finite set of successful measurement lanes is insufficient.
3. **Bound its ideal-prefix complement.** Use exact counting, analytical bounds, or confidence intervals from independently sampled ideal prefixes evaluated by that proved predicate. Sampling unknown outcome flags is not a replacement for the predicate proof. Table strata must not be pooled as if they were the algorithm's distribution.
4. **Assemble the hybrid budget.** Use certified upper bounds for all calls, include any additional preparation/Fourier errors, and translate final trace distance into a success-probability difference from the correct ideal algorithm.

The main publishable improvement here is a precise conditional statement that closes the logical gap between single-call arithmetic evidence and algorithmic use, and an explicit identification of what the current evidence still lacks. The underlying quantum-information inequalities are standard, so the oral-strength contribution would be the circuit-specific predicate proof and nonvacuous schedule-specific certificate, not novelty of the elementary hybrid argument alone.
