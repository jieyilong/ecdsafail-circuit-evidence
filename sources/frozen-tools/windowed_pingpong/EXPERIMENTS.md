# ECDSA.Fail Ping-Pong Validation Experiments

Status: Experiments 1 and 2 completed on 2026-09-07. The original specifications are retained below. Actual execution, departures from the prospective protocol, and limits of the evidence are documented in the results sections.

## Purpose

These experiments test whether the comparison-free ping-pong dialog-GCD construction retains its reported resource advantage under independent evaluation and whether it can support the coherent window-selected interface used in windowed implementations of Shor's ECDLP algorithm.

The experiments address two questions:

1. Does mixed-addition ping-pong retain its $Q\times T$ advantage over its predecessor at a comparable empirical failure rate on a common independent corpus?
2. What resource and correctness overhead results from adapting ping-pong to coherent window-selected point addition?

Neither experiment implements or validates a complete fault-tolerant attack.

## Notation

- $G$ is the standardized generator of the secp256k1 group.
- $R=(x_R,y_R)$ is the accumulator before one point addition.
- $A=(x_A,y_A)$ is the classical or QROM-selected addend.
- $R'=R+A$ is the intended output.
- $Q$ is peak logical qubit width.
- $T$ is average executed Toffoli count on the stated corpus.
- $S=Q\times T$ is the raw benchmark score.
- $\hat p=1-F/N$ is the empirical probability of passing all recorded checks, where $F$ is the number of any-channel failures among $N$ inputs.
- $Q\times T/\hat p$ is a per-call sensitivity proxy under an independently rerunnable classical-success model. It is not the expected cost of a coherent Shor computation.

## Shared Rules

### Artifact Freeze

Before generating the final held-out corpus, record:

- Full source commit for every circuit.
- Evaluator, simulator, compiler, and dependency revisions.
- Build configuration and environment variables.
- Circuit and serialized-operation-stream hashes.
- Corpus-generator source and revision.
- Input and measurement-randomness policies.
- Static resource counts by gate class.

No circuit, parameter, nonce, or truncation width may change after final outcomes are viewed. A changed circuit requires a new held-out corpus and experiment identifier.

### Data Separation

Maintain three disjoint data roles:

1. **Development data:** implementation and debugging.
2. **Pilot data:** evaluator checks and runtime estimation before the freeze.
3. **Final held-out data:** generated after the freeze and used for the reported statistical comparison.

Do not search circuit-dependent nonces or discard unfavorable final outcomes. Preserve the complete input and result ledgers.

### Correctness Channels

Record for every input:

- **cls:** incorrect classical output.
- **pha:** unwanted relative phase or phase-cleanup failure.
- **anc:** nonzero or unreleased ancilla state.
- **any:** union of the preceding channels.

The categories may overlap. Report their separate counts and their union. Do not add the channel counts to obtain the number of failed inputs.

### Resource Metrics

Report:

- Peak logical width $Q$.
- Mean executed Toffoli count $T$.
- Static Toffoli count.
- Raw product $Q\times T$.
- Total static operation count.
- Clifford count.
- Measurement count and feed-forward rounds.
- Toffoli depth or another defined parallelism-sensitive metric, if available.
- $Q\times T/\hat p$, labeled only as a per-call retry-sensitivity proxy.

## Experiment 1: Independent Mixed-Addition Evaluation

### Objective

Evaluate ping-pong and its relevant predecessors on the same independent corpus. Determine whether the ping-pong resource improvement persists at comparable empirical accuracy and diagnose the causes of any failures.

### Circuits

| Role | Identifier | Frozen revision |
|---|---|---|
| Historical Jump-2 circuit | 8e9c9a2 | 60d61859fa6965eba53634f91877b1141a6f9dce |
| Exact source parent of ping-pong | Parent of 3616dbf | 31f9c58ce9c5a12df8d18245f3905cc3352cb6a9 |
| Ping-pong circuit | 3616dbf | 897dda2b0cf267151ecd973252d2a5078cbf1b63 |

Retain both the historical Jump-2 circuit and the exact ping-pong parent if they differ. The exact parent supports attribution of the bundled source change. The historical circuit connects the experiment to the paper's earlier operating point.

### Corpus

Prefer reproducing the existing Jump-2 corpus with seed **ecdsafail-windowed-independent-random-100k-v1**, but only if the pinned generator and complete input ledger reproduce it exactly. Otherwise, define a new corpus and rerun every circuit. Do not combine old aggregate counts with new per-input results as though they were paired.

Generate $N=100{,}000$ cases:

1. Sample nonzero $a\in\mathbb Z_r$ and set $R=[a]G$.
2. Sample $j\in\{0,\ldots,2^{16}-1\}$ uniformly.
3. Set $A=[j]G$ and provide its coordinates classically to each mixed circuit.
4. Mark $j=0$, where $A=\mathcal O$, as an identity-row case.
5. Mark inputs outside the common declared domain, including any encountered $R\in\{A,-A,-2A\}$.

Use the common supported nonidentity domain for the primary comparison. Report identity and other exceptional cases separately. Preserve exclusion counts and do not silently resample cases after evaluation.

### Reference Diagnostics

For each denominator used in point addition, run an untruncated classical reference implementation of the ping-pong recurrence. Record:

- Exact rounds required to reach the signed-unit endpoint.
- Whether convergence occurs within 704 rounds.
- Signed bit length of both Euclidean operands at every round.
- First violation of the submitted active-width schedule.
- Carry, fold, comparison, or endpoint-recovery conditions exceeding a calibrated window.
- First stage and operation family diverging from exact arithmetic.

Classify failures by fixed-round nonconvergence, width truncation, modular correction, endpoint recovery, phase cleanup, or another identified cause.

### Statistical Analysis

For each circuit:

1. Compute $\hat p=1-F/N$ using any-channel failures.
2. Report a two-sided 95% Wilson interval for the failure rate.
3. Report raw $Q\times T$ and the secondary $Q\times T/\hat p$ proxy.

For each paired comparison:

1. Report both pass, both fail, baseline-only fail, and candidate-only fail.
2. Apply an exact paired sign test or exact McNemar test to discordant outcomes.
3. Report a confidence interval for the paired failure-rate difference.
4. Predeclare a noninferiority margin $\Delta_{\mathrm{NI}}$ based on the intended error budget. Experiment 1 used $\Delta_{\mathrm{NI}}=0.0005$, or 0.05 percentage points.

### Success Criterion

Experiment 1 supports the principal empirical claim if:

1. Ping-pong retains a lower $Q\times T$ than its exact parent on the common corpus.
2. The upper confidence bound for the ping-pong-minus-parent failure-rate difference is at most $\Delta_{\mathrm{NI}}$.
3. Failure mechanisms, exclusions, and all final outcomes are reported without nonce or support selection.

If this criterion is not met, report the result and revise the claim. Do not search for a more favorable corpus.

## Experiment 2: Coherent Window-Selected Ping-Pong

### Objective

Adapt ping-pong to the single-call map

$$
U_{\mathcal T}\lvert j\rangle_J\lvert R\rangle_{XY}\lvert0\rangle_W
\longmapsto
\lvert j\rangle_J\lvert R+\mathcal T[j]\rangle_{XY}\lvert0\rangle_W
$$

on its declared domain. Measure coherent-selection overhead and test whether the adaptation produces a detectable basis-state accuracy regression.

### Circuits

| Role | Identifier | Frozen revision |
|---|---|---|
| Mixed Jump-2 | 8e9c9a2 | 60d61859fa6965eba53634f91877b1141a6f9dce |
| Two-column windowed Jump-2, version 2 | Windowed 8e9c9a2 | 15a29ac9b1e97fc21eb81b9a6f0f6d9c4dc7a92e |
| Mixed ping-pong | 3616dbf | 897dda2b0cf267151ecd973252d2a5078cbf1b63 |
| Windowed ping-pong | Two-column runtime-table adapter | a1373a0582c9554d66633b13c76300d0ecdf81c4 |

Use the two-column windowed Jump-2 construction for comparisons involving the previously reported 191/100,000 result. A later three-column implementation must be treated as a distinct circuit.

### Interface Requirements

The new circuit must:

- Use a $w=16$ quantum address register $J$.
- Accept a topology-independent classical table with two coordinate columns.
- Preserve $J$.
- Handle $j=0$ coherently as the identity addend.
- Load selected coordinates only when needed and uncompute them after use.
- Return QROM, arithmetic, and routing workspace to zero.
- Apply every measurement-dependent phase correction.
- Leave no measurement record whose distribution depends on $j$ or $R$.

### Basis-State Evaluation

Evaluate all four circuits on one pinned corpus using the same $R=[a]G$, address $j$, and table entry $A=\mathcal T[j]=[j]G$ wherever their interfaces share a domain.

Report:

1. **Common-domain analysis:** nonzero addresses satisfying every compared circuit's generic-affine conditions.
2. **Identity-row analysis:** all $j=0$ cases, used to test the coherent bypass without penalizing mixed circuits that do not support $A=\mathcal O$.

In addition to 100,000 random cases, exercise every $j\in\{0,\ldots,2^{16}-1\}$ at least once at the routing and lookup layer. Check address preservation and workspace cleanup for the entire table.

### Coherence Evidence

Basis-state tests are not sufficient. Provide:

#### Implementation-Level Argument

Show for the actual lookup network that:

1. Payload coordinates are restored before reverse lookup.
2. Address and routing controls retain the values required for cleanup.
3. Every measured temporary AND contributes only an input-independent branch amplitude after conditional phase correction.
4. Routing measurement records reveal no information about $j$ or $R$.
5. The arithmetic backend preserves coherent control on the supported subspace.

#### Reduced Coherent Tests

At smaller window widths, compare the implemented operation with a reference using:

- Uniform and nonuniform address superpositions.
- Superpositions spanning zero and nonzero addresses.
- Complex relative amplitudes.
- Address and workspace checks.
- Corrected measurement branches or the resulting channel.

Compare the final state or channel up to global phase. A forward-then-inverse test alone is insufficient because matching errors may cancel.

### Required Comparisons

Report:

1. Windowed ping-pong versus mixed ping-pong, measuring interface overhead.
2. Windowed ping-pong versus windowed Jump-2, comparing backends under one interface.
3. Windowed and mixed versions of each backend, testing whether observed failure changes are attributable to coherent selection.

Use the statistical analysis and predeclared noninferiority margin from Experiment 1 where applicable.

### Success Criterion

Experiment 2 supports a window-compatibility claim if:

1. The circuit realizes the stated interface under an implementation-specific coherence argument.
2. Every tested address preserves $J$ and clears lookup and routing workspace.
3. Windowed ping-pong retains a resource advantage of interest over windowed Jump-2.
4. The upper confidence bound for the windowed-minus-mixed ping-pong failure-rate difference is at most $\Delta_{\mathrm{NI}}$.

The conclusion remains limited to one point-addition call. Do not describe the result as a complete implementation or validation of Shor's algorithm.

## Result Table

| Circuit | Interface | $Q$ | Mean $T$ | Static Toffoli | Total operations | $Q\times T$ | cls | pha | anc | any | 95% error interval | $Q\times T/\hat p$ |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Jump-2 8e9c9a2 | Mixed | 1,151 | 1,299,440.793 | 1,358,316 | 9,133,449 | 1.495656B | 154 | 115 | 0 | 192 | [0.1667%, 0.2211%] | 1.498534B |
| Ping-pong parent | Mixed | 1,150 | 1,284,770.688 | 1,340,596 | 9,018,685 | 1.477486B | 216 | 169 | 0 | 267 | [0.2369%, 0.3010%] | 1.481442B |
| Ping-pong 3616dbf | Mixed | 1,321 | 952,719.423 | 1,009,077 | 13,586,833 | 1.258542B | 35 | 17 | 0 | 42 | [0.0311%, 0.0568%] | 1.259071B |
| Jump-2 version 2 | Window-selected | 1,162 | 1,684,160.924 | 1,754,382 | 213,387,745 | 1.956995B | 151 | 117 | 0 | 191 | [0.1658%, 0.2200%] | 1.960740B |
| Ping-pong | Window-selected | 1,338 | 1,288,559.922 | 1,345,161 | 217,603,629 | 1.724093B | 33 | 14 | 0 | 36 | [0.0260%, 0.0498%] | 1.724714B |

All table means and products include all 100,000 cases, including the two identity rows. Common-domain failure comparisons exclude those two rows, which the mixed circuits do not support. B denotes $10^9$.

## Required Artifacts

Release:

- Exact source trees or immutable repository links.
- Build and evaluator manifests.
- Corpus generator and immutable corpus.
- Per-input expected and observed outputs.
- Per-input cls, pha, anc, and any indicators.
- Per-input executed Toffoli counts.
- GCD convergence and width-diagnostic ledgers.
- Static resource reports.
- Statistical-analysis source and generated tables.
- Coherence argument and reduced coherent-test artifacts.
- SHA-256 manifest covering every artifact.

## Execution Order

1. Freeze and reproduce the three mixed circuits.
2. Implement the shared-corpus harness and diagnostics.
3. Run pilot cases and repair instrumentation only.
4. Freeze Experiment 1 and generate its final corpus.
5. Run Experiment 1 and publish every outcome.
6. Adapt ping-pong to the two-column window-selected interface.
7. Complete address coverage and reduced coherent tests.
8. Freeze Experiment 2 and generate its final corpus.
9. Run Experiment 2 and publish every outcome.
10. Regenerate manuscript tables and claims directly from the released ledgers.

## Paper Integration

- Section 4.3: add ping-pong convergence and failure-mechanism findings.
- Section 6: describe windowed ping-pong and its implementation-specific coherence argument.
- Section 7.2: add common-corpus resource comparisons.
- Section 7.3: report paired outcomes, uncertainty, and the limited interpretation of $Q\times T/\hat p$.
- Limitations: preserve the distinction between basis-state evidence, coherent correctness, and complete-Shor validation.

## Experiment 1 Results

Experiment 1 was conducted on 2026-09-07 using submission 3616dbf2-f32d-41c8-9ea2-7a5bbe372fc0 as the ping-pong circuit. The point-addition sources were frozen at the revisions listed above. Each worktree used the same trusted shared-corpus evaluator, simulator, and table generator taken from evaluator revision 15a29ac9b1e97fc21eb81b9a6f0f6d9c4dc7a92e. No file under src/point_add was modified.

### Corpus and Scope

- Seed: **ecdsafail-windowed-independent-random-100k-v1**.
- Evaluated cases: 100,000.
- Addend distribution: $A=[j]G$ for uniform 16-bit $j$, supplied classically.
- Accumulator distribution: nonidentity $R=[a]G$.
- Equal-x exceptional inputs $R=\pm A$ were rejected during corpus generation.
- No nonidentity case satisfying $x_{R'}=x_A$, which would include the remaining $R=-2A$ exception, occurred in the generated corpus.
- Two identity rows with $j=0$ were retained.
- The point-addition circuits were evaluated on identical inputs and expected outputs.
- A 128-case pilot from this pre-existing corpus was inspected before the full run. No circuit or parameter was changed afterward. The experiment is therefore a common-corpus exploratory evaluation, not a newly blinded confirmatory test.

### Aggregate Results

| Circuit | $Q$ | Mean $T$ | Static Toffoli | Mean Clifford | $Q\times T$ | Any failures | Failure rate, 95% Wilson CI | $Q\times T/\hat p$ |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Jump-2 8e9c9a2 | 1,151 | 1,299,440.793 | 1,358,316 | 5,346,775.588 | 1.495656B | 192 | 0.192%, [0.1667%, 0.2211%] | 1.498534B |
| Ping-pong parent | 1,150 | 1,284,770.688 | 1,340,596 | 5,304,943.171 | 1.477486B | 267 | 0.267%, [0.2369%, 0.3010%] | 1.481442B |
| Ping-pong 3616dbf2 | 1,321 | 952,719.423 | 1,009,077 | 11,110,772.133 | 1.258542B | 42 | 0.042%, [0.0311%, 0.0568%] | 1.259071B |

The ping-pong circuit had 35 classical-output failures and 17 phase failures, with 10 inputs failing both channels. It had no ancilla failures. The source parent had 216 classical failures, 169 phase failures, and 267 failures in their union. Jump-2 had 154 classical failures, 115 phase failures, and 192 failures in their union.

All three circuits failed the two identity rows, as expected for mixed-addition circuits that do not support $A=\mathcal O$. Excluding those rows leaves 190 Jump-2 failures, 265 parent failures, and 40 ping-pong failures among 99,998 common-domain cases. Their respective nonidentity failure rates are approximately 0.1900%, 0.2650%, and 0.0400%.

### Resource Comparisons

Relative to its exact source parent, ping-pong:

- Uses 14.87% more logical qubits.
- Reduces mean executed $T$ by 25.85%.
- Reduces static Toffoli count by 24.73%.
- Reduces raw $Q\times T$ by 14.82%.
- Reduces $Q\times T/\hat p$ by 15.01%.
- Increases total static operations by 50.65%.
- Increases mean Clifford operations by 109.44%.

Relative to Jump-2, ping-pong reduces mean executed $T$ by 26.68%, raw $Q\times T$ by 15.85%, and $Q\times T/\hat p$ by 15.98%.

### Paired Outcomes

| Comparison | Both fail | Baseline only fails | Ping-pong only fails | Neither fails | Ping-pong minus baseline failure rate | Approximate 95% paired interval | Exact two-sided sign-test p-value |
|---|---:|---:|---:|---:|---:|---:|---:|
| Parent versus ping-pong | 3 | 264 | 39 | 99,694 | -0.225 percentage points | [-0.2591, -0.1909] percentage points | $3.27\times10^{-42}$ |
| Jump-2 versus ping-pong | 2 | 190 | 40 | 99,768 | -0.150 percentage points | [-0.1797, -0.1203] percentage points | $1.44\times10^{-24}$ |

The ping-pong-minus-parent interval lies entirely below the predeclared noninferiority margin of +0.05 percentage points. Under this exploratory analysis, ping-pong is not merely noninferior: it has a substantially lower observed failure rate on the common corpus.

### Exact-Recurrence Diagnostics

For each nonidentity input, an untruncated classical implementation evaluated the two intended ping-pong denominator walks:

- 33 of 99,998 inputs had at least one denominator requiring more than 704 rounds.
- Eight of those 33 inputs also violated the submitted shrinking-width schedule.
- The largest observed exact convergence counts were 725 rounds for division and 723 rounds for multiplication.
- Of the 33 inputs flagged by the recurrence or width diagnostics, 32 failed at least one circuit check.
- The 32 diagnosed failures account for 80% of the 40 observed nonidentity ping-pong failures.
- One diagnostically flagged input passed the recorded circuit checks.
- Eight observed nonidentity failures were not explained by these convergence and width diagnostics.

These diagnostics use intended denominators reconstructed from the reference point-addition inputs and outputs. They do not trace the first divergent gate and therefore do not prove that the 32 associated failures were caused solely by nonconvergence. The remaining eight failures require additional carry, modular-correction, endpoint, and phase-cleanup instrumentation.

### Interpretation

Experiment 1 satisfies its empirical success criterion. On the common independently seeded corpus, ping-pong retains a lower raw and retry-adjusted $Q\times T$ than its exact source parent, while its observed failure rate is also lower. This strengthens the evidence that the reported resource reduction is not an artifact of the circuit-dependent Fiat--Shamir support.

The result remains finite-sample basis-state evidence. It does not establish all-input convergence, validate every truncated arithmetic assumption, or provide the success probability of a coherent Shor computation. The recurrence diagnostics confirm that the 704-round schedule is insufficient for some sampled denominators, so the corresponding limitation must remain explicit in the paper.

### Experiment Artifacts

The complete experiment is stored under:

**outputs/ecdsafail-pingpong-independent-100k-20260907/**

Key files:

- PROTOCOL_FROZEN.md: frozen circuits, seed, margin, and qualifications.
- analysis.json: machine-readable aggregate and paired results.
- analyze_results.py: deterministic reconstruction and diagnostic analysis.
- summary.csv: compact result table.
- results/pingpong/inputs.tsv: ping-pong per-input ledger.
- results/parent/inputs.tsv: parent per-input ledger.
- results/jump2/inputs.tsv: Jump-2 per-input ledger.
- results/pingpong/gcd_diagnostics.tsv: exact-recurrence diagnostics.
- ARTIFACT_MANIFEST.sha256: checksums for the principal artifacts.

Experiment 1 supports the conclusion that the comparison-free reversible Euclidean architecture retains its point-addition resource advantage under this independent common-corpus evaluation. A claim that the ping-pong construction also supports the coherent single-call interface required by windowed Shor remains contingent on Experiment 2. Neither conclusion constitutes a complete fault-tolerant attack estimate.

## Experiment 2 Results

Experiment 2 was completed on 2026-09-07. It adapts the requested submission **3616dbf2-f32d-41c8-9ea2-7a5bbe372fc0**, source `897dda2b0cf267151ecd973252d2a5078cbf1b63`, to the two-column runtime-table interface described in the supplied windowed-8e9c9a2 technical document and the latest arXiv draft.

### Source and Freeze

- Repository: [jieyilong/ecdsafail-challenge](https://github.com/jieyilong/ecdsafail-challenge).
- New branch: [codex/windowed-pingpong-3616dbf](https://github.com/jieyilong/ecdsafail-challenge/tree/codex/windowed-pingpong-3616dbf).
- Frozen circuit implementation: [a1373a0582c9554d66633b13c76300d0ecdf81c4](https://github.com/jieyilong/ecdsafail-challenge/commit/a1373a0582c9554d66633b13c76300d0ecdf81c4).
- Two-column adapter donor: `15a29ac9b1e97fc21eb81b9a6f0f6d9c4dc7a92e`. The later three-column variant was not used.
- The 704-round ping-pong recurrence, shrinking-width schedule, transcript, and replay implementation are unchanged. No circuit setting or nonce was changed after the full windowed run began.
- The default mixed mode reproduces the original compressed operation stream byte for byte. All 100,000 complete mixed result records also reproduce Experiment 1 exactly.
- Subsequent branch commits add analysis, documentation, and result artifacts, without changing the frozen circuit sources.

### Circuit Modifications

The quantum interface is $\lvert j\rangle_J\lvert R\rangle_{XY}\lvert0\rangle_W\mapsto\lvert j\rangle_J\lvert R+\mathcal T[j]\rangle_{XY}\lvert0\rangle_W$, subject to the inherited arithmetic assumptions. The ABI contains quantum registers $X,Y,J$ followed by classical 256-bit coordinate registers $T_x[0],T_y[0],\ldots,T_x[2^{16}-1],T_y[2^{16}-1]$. Row zero contains $(0,0)$ as the encoding of $\mathcal O$. Other rows contain affine points. Table contents are runtime data, not hard-coded point coordinates in the operation stream.

1. **Stage-local lookup and replay.** Stages 1 and 6 load both selected coordinates through a shared unary traversal. Stage 3 loads only $x_A$ using the donor's two-row-blocked, $K=2$ QROAM. Every selected payload is cleared before the division or multiplication peak.
2. **Two coordinate columns only.** Stage 3 applies $x_A$ and $2x_A$, reverses the temporary modular doubling, and replays the lookup. It does not introduce a precomputed $3x_A$ column.
3. **Original arithmetic backend.** The windowed coordinate routine calls the existing ping-pong division in Stage 2 and multiplication in Stage 5. Their source-level algorithm and parameters are retained.
4. **Coherent identity handling.** A flag $b=[j\ne0]$ controls the square and final modular negation. The square computes a 256-qubit masked slope $M=b\lambda$, applies the original product-register square to $M$, then uncomputes $M$. Computing and clearing the mask adds 512 CCX gates.
5. **Bounded carry workspace.** The product-register square limits carry venting to the remaining budget under $1321+w+1$ live qubits. Unvented carries are cleared by exact reverse Toffolis. This changes the space-work schedule without adding another arithmetic truncation.
6. **Inherited coordinate approximations.** Loaded-coordinate arithmetic uses the donor's low-peak routines, including its 64-bit upper comparison and short modular corrections. These remain approximations, not all-input guarantees.

For $j=0$, the coordinate payloads are zero, the square and final negation are disabled, and division and multiplication use the same denominator. They cancel on paths satisfying the arithmetic assumptions. The circuit does not measure the address or simply skip the entire GCD computation. The ordinary affine exclusions $R=\mathcal O$ and $R\in\{A,-A,-2A\}$ for nonidentity $A$ remain outside the declared domain.

The principal changes are in `src/point_add/pingpong_div.rs` and the `trailmix_ludicrous` coordinate, QROM, arithmetic, and square modules. The evaluator, simulator, and runtime table generator are byte-identical to the two-column Jump-2 donor.

### Corpus and Execution

The run used the requested **same 100,000 inputs**, with seed `ecdsafail-windowed-independent-random-100k-v1`. The generator consumes a pseudorandom little-endian 256-bit scalar to construct $R=[a]G$ and a uniform 16-bit address to select $A=[j]G$. It does not sample $a$ by exact rejection into $\mathbb Z_r$. Nonidentity equal-$x$ pairs are rejected during generation. The two identity rows, indices 3003 and 23423, are retained. No remaining $R=-2A$ exception occurred.

Joining all four ledgers by index found **zero differences** in addresses, accumulator coordinates, addend coordinates, or expected outputs. The SHA-256 of the sorted metadata records is `65a8808d67e6febcfacbc2587914090da6be005f3dc214c7c54dcc06c3b36f34`.

The mixed ping-pong circuit was evaluated again. The windowed Jump-2 comparison reuses its complete August 9 paired ledger. Its operation fingerprint was independently recomputed and matched the original checkpoint. This is not presented as a new Jump-2 evaluation. The mixed Jump-2 results come from Experiment 1.

The new full evaluation used eight workers on an Apple Silicon machine with 32 GiB RAM and 12 logical CPUs. It completed in 1,796.14 seconds, including initialization and temporary contention from an optional reference check. That redundant full-memory reference check was stopped, and a bounded-memory fingerprint check was used instead. The primary evaluation ran to completion without discarding or regenerating outcomes.

This is an **exploratory common-corpus comparison**, not a newly blinded confirmatory experiment. Development used the separate seed `ecdsafail-pingpong-windowed-pilot-20260907`. The original prospective requirement to generate a fresh held-out corpus is superseded here by the explicit request to reuse the same 100,000 inputs.

### Measured Operating Point

| Metric | Windowed ping-pong |
|---|---:|
| Peak logical width $Q$ | 1,338 |
| Mean executed Toffoli count $T$ | 1,288,559.92169 |
| Static Toffoli count | 1,345,161 |
| Total serialized operations | 217,603,629 |
| Mean evaluator-counted Clifford operations | 96,480,649.46440 |
| Static HMR operations | 1,332,256 |
| Static reset operations | 1,360,002 |
| $Q\times T$ | 1,724,093,175.22122 |
| Classical-output failures | 33 |
| Phase failures | 14 |
| Ancilla failures | 0 |
| Address-preservation failures | 0 |
| Inputs failing any channel | 36 |
| $\hat p$ | 0.99964 |
| Failure rate, 95% Wilson interval | 0.0360%, [0.0260%, 0.0498%] |
| $Q\times T/\hat p$ | 1,724,714,072.28724 |

Eleven inputs failed both the classical and phase checks, so the union is 36 rather than 47. Both identity-addend cases passed every recorded check. All means include failures and use exact batch totals rather than the evaluator's rounded console output.

Relative to mixed ping-pong, the window adapter adds **17 qubits (1.29%)**, **335,840.49854 mean Toffolis (35.25%)**, and **36.99% in raw $Q\times T$**.

Relative to the interface-matched windowed Jump-2 circuit, it uses **176 more qubits (15.15%)** but reduces mean $T$ by **23.49%**, raw $Q\times T$ by **11.90%**, and $Q\times T/\hat p$ by **12.04%**. Its mean counted Clifford operations increase by **6.31%**. The improvement is therefore a trade-off under the stated score, not a reduction in every resource.

### Paired Accuracy

| Common-domain comparison (99,998 inputs) | Both fail | Baseline only fails | Candidate only fails | Neither fails | Exact two-sided sign-test p-value |
|---|---:|---:|---:|---:|---:|
| Mixed ping-pong to windowed ping-pong | 36 | 4 | 0 | 99,958 | 0.125 |
| Windowed Jump-2 to windowed ping-pong | 0 | 191 | 36 | 99,771 | $1.07\times10^{-26}$ |
| Mixed Jump-2 to windowed Jump-2 | 162 | 28 | 29 | 99,779 | 1.0 |

Every windowed ping-pong any-channel failure also occurred in mixed ping-pong. Their nonidentity classical-output failure sets are identical. The reduction from 35 to 33 classical failures is entirely due to supporting the two identity rows. Phase outcomes differ because the operation streams use different measurement histories. There are eight windowed-only phase failures, but each occurs on an input already failing the classical check. No new any-channel failure is introduced on this corpus.

The four fewer common-domain failures do **not** establish that the adapter improves arithmetic accuracy. The exact paired test gives $p=0.125$, and the small number of discordant cases makes the normal paired interval unreliable for a superiority claim. For noninferiority, zero candidate-only failures gives a conservative exact one-sided 95% upper bound on the failure-rate increase of $1-0.05^{1/99998}\approx0.000029958$, or **0.0030 percentage points**. This is below the protocol's **0.05 percentage-point** margin. This bound follows because the failure-rate increase cannot exceed the probability of a candidate-only failure.

Against windowed Jump-2, the observed failure-rate difference is approximately **-0.1550 percentage points**, with an approximate paired 95% interval of **[-0.1845, -0.1255] percentage points**. This remains finite-sample, exploratory evidence under the stated input and measurement distributions.

Of the 33 inputs flagged by Experiment 1's intended-denominator convergence or width diagnostics, 31 fail the windowed circuit. Five other windowed failures remain unexplained by those diagnostics. These associations are not a first-divergent-gate diagnosis and do not justify removing the 704-round or truncation limitations.

### Lookup and Coherence Checks

The production lookup emitters passed all-address tests for **all 65,536 addresses** in each of three layouts: unary single-column, shared unary two-column, and $K=2$ single-column. Injective 16-bit row labels check routing across the entire address space. Every tested case preserved the address, produced the expected selected output, and cleared payload and routing workspace with zero residual phase.

At widths $w=0,\ldots,5$, tests also exercised the actual lookup/use/replay routines with arbitrary runtime **256-bit payloads**. All address components shared each of four measurement records: all-zero, all-one, and two pseudorandom records. Correct output images and identical phases were checked for every component, including the zero address.

These are **branchwise basis-image reconstruction checks**, not a dense state-vector simulation of the complete point-addition circuit. Their relevance to arbitrary complex address amplitudes follows from the lookup-specific argument: measuring a routing AND $ab$ contributes $(-1)^{mab}/\sqrt2$, and the recorded-outcome-controlled CZ cancels that phase. The controls remain available until cleanup. Thus each corrected lookup branch has an address-independent normalization factor, preserving arbitrary coefficients over the checked basis images. Selected payloads are replay-uncomputed, not measured.

Complete arithmetic was additionally tested in **256 four-call sequences at each $w=0,\ldots,5$**, totaling 6,144 calls on the development seed:

| Window bits | Q | Identity calls | Failed sequences | Classical failures | Phase failures | Ancilla failures |
|---:|---:|---:|---:|---:|---:|---:|
| 0 | 1,322 | 1,024 | 0 | 0 | 0 | 0 |
| 1 | 1,323 | 529 | 0 | 0 | 0 | 0 |
| 2 | 1,324 | 281 | 0 | 0 | 0 | 0 |
| 3 | 1,325 | 144 | 0 | 0 | 0 | 0 |
| 4 | 1,326 | 71 | 0 | 0 | 0 | 0 |
| 5 | 1,327 | 39 | 1 | 1 | 1 | 0 |

The one failing sequence is retained. It was not used to tune the final corpus. The inherited general `cargo test` target has stale test modules that do not compile. The dedicated production-QROM self-check and the five Python analysis tests pass. The trusted-library test target builds but contains zero tests.

### Reproduction and Artifacts

From the new branch:

```sh
cargo build --release --locked --offline --bin build_circuit --bin eval_circuit

WINDOWED_QROM_BRANCH_SELFTEST=1 ./target/release/build_circuit

python3 experiments/windowed_pingpong/run_cases.py full \
  --output /path/to/experiment-output --threads 8
```

The runner sets `WINDOWED_MODE=1`, `WINDOW_BITS=16`, `SINGLE_CCX_FANOUT_DISABLE=1`, the shared seed, 100,000 tests, and one call per case. Its allowed-error value of 1 collects all failures and is not an acceptance criterion. Use `--resume` only with the matching operation file and checkpoint. Omit `--offline` when dependencies must first be downloaded.

The SHA-256 of the new compressed operation stream is:

`76c990d44ab6dc1959141ef873dccdaaeab8099da302606f6cde76a802a293c4`

The complete local experiment is under **outputs/ecdsafail-pingpong-windowed-100k-20260907/**. The branch's **experiments/windowed_pingpong/** directory contains the construction protocol, provenance, analysis scripts, this research record, and released results. The shared corpus and all four per-input outcome ledgers are compressed and factored without dropping successful cases or failed outputs. Reconstructing the released ledgers reproduces the raw-ledger statistics exactly. Original ledger hashes and operation-stream fingerprints are recorded separately. The pre-Experiment-2 version of this document is preserved as `SPEC_BEFORE_EXPERIMENT_2.md`, retaining the document hash recorded in Experiment 1's historical manifest.

Resource reporting departs from the original prospective list in three respects: executed Toffoli costs are available per 64-input batch, not per individual input; executed measurement counts and feed-forward rounds are unmeasured; Toffoli depth is unmeasured. Static HMR/reset counts must not be interpreted as measurement depth. The evaluator's counted Clifford total excludes tracked X and Z operations and includes CX, CZ, SWAP, HMR, and reset.

### Interpretation

The experiment supports a **window-selected, single-call ping-pong construction** with a lower measured $Q\times T$ than the earlier two-column windowed Jump-2 construction and no observed any-channel accuracy regression relative to mixed ping-pong on the common supported domain. The lookup argument and dedicated checks address the newly introduced coherent selection and cleanup, conditional on the arithmetic backend's assumptions.

It remains an approximate circuit evaluated on a finite, previously studied corpus. The result does not prove all-input arithmetic correctness, bound coherent full-attack error, or implement the complete shifted-table, window, Fourier, and postprocessing schedule of Shor's algorithm. $Q\times T/\hat p$ remains a per-call retry-sensitivity proxy, not a coherent-Shor cost estimate.
