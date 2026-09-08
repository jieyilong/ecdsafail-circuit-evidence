# Experiment 2 protocol

Date: 2026-09-07. Freeze applies before the 16-bit 100,000-input windowed evaluation.

- Circuit base: 897dda2b0cf267151ecd973252d2a5078cbf1b63.
- Adapter donor: 15a29ac9b1e97fc21eb81b9a6f0f6d9c4dc7a92e.
- Primary corpus seed: ecdsafail-windowed-independent-random-100k-v1.
- Development seed: ecdsafail-pingpong-windowed-pilot-20260907.
- Test cases: 100,000, using the unchanged donor generator and per-batch measurement seed.
- Uniform 16-bit address j; the accumulator is obtained from the generator's 256-bit pseudorandom scalar. Equal-x nonidentity pairs are resampled. Identity rows are retained.
- Window width: 16. Two runtime coordinate columns. Default unary paired-column lookup and K=2 single-column lookup. Payload unload by replay.
- Noninferiority margin for any-channel failure-rate increase: 0.0005 (0.05 percentage points), carried over from Experiment 1 as an exploratory comparison margin. It is not derived from a coherent Shor error bound.
- Report Q, static and executed T, Q*T, empirical any-channel pass rate, Q*T/pass-rate, Wilson 95% intervals, and paired discordant outcomes.
- Report identity rows separately. Do not count an unsupported identity in a mixed baseline as a regression of its ordinary affine arithmetic.
- Reconcile all 100,000 address/accumulator/addend/expected-output columns against Experiment 1's ledgers.
- Analyze the already studied corpus as an exploratory paired comparison. Do not describe it as a new blinded or confirmatory sample.
- Record every failure. Do not tune the circuit or select a new nonce after inspecting final outcomes.
- Keep Experiment 1 data immutable. Experiment 2 summaries identify source and operation-stream hashes.

The complete circuit retains the source's 704-round and finite-width approximations. No inference of all-input or full-Shor correctness is made from the sample.
