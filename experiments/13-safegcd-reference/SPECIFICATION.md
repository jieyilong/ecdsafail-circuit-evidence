# Reversible safegcd baseline specification

Follow-up status: complete gates and shell integration are now measured in
`FULL_BASELINE_REPORT.md` and `full-results.json`. The "not yet lowered"
statements below record the first-pass state and are superseded by that report.

Status: exact scalar specification and isolated emitted controller/value round.
NOT an emitted matched division baseline, NOT a full point-addition baseline,
and NOT an optimized-baseline claim. The coefficient pass remains unlowered.

## Interface and provenance

Prime `p = 2^256 - 2^32 - 977`, `n = 256`. Use little-endian field registers,
canonical residues `0 <= c < p`, and nonzero denominator `0 < z < p`.
The required clean interface is

```
DIV: |z>|c>|0_work> -> |z>|c/z mod p>|0_work>
MUL: |z>|c>|0_work> -> |z>|z*c mod p>|0_work> = DIV^-1.
```

This matches `pingpong_mod_mul_div_in_place` in
`ecdsafail-qip-bounded-validation/src/point_add/pingpong_div.rs:57`, at
commit `345c23fcf1073b7559a9d41e113f755259545bf2`. In particular, output must
return on the original denominator/payload wires, not just a relabeled bank.
The oral-repairs parent has the same HEAD but concurrent uncommitted edits;
the new sibling `ecdsafail-qip-safegcd-20260922` starts from this frozen HEAD.
The original parser/simulator files are unchanged in both parents.

At the generic-affine point-addition interface, `z=d_x=x_R-x_A` and `c=d_y`
produce the slope. A caller using the two opposite differences has the same
slope. This block does not resolve zero denominators, `R=+/-A`, identity
points, or other exceptional-domain handling. Tests reject `z=0`; a complete
unitary still needs a specified extension on unsupported encodings. No field
input, payload, or addend is treated as classical merely to save gates.

## Primary source and round bound

Bernstein and Yang, *Fast constant-time gcd computation and modular inversion*,
2019-04-13, Sections 8.1-8.3, Theorems 9.1-9.2 and 11.2, Figure 11.1.
[Author copy](https://troll.iis.sinica.edu.tw/by-publ/recent/safegcd.pdf),
[accessible primary-paper mirror](https://d-nb.info/1205834052/34).
The author PDF timed out, so the complete theorem and recurrence were read
from the identical titled primary paper at the mirror, journal pp. 360-366.
The computer-assisted convergence proof itself was not rerun.

For initial `(delta,f,g)=(1,p,z)`, choose
`N=floor((49*n+80)/17)` for `n<46`, otherwise
`N=floor((49*n+57)/17)`. Here `N=741`. The theorem's size hypothesis holds
because `p^2+4*z^2 < 5*2^(2*n)`. Terminal values satisfy `g_N=0`, `f_N=+/-1`.
This is the original integer-delta recurrence, not half-delta, plus/minus
divstep, or the Bitcoin implementation's separately established shorter bound.
Fixed padding continues through all 741 rounds, including after `g=0`.

## One reversible value round

At entry let `e=g mod 2` and `s=e AND [delta>0]`. Store `(e,s)` in two clean
history qubits by coherent predicate XOR. Record old-state parity, not an
unexplained post-update parity.

| Branch | delta' | f' | g' |
| --- | --- | --- | --- |
| s=1 | 1-delta | g | (g-f)/2 |
| s=0 | 1+delta | f | (g+e*f)/2 |

All RHS values refer to the predecessor. Division is exact signed integer
division. The inverse, while retaining the record, is

| Branch | delta | f | g |
| --- | --- | --- | --- |
| s=1 | 1-delta' | f'-2*g' | f' |
| s=0 | delta'-1 | f' | 2*g'-e*f' |

After reconstructing the predecessor, recompute its predicates and XOR-clear
the two history bits. Never erase them using the successor alone: `(0,3,2)`
and `(0,3,-1)` both map to `(1,3,1)` but have different parity records.
The inverse restores delta itself, not only `(f,g)`.

The scalar boundary values fit signed `n+1=257` bits. A signed add/subtract
numerator needs `n+2=258` bits. The emitted prototype conservatively retains
258-bit sign-extended banks throughout. Inductively `|delta_i| <= i+1`, so
11 signed bits cover all 741 steps and their padding. No empirical cutoff,
shrinking-width assumption, saturation, or truncation is used.

## Coefficient and payload maps

Use local payload names `(a,b)`; these are not Shor exponent registers.
Let `h(x) = (x_mod_p + (x_mod_p mod 2)*p)/2`, a canonical modular half.

| Branch | a' | b' | Inverse a | Inverse b |
| --- | --- | --- | --- | --- |
| s=1 | b | h(b-a) | a'-2*b' mod p | a' |
| s=0 | a | h(b+e*a) | a' | 2*b'-e*a' mod p |

Writing column vectors, the maps are `L_s=[[0,1],[-1/2,1/2]]` and
`L_e=[[1,0],[e/2,1/2]]`. Both have determinant `1/2`, hence are bijective
over the odd prime field. The integer matrices `M=2*L` have determinant 2.
With `(a,b)=(0,c)` the inductive invariants are
`z*a=c*f mod p`, `z*b=c*g mod p`, also when `c=0`.
At termination `(a,b)=(f_N*c/z,0)`. This is an unscaled modular representation;
no final uncharged `2^-N` multiplication is needed. A batched integer-matrix
variant would need its own explicitly charged scaling and matrix workspace.

## Full clean schedule

1. Initialize `f=p`, extend caller denominator into `g=z`, and set `delta=1`.
2. Run N value rounds, retaining the 2N quantum history qubits. Keep full
   terminal values and delta live. No history measurement or host routing.
3. DIV: initialize extra field bank `a=0`, with caller payload in `b=c`.
   Replay N coefficient maps in forward chronological order. Negate `a`
   modulo p controlled by the sign of terminal f. Swap the two field banks
   using emitted fixed SWAPs so output is in the original payload bank b.
   The extra bank a is now exactly zero.
4. MUL: after the same value walk, start `(a,b)=(0,c)`, swap a/b, apply the
   same terminal controlled sign normalization, then replay inverse
   coefficient maps in reverse chronological order. End at `(0,z*c)`.
5. Reverse all value rounds, restoring every predecessor and clearing each
   record. The resulting value state is exactly `(1,p,z)`.
6. Unload the public constants 1 and p, verify/free clean extension and scratch
   wires, and return denominator/payload on the original ABI wires.

The value work cancels on both sides of the coefficient sandwich; this makes
MUL the adjoint of DIV. No inverse-result register or separate multiply is
hidden in this construction. The coefficient replay costs themselves are
not free and have NOT yet been emitted in this deliverable.

## Lowered round

`ecdsafail-qip-safegcd-20260922/safegcd_probe/round.py` emits pure X/CX/CCX.
It computes both history predicates, conditionally negates delta, increments
delta, coherently swaps f/g, conditionally negates g, adds e*f with a cleaned
masked addend, and divides the known-even numerator by two. The last operation
is a fixed right rotation followed by a sign-extension CX, not a lossy shift.
MCX decomposition and every conditional swap are charged. Cuccaro MAJ/UMA
is adapted from the repository's measurement-free `arith/adder.rs` helper.

Scratch is a fixed 258-wire bank plus one carry, cleared after each round.
The inverse gate stream is literally the reversed emitted gate list and
clears history last, after recovering the old predicates. Since these gates
are phase-free permutations, there are no measurement or phase-repair branches.
Scalar `if` statements define expected answers only; they do not route the
emitted circuit. Unsupported bit patterns still undergo a gate permutation,
but arithmetic correctness is claimed only on the stated valid-state domain.

## Verification scope

`scalar-results.json` records exhaustive small-prime payload tests, local
signed states, coefficient bijections, all-741-step secp trajectories, exact
predecessor restoration, canonical residues, and DIV/MUL mutual inverses.
`round-results.json` in the sibling records emitted-gate simulation.
The original repository parser/simulator independently reads `.kmx` and
compares every output wire to scalar vectors, then runs the exact reversed
stream and checks every input, history and scratch wire plus phase.
Passing scalar or local-round tests is not evidence of full point-addition
correctness or a measured matched full baseline.
