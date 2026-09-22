# Safegcd bounded deliverable, September 22, 2026

## Current Status: Complete References

The follow-up completed full DIV/MUL and actual w=4 point-addition emissions.
See **[FULL_BASELINE_REPORT.md](FULL_BASELINE_REPORT.md)** and `full-results.json`.

| Complete component, same canonical Cuccaro payload primitives | Q | Static T per direction |
| --- | ---: | ---: |
| Safegcd, 741 rounds | 3,300 | 7,501,932 |
| Ping-pong, conditional/insufficient 768 rounds | 2,320 | 6,289,400 |
| Ping-pong, conditional 1,536 rounds | 3,088 | 12,574,712 |

The 741-round safegcd and 1,536-round ping-pong pass 128 common secp256k1 cases per direction and 5,196 exhaustive
small-prime cases per direction. The safegcd w=4 full shell measures Q=3,305,
T=15,077,023 and passes 64 common pilot shots. The frozen canonical ping-pong
w=4 shell measures Q=1,792, T=5,020,617 and also passes, but uses different
fast HMR arithmetic and an insufficient-as-a-universal-bound 736-round budget.
Its cost gap does **not** isolate recurrence. All variants are unoptimized or
conditional references, with no optimized-safegcd claim and no w=16 extrapolation.

The remainder below is the preserved **first-pass round-only record**, not
the current completion status. `SPECIFICATION.md` and `GATE_ACCOUNTING.md`
also retain that first-pass snapshot; the full report supersedes their open
implementation statuses and supplies measured complete accounting.

## Result

**Actual emitted reversible controller/value divstep: Q=788, static T=1,864
CCX per direction.** Counts include delta, two quantum history bits, signed
value banks, predicate/routing gates and 259 scratch qubits. They exclude the
coefficient pass and caller payload. This is NOT the requested matched full
division/point-addition baseline; that remains unfinished.

The original repository parser and simulator passed 24,836 secp-width states
and 8,432 exhaustive small signed states, forward and inverse. All output
wires, scratch, history, delta and phase were checked. The emitted circuit
uses only X, CX and CCX, with no measurements or classical routing.

The exact scalar payload model passed 137,112 exhaustive small-field pairs
over all odd primes below 128, plus 3,084 payload cases across 771 secp256k1
denominators. It uses the primary-paper 741-round bound and preserves the
existing in-place denominator/payload ABI, including multiplication as the
inverse. These are scalar tests, not full-circuit correctness measurements.

## Files

- `SPECIFICATION.md`: recurrence/bound, coefficient maps, predecessor decoder,
  delta/history cleanup, widths and complete DIV/MUL schedule.
- `GATE_ACCOUNTING.md`: measured round, complete-call accounting obligations,
  lifetime table and explicitly unmeasured terms.
- `scalar.py`, `verify.py`, `scalar-results.json`: exact scalar model/tests.
- `gates-256-results.json`, `gates-small-results.json`: original-simulator reports.
- `SOURCES.md`: workspace index search and primary-source provenance.
- `provenance.json`: frozen parent and simulator/stream hashes.

Isolated detached worktree: `ecdsafail-qip-safegcd-20260922/` at
`345c23fcf1073b7559a9d41e113f755259545bf2`, with new files only:

- `safegcd_probe/round.py`: reversible round emitter and separate Python gate tests.
- `safegcd_probe/round-256.kmx`: frozen executable gate stream.
- `safegcd_probe/round-small.kmx`: small-width gate stream.
- `safegcd_probe/*-vectors.txt`: scalar-generated full-wire expected states.
- `src/bin/safegcd_round_verify.rs`: original-simulator validation driver.

The original simulator and parser are byte-identical to the user-designated
`ecdsafail-qip-oral-repairs-20260922` parent. Its uncommitted repairs were not
copied or modified; the probe uses the shared frozen HEAD and unchanged
simulator, not the in-progress point-addition repair implementation.

## Reproduce

Run from the workspace root, then the isolated worktree as shown:

```sh
python3 -B research/qip-oral-20260922/safegcd/verify.py
python3 -B ecdsafail-qip-safegcd-20260922/safegcd_probe/round.py
cd ecdsafail-qip-safegcd-20260922
cargo build --offline --release --bin safegcd_round_verify
./target/release/safegcd_round_verify safegcd_probe/round-256.kmx safegcd_probe/round-256-vectors.txt ../research/qip-oral-20260922/safegcd/gates-256-results.json
./target/release/safegcd_round_verify safegcd_probe/round-small.kmx safegcd_probe/round-small-vectors.txt ../research/qip-oral-20260922/safegcd/gates-small-results.json
```

## Remaining work

The next necessary implementation is the fully reversible canonical modular
coefficient half/double and add/subtract pair, followed by endpoint sign/ABI
maps and complete 741-round DIV/MUL generation. The raw history requires 1482
qubits; the straightforward full layout is already too wide to serve as a
low-width improvement claim. Emit and measure the full schedule before any
comparison against a matched point-addition baseline. This pass did not claim
that the full baseline was completed or optimized.
