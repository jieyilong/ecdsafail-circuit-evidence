# 05. Post-Hoc Zero-Payload Probe

[Repository overview](../../README.md) | [Generated results](RESULTS.md) | [Summary CSV](summary.csv) | [Interpretation](../../docs/INTERPRETATION.md)

**Purpose:** test representation and phase behavior of ping-pong division and multiplication on zero payloads. This separate diagnostic supports the structured boundary check in **Section 7.4**, the encoding and phase conditions in **Section 4.3**, and **Section 8's limitations**.

It was performed after the frozen random study. It does not modify any of that study's three streams or outcomes, and it is not a fourth point-addition candidate.

## Observations

| Subroutine | Cases | Output word p instead of canonical zero | Phase flags | Denominator mismatches | Dirty ancillas |
|---|---:|---:|---:|---:|---:|
| Division | 64 | 28 | 19 | 0 | 0 |
| Multiplication | 64 | 46 | 26 | 0 | 0 |

Every nonzero observed output word equals the field modulus $p$, so it is congruent to zero modulo $p$ but is not the canonical zero bit string. Output and phase categories overlap. Do not add the two columns to infer an any-channel count.

## Fixtures and Source

The fixtures use the first 64 division denominators in fresh stratum `G-s0`, ordered by input index. Their exact signed value walks converge to signed units within 667 rounds and fit the selected 736-round guarded schedule, including pre-halving sums. This controls value-walk conditions, not the modular coefficient folds or phase predicates.

An initial small-integer-denominator attempt encountered a width violation during a classical precheck and was not used to isolate coefficient behavior. The retained fixtures are targeted diagnostic inputs, not a random error-rate sample.

The original records are kept with the isolated source snapshot instead of duplicated here:

| Record | Purpose |
|---|---|
| [Original probe README](../../sources/trees/zero-payload-probe/README.md) | Protocol, instrumentation, and original command |
| [selection.json](../../sources/trees/zero-payload-probe/selection.json) | Source indices, denominator words, and convergence rounds |
| [probe-inputs.json](../../sources/trees/zero-payload-probe/probe-inputs.json) | Ordered denominator fixtures in JSON |
| [probe-denominators.txt](../../sources/trees/zero-payload-probe/probe-denominators.txt) | Input file used by the diagnostic entry point |
| [zero-probe.log](../../sources/trees/zero-payload-probe/zero-probe.log) | Actual per-case report and totals |
| [Original source archive](../../sources/archives/zero-payload-probe.tar.gz) | Byte-identical archived diagnostic source and records |

Instrumentation is limited to an early emitter dispatch, module visibility, and an appended reporting helper. The arithmetic functions are unchanged from the conservative source. The helper uses the existing simulator and seed `qip-posthoc-zero-payload-probe-v1`.

## Reproduction and Scope

From the repository root:

```sh
python3 scripts/reproduce.py build --candidate zero-payload-probe
python3 scripts/reproduce.py zero-probe
```

The probe is an emitter entry point, not a library unit test. The original `cargo test --lib` attempt ran zero tests and provides no evidence. New output belongs under `.work/`, leaving the original log intact.

These component results demonstrate that field congruence and a convergent value walk are insufficient to certify canonical register behavior and correct phases. They do **not** establish a full point-addition failure count, supply resource estimates, or change the conservative circuit's recorded **0 / 100,000** fresh-study result. No corrective patch is promoted into the frozen circuit.
