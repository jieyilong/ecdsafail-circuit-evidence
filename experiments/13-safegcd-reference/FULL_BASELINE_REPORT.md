# Complete unoptimized references

September 22, 2026. This supersedes the first-pass round-only status.
No parent source or frozen reference was edited. All new code and generated
circuits are in `ecdsafail-qip-safegcd-20260922`; reports are in this directory.

## Primitive-matched complete DIV/MUL components

Both rows below use the **same implementation** of canonical negation,
addition, halving, comparison and measurement-free Cuccaro arithmetic in
`safegcd_probe/full.py`. Both retain full signed value widths, quantum history,
fixed physical input/output wires and explicit scratch. Neither uses the
reference's optimized measured adders or shrinking value layout.

| Complete component | Rounds | Full width | Same payload primitives | Q | Static T per DIV or MUL | Budget status |
| --- | ---: | --- | --- | ---: | ---: | --- |
| Safegcd | 741 | Yes | Yes | 3,300 | 7,501,932 | Proved Bernstein-Yang round bound on nonzero canonical field input |
| Ping-pong, previously fixed horizon | 768 | Yes | Yes | 2,320 | 6,289,400 | Conditional and known insufficient; diagnostic failures retained |
| Ping-pong, generous horizon | 1,536 | Yes | Yes | 3,088 | 12,574,712 | Conditional budget, not a proved universal bound |

These counts come from complete emitted streams parsed by the original
simulator, including setup, every value/controller round, all coefficient
rounds, endpoint normalization, reverse value walk and final cleanup. MUL is
the exact reversed DIV stream and is also tested on independent initial
payloads, not only as the undo of a previous DIV. No stopping-time discount
or classical routing is charged as free.

All are **unoptimized references**. The rows match payload arithmetic lowering
and allocation conventions, but deliberately use different history/controller
state and different round budgets. The figures do not establish an optimized
recurrence advantage or global resource dominance. In particular, 1,536
ping-pong rounds is not proved sufficient for every secp256k1 denominator.

The PP768 stream uses the previously fixed 768 candidate, not a horizon tuned
on the common corpus. It is cheaper than safegcd under these same primitives,
whereas PP1536 is more expensive. This negative comparison must not be omitted:
the apparent ordering depends strongly on how many ping-pong rounds are paid
for. PP768 is not a correct all-input substitute. `pingpong-768-results.json`
records its original-simulator output and scratch failures on the unchanged
128-case common corpus, separately for DIV and MUL. Passing exact circuit
reversal does not repair an incorrect forward arithmetic map.

The measured PP768 outcome is **12/128 failing DIV cases and 12/128 failing
MUL cases**. In both directions all 12 have wrong public outputs and dirty
scratch; there are zero phase failures. All 128 still reverse exactly, as a
reversible but arithmetically incorrect forward map must. The zero payloads
pass, so they were included rather than discarded from the failure denominator.

The exact full-width ping-pong recurrence keeps both values odd, first lifting
an even denominator to `z-p`. On alternating target banks it records
`s=source[1] XOR target[1]`, then applies
`target <- (target + (-1)^s * source)/2`.
The coefficient pass applies the same signed modular add followed by canonical
halving. Terminal signed units yield two signed copies of `c/z`; canonical
sign corrections and XOR erase the redundant coefficient. The inverse clears
the history and restores the odd-lift bit and original denominator. Padding
after the signed-unit pair is stable. There is no shrinking-width assumption.

The common test includes `z=3`, whose exact walk needs **1,135** rounds, and
`z=2^255`, which needs **1,239**. Thus 736/768 is not a universal terminal
budget. The extra literal `z=0xd3` test takes 1,016 rounds; it is distinct from
the denominator-3 example. See the convergence entries in `full-results.json`.

## Actual matched-shell point-addition emissions

These are separately emitted **four-bit-window**, single-call, quantum-addressed
point-addition circuits. The frozen experiment-09 coordinate shell, canonical
coordinate wrappers, square, QROM and evaluator remain byte-identical. Only
the DIV/MUL callback is replaced in the private copy. They are not modeled
by adding component estimates to an existing published result.

| Actual w=4 shell | Q | Serialized static T | Mean executed T, 64 shots | Any-channel failures |
| --- | ---: | ---: | ---: | ---: |
| Safegcd callback, pure Cuccaro payload | 3,305 | 15,077,023 | 15,076,583.516 | 0/64 |
| Frozen canonical ping-pong, fast HMR payload | 1,792 | 5,020,617 | 5,020,169.953 | 0/64 |

**Matched shell is not matched arithmetic lowering.** The second row retains
fast measurement-uncomputed arithmetic and the guarded 736-round shrinking
schedule. This cost gap cannot isolate the recurrence and is not a fair
optimized-safegcd comparison. Its 0/64 pilot is conditional evidence, not an
all-input guarantee. The known long walks invalidate a universal bounded
schedule claim even though the pilot happened to pass. No w=16 result is
claimed or inferred from either w=4 row, and neither row is full Shor.

Both calls use the same fresh evaluator seed and same w=4 table/input schedule.
The common seed is independent of circuit serialization. Output, phase and
ancilla channels all had zero failures. The pilot contains 64 basis-input
shots, including four identity-table rows; it is not a state-vector proof for
the complete shell or a useful rare-event error bound.

## Emitted versus bookkeeping counts

| Shell | Builder scratch bookkeeping T | Actual serialized T | Discarded forward-work excess |
| --- | ---: | ---: | ---: |
| Safegcd w=4 | 15,083,167 | 15,077,023 | 6,144 |
| Canonical ping-pong w=4 | 5,026,761 | 5,020,617 | 6,144 |

The frozen `emit_inverse` materializes forward operations, truncates their
stream, and emits the inverse without undoing non-count-only bookkeeping.
Three inverse coordinate-subtraction blocks each contribute 2,048 temporary
forward Toffolis. `stats_stream` directly reads each final compressed `ops.bin`;
its CCX+CCZ count is authoritative. `collect_results.py` asserts the exact
6,144 discrepancy for both streams and verifies their hashes. No discarded
forward operation is counted in the report's static T.

## Validation

- Full safegcd small-prime DIV and MUL: 5,196 exhaustive `(z,c)` cases in each
  direction across p=3,5,7,11,13,17,31,61. All data, phase, history and scratch
  wires checked, forward and inverse, by the original simulator.
- Full-width ping-pong using identical payload helpers: the same 5,196 cases
  per direction, with generous `8*n+16` rounds and scalar convergence checks.
  Exhaustiveness applies only to these listed primes, not secp256k1.
- Safegcd sparse coherent-state tests at p=3,5,7,11: arbitrary nonuniform
  relative phases across the entire supported denominator/payload subspace,
  exact DIV and MUL outputs, all scratch zero, inverse composition identity.
- Standalone coefficient gates: exhaustive arbitrary canonical coefficient
  pairs over six small primes for all three `(e,s)` codes, plus 915 secp256k1
  branch/pair cases. This supplements reachable-state integration tests.
- Both n=256 components: **128 common fresh cases per direction**, including
  zero payloads and the long-walk examples. All wires checked before any reset;
  inverse restores the original state exactly. An earlier separate safegcd
  128-case corpus also passed.
- Two actual w=4 point-addition emissions: 64 common fresh shots each, 0 output,
  phase or ancilla failures. The unchanged square's broader limitations remain.

Small-field coherent evidence does not extend the inherited point-addition
shell's supported-domain theorem. The safegcd division contract excludes z=0
and noncanonical input words. Both complete component gate streams are pure
X/CX/CCX permutations, giving an exact phase-free coherent extension on their
specified supported subspaces.

## Complete accounting

| Safegcd DIV stage | Static T |
| --- | ---: |
| Setup and constant unload | 0 (502 X gates total) |
| 741 value/controller forward rounds | 1,381,224 |
| 741 canonical payload rounds | 4,737,954 |
| Terminal sign and physical ABI transfer | 1,530 |
| 741 reverse value/controller rounds, history cleanup | 1,381,224 |
| Total | 7,501,932 |

The safegcd component's fixed 3,300-wire layout is 1,028 value/payload wires
(two 258-bit signed banks and two 256-bit field banks, including the caller
banks), 11 delta, 1,482 history, and 779 scratch. Scratch includes 258 temporary
addend/MCX wires, one carry, 256 masked-addend wires, 258 comparison wires and
six predicate/extension wires. All are counted while idle as well as active.

The primitive-matched ping-pong uses 1,028 value/payload wires, 1,536 history,
one lift bit, and 523 scratch wires. It needs no parity-masked addend bank or
delta register. Its setup/unload contributes 1,028 Toffolis, value walks
789,504 in each direction, coefficient replay 10,991,616, and endpoint 3,060.
These sum to 12,574,712. Endpoint handling includes zero payloads, not only
nonzero residues.

## Artifacts and reruns

`full-results.json` aggregates source and stream hashes, exact phase ledgers,
the matching audit, and common-corpus reports. Full streams and reproduction
scripts live under the dedicated worktree's `safegcd_probe/`. The private
frozen-shell source is `matched_reference/`; its only changed existing source
is `src/point_add/pingpong_div.rs`, plus new `safegcd_stream.rs`.

```sh
python3 -B safegcd_probe/test_full.py
python3 -B safegcd_probe/test_coefficients.py
python3 -B safegcd_probe/test_pingpong.py
python3 -B safegcd_probe/common_components.py
python3 -B safegcd_probe/collect_results.py
```

Run those from the dedicated worktree after building `safegcd_round_verify`
and generating the component streams using `full.py` and `pingpong.py`.
`run_matched.py emit/eval --w 4`, with and without `--baseline`, reproduces
the full-shell runs using `target/matched/release` binaries. All lowerings
remain deliberately unoptimized. No public result or manuscript was changed.
