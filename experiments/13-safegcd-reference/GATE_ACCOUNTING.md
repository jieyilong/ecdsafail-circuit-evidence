# Full accounting obligations

Follow-up: these first-pass obligations are now discharged for complete
DIV/MUL and measured w=4 shell integration; see `FULL_BASELINE_REPORT.md` for
actual totals, validation limits, and the arithmetic-matching distinction.
The old unknown/extrapolated entries below are retained as a historical ledger.

## Measured isolated round, not full division

The emitted original-delta controller/value round at n=256 uses 258-bit signed
f/g banks, 11 delta wires, 2 history wires, and 259 clean scratch wires:
**Q=788, static T=1,864 CCX**, plus 3,706 CX and 24 X per direction.
The inverse has identical static counts. No measured branches, classical
conditions, free conditional routing, reset, or phase repair are present.
These counts cover the actual emitted stream, not Python operation counts.
Payload/coefficient banks and their gates are absent from this isolated Q/T.
See the original-simulator JSON reports for independent stream checks.

## Persistent storage and lifetimes

| Live object | Size for n=256 | Lifetime |
| --- | ---: | --- |
| f, g boundary values | 2*257=514 | setup through value reversal |
| Conservative emitted guard extension | 2 | same lifetime |
| delta | 11 | setup through value reversal, then constant unload |
| history (e,s) | 2*741=1482 | recorded prefix until matching reverse step |
| payload b + extra coefficient a | 512 | payload entire call, a coefficient pass |
| lowered value scratch | 259 | one round, recycled after zero verification |
| coefficient/normalization scratch | unknown | must be measured after lowering |

The minimal boundary-bank schedule with both coefficient banks live occupies
2519 wires before scratch; the emitted guard convention raises this to 2521.
A conservative all-banks-live embedding with the present value scratch would
occupy 2780 wires before any larger coefficient scratch. This is a layout
calculation, NOT measured peak Q of a complete generated call. An actual
allocator may shorten the extra coefficient bank's lifetime, but must retain
and account for the payload while the value walk is running. Other live point
coordinates, coherent addend/QROM banks, and caller scratch are additional.
No claim of fitting the existing low-Q circuit follows from this layout.

## Required cost ledger

| Component | Must charge | Current evidence |
| --- | --- | --- |
| Setup/teardown | constants, extensions, wire layout, every carry cleanup | specification only |
| Value/controller forward | parity, signed delta>0, record, negation, delta update, coherent routing, full-width add, reversible shift | one round emitted |
| Value/controller reverse | exact predecessor, delta recovery, scratch/history erasure | reversed round emitted |
| Coefficient forward | controlled swap/negation, e-controlled add, canonical reduction, modular half, temporary controls | scalar verified only |
| Coefficient reverse | modular double, canonical reduction/subtraction, routing, temporary controls | scalar verified only |
| Modular half | canonicalize sum/difference, parity-conditioned +p including carry, reversible divide, parity/overflow cleanup | unmeasured |
| Terminal normalization | sign(f)-controlled modular negation including zero fixup; full fixed ABI swap | unmeasured |
| History access | all 1482 live qubits, addressing or any compression/recomputation decoder | raw tape specified, full allocation unmeasured |
| Phase | every HMR feed-forward/repair if introduced; no state-dependent phase | no phase gates in present round |
| Full point addition | both DIV and MUL uses, field multiplication/squaring, additions, exceptions, other live registers, coherent addend interface | not assembled |

Using V_i and V_i^-1 for charged value-round costs, C_i for coefficient replay,
and E for normalization/ABI transfer, the division ledger is

```
T_DIV = T_setup + sum_i T(V_i) + sum_i T(C_i)
        + T(E) + sum_reverse_i T(V_i^-1) + T_teardown.
T_MUL = T_setup + sum_i T(V_i) + T(E^-1)
        + sum_reverse_i T(C_i^-1) + sum_reverse_i T(V_i^-1) + T_teardown.
T_PA  = T_other_PA + T_DIV + T_MUL       [only if this is the actual caller schedule]
Q_PA  = max_over_time(all live caller, history, data, coefficient, scratch wires).
```

Repeating this exact measured value kernel gives an arithmetic contribution
`2*741*1864 = 2,762,448` CCX to one DIV (forward/reverse values), and
`4*741*1864 = 5,524,896` to a DIV+MUL pair. These are **extrapolated value-only
contributions**, not measurements of complete calls, and not algorithmic
lower bounds. All coefficient and integration terms remain unknown, not zero.

## Acceptance gates before a matched-baseline claim

1. Emit both coefficient directions and endpoint maps, with the same canonical
   p-field and payload ABI. Check arbitrary coefficients as well as reachable
   payload states; coefficients need modular half, not signed integer half.
2. Emit all 741 rounds with quantum history, original-wire restoration, and
   an explicit full allocation trace. Do not overwrite predecessor information.
3. Run the original simulator on complete DIV/MUL calls and their composition,
   checking data, every freed wire, and phase. Fresh inputs after source freeze.
4. Replace both arithmetic call sites in the point-addition parent; preserve
   its actual mixed/coherent addend interface and supported-domain policy.
5. Measure Q and static/executed T from that same emitted circuit and corpus.
   Report source/stream hashes, configuration, seed, failure channels and counts.
6. Only then compare with the frozen parent. Neither a classical constant-time
   implementation nor this scalar reference qualifies as an optimized quantum
   baseline. Classical instruction counts and quantum-control-zero frequencies
   are not discounts on emitted Toffolis.

No scan, leaderboard submission, new approximation, paper-result replacement,
or optimized-baseline claim was performed in this bounded pass.
