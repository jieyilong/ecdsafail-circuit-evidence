# Publication Checks

## v1.2.0 Additions

The root verifier also checks experiment 08, all 148 original supplement files,
and preservation of v1.1.0 scientific records. It recomputes the scalar/trace
correspondence and runs six standard-library diagnostic tests without circuits.
The original seven-test receipt includes a GMP crosscheck, available separately
through the scratch-space reproduction wrapper. The 10-million-trial loop and
full circuit executions are not rerun in CI. No high-cost reference circuit is
included, and the original frozen outcomes remain unchanged.

Publication testing passed all 22 root regression tests. The scratch-space
wrapper also rebuilt the GMP diagnostic, reproduced the 10,000-case prefix,
and passed the original seven-test suite including the 1,033-case GMP/Python
comparison. These small publication checks are not new ten-million-trial or
full-circuit runs.

## v1.1.0 Additions

The root verification command and CI now check the portable accounting and boundary packages, preserve the original v1.0.0 scientific files, and rerun scalar algebra/accounting checks. These are offline record and source checks, not new circuit experiments. Nineteen root regression tests cover the original wrappers and the added verification paths.

The accounting package retains 12 successful bounded instrumented/unchanged stream comparisons and all six smoke runs, including failures. Omitted operation streams remain historical hash receipts. The boundary package has seven portable verification groups and a separately recorded offline rebuild/replay. Its preserved eight-test diagnosis receipt is not misreported as a new CI circuit execution. The local 9,200-case negation result is not a complete repair.

The new files were verified in their staged and relocated layouts before publication. No frozen outcome, original source snapshot, pre-study freeze, or v1.0.0 tag is replaced. The checks below describe the original publication and retain their historical scope.

The reorganization preserves all **235 original bundle files byte for byte**. Four source archives are unchanged. Their browsable trees omit only the explicitly recorded cached-bytecode copies.

## Completed Checks

- The original verifier reconstructed all 300,000 fresh-study outcome rows and checked original raw-file hashes, byte offsets, failure unions, and batch counts.
- All five development ledgers and the 8,192-case evaluator-equivalence comparison reproduced their recorded statistics.
- The optional OpenSSL oracle was rerun on all 100,000 fresh inputs, selected addends, and expected sums, with no mismatches.
- All 15 derived Markdown/CSV/JSON reader-facing reports agree with the original records.
- The current reproduction wrapper built the conservative emitter and evaluator from the browsable snapshot using Rust 1.93.0.
- It emitted a compressed operation stream with the original SHA256 `9b1c169117e804991284c41850027af2f60ed7f01016aff0c481ef39b1b4b7f6`.
- A 128-case conservative G-s0 smoke run matched every recorded input, output, failure flag, and integer batch gate total for that prefix.
- The separate zero-payload wrapper reproduced both negative component reports. This is not a fourth final-study circuit or a random accuracy estimate.
- Unit tests cover preserved bytes, source-tree identity, report generation, case expansion, complete failure indexes, environment isolation, invalid smoke sizes, and output-path alias protection.

The reorganized repository was not used to rerun all 300,000 circuit executions for publication. Those original complete executions are the frozen scientific evidence. The publication checks verify their records and test the new access/reproduction paths.

## Independent Review and Privacy Check

A separate read-only agent review identified work-directory alias risks and an unverified browsable-probe read. Output guards, atomic receipt/report writes, source verification, and regression tests address those findings. The wrappers are not a security sandbox for arbitrary untrusted programs or a concurrently hostile local filesystem.

A scan of the complete original ZIP, gzip ledgers, and source-archive members found no patterns matching GitHub/API tokens, AWS access keys, private-key PEM blocks, or credential-bearing URLs. Historical local paths remain in preserved logs and source caches. No claim is made that a pattern scan is a complete security audit.

The [GitHub verification workflow](.github/workflows/verify.yml) repeats standard-library tests and complete evidence reconstruction. The optional oracle and large circuit executions are not run automatically in CI. No scientific correctness statement beyond the documented finite-sample and conditional scope follows from passing these checks.
