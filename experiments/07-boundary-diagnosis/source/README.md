# Post-Hoc Zero-Payload Boundary Probe

This is an isolated diagnostic derived from frozen source `345c23fcf1073b7559a9d41e113f755259545bf2`. It does not change any operation stream or result in the frozen three-circuit study.

The helper tests the division and multiplication subroutines on payload zero. The 64 denominators are the first 64 division denominators in fresh stratum G-s0, ordered by input index. Their exact signed value walks reach signed units within 667 rounds and fit the selected 736-round guarded width schedule, including the pre-halving sums. This controls the value-walk preconditions, not the modular coefficient folds or phase predicates.

An initial attempt using small integer denominators encountered a width violation in a classical precheck. Those cases were not used to isolate coefficient behavior. The selected fixtures are diagnostic cases, not a random error-rate sample. Full scalar values and source indices are retained in `selection.json`.

## Reproduction

```sh
cargo build --release --locked --offline --bin build_circuit
QIP_PINGPONG_PROFILE=guarded TLM_MSBS=40 \
QIP_ZERO_PROBE_INPUTS="$PWD/probe-denominators.txt" \
./target/release/build_circuit
```

Omit `--offline` if dependencies are not cached. The probe is an entry point in the isolated emitter, not a library unit test. A first `cargo test --lib` invocation ran zero tests and is not evidence. The actual report is `zero-probe.log`.

The only source instrumentation is an early diagnostic dispatch in `build_circuit`, module visibility for that dispatch, and an appended reporting helper. The arithmetic functions are unchanged. The helper uses the existing simulator, with SHAKE seed `qip-posthoc-zero-payload-probe-v1`, and does not report resource estimates or acceptance status.

## Observations

| Subroutine | Cases | Output word p instead of canonical zero | Phase flags | Denominator mismatches | Dirty ancillas |
|---|---:|---:|---:|---:|---:|
| Division | 64 | 28 | 19 | 0 | 0 |
| Multiplication | 64 | 46 | 26 | 0 | 0 |

All nonzero output words equal p, so they are congruent to zero as field values. They are not the canonical zero bit string. Phase and output categories overlap and must not be added to infer an any-channel failure count.

These are component-level observations. They do not establish a failure count for complete point addition, and do not alter the random-study pass fractions. They demonstrate why field congruence alone is insufficient to justify a canonical quantum-register map, and why the arithmetic proposition must state its representation and phase assumptions. No corrective patch is promoted into the frozen circuit.
