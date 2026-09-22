"""Unoptimized, canonical, fully coherent safegcd DIV/MUL gate emitter.

Canonical contracts and reduction identities follow the frozen experiment 09
canonical_replay.rs. Lowering is measurement-free Cuccaro, not its fast HMR
implementation. Full streams are emitted, never priced from scalar operations.
"""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import random
import sys

from round import Round

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "research/qip-oral-20260922/safegcd"))
from scalar import iterations, SECP256K1_P


class Full(Round):
    def __init__(self, p):
        self.p, self.n = p, p.bit_length()
        self.rounds = iterations(self.n)
        self.d = 1 + (self.rounds + 1).bit_length()
        self.w = self.n + 2
        self.ops, self.size = [], 0
        self.z = self.alloc(self.n)
        self.b = self.alloc(self.n)
        self.delta = self.alloc(self.d)
        self.f = self.alloc(self.w)
        self.g = self.z + self.alloc(2)
        self.a = self.alloc(self.n)
        self.history = self.alloc(2 * self.rounds)
        self.e, self.s = self.history[:2]
        self.temp = self.alloc(max(self.w, self.d + 1))
        self.carry = self.alloc(1)[0]
        self.mask = self.alloc(self.n)
        self.cmp = self.alloc(self.n + 2)
        (self.pad, self.source_high, self.target_high, self.flag,
         self.zero, self.active) = self.alloc(6)
        self.value_ops = self.capture(lambda: Round.emit(self))
        self.coeff_ops = self.capture(self.coefficient)
        self.endpoint_ops = self.capture(self.endpoint)
        self.init_ops = self.capture(self.initialize)

    def capture(self, emit):
        old, self.ops = self.ops, []
        emit()
        result, self.ops = self.ops, old
        return result

    def reverse(self, emit):
        self.ops.extend(reversed(self.capture(emit)))

    def swap(self, a, b, control=None):
        for x, y in zip(a, b):
            self.gate("CX", y, x)
            self.gate("CX", x, y) if control is None else self.gate("CCX", control, x, y)
            self.gate("CX", y, x)

    def const_add(self, target, value, control=None):
        a = self.temp[:len(target)]
        def load():
            for j, q in enumerate(a):
                if (value >> j) & 1:
                    self.gate("X", q) if control is None else self.gate("CX", control, q)
        load()
        self.add(a, target)
        load()

    def lt(self, a, b, out):
        """Toggle out by a<b; clean reversible widened subtract/unsubtract."""
        assert len(a) == len(b)
        c = self.cmp[:len(a) + 1]
        for x, y in zip(a, c):
            self.gate("CX", x, y)
        self.reverse(lambda: self.add(b + [self.pad], c))
        self.gate("CX", c[-1], out)
        self.add(b + [self.pad], c)
        for x, y in zip(a, c):
            self.gate("CX", x, y)

    def eqzero(self, reg, out):
        for q in reg:
            self.gate("X", q)
        self.mcx(reg, out)
        for q in reg:
            self.gate("X", q)

    def negate(self, control, reg):
        self.eqzero(reg, self.zero)
        self.gate("X", self.zero)
        self.gate("CCX", control, self.zero, self.active)
        for q in reg:
            self.gate("CX", self.active, q)
        correction = (1 << self.n) - 1 - self.p
        self.reverse(lambda: self.const_add(reg, correction, self.active))
        self.gate("CCX", control, self.zero, self.active)
        self.gate("X", self.zero)
        self.eqzero(reg, self.zero)

    def mod_add(self, source, target):
        t, s = target + [self.target_high], source + [self.source_high]
        self.add(s, t)
        correction = (1 << self.n) - self.p
        self.const_add(t, correction)
        self.gate("CX", self.target_high, self.flag)
        self.gate("X", self.flag)
        self.reverse(lambda: self.const_add(t, correction, self.flag))
        self.gate("X", self.flag)
        self.gate("CX", self.flag, self.target_high)
        self.lt(target, source, self.flag)

    def controlled_mod_add(self, control, source, target):
        for a, t in zip(source, self.mask):
            self.gate("CCX", control, a, t)
        self.mod_add(self.mask, target)
        for a, t in zip(source, self.mask):
            self.gate("CCX", control, a, t)

    def halve(self, target):
        wide = target + [self.target_high]
        self.gate("CX", target[0], self.flag)
        self.const_add(wide, self.p, self.flag)
        for i in range(self.n):
            self.swap([wide[i]], [wide[i + 1]])
        threshold = (self.p + 1) // 2
        reg = self.temp[:self.n]
        for j, q in enumerate(reg):
            if (threshold >> j) & 1:
                self.gate("X", q)
        self.lt(target, reg, self.flag)
        self.gate("X", self.flag)
        for j, q in enumerate(reg):
            if (threshold >> j) & 1:
                self.gate("X", q)

    def coefficient(self):
        self.swap(self.a, self.b, self.s)
        self.negate(self.s, self.b)
        self.controlled_mod_add(self.e, self.a, self.b)
        self.halve(self.b)

    def endpoint(self):
        self.negate(self.f[-1], self.a)
        self.swap(self.a, self.b)

    def initialize(self):
        self.gate("X", self.delta[0])
        for j, q in enumerate(self.f):
            if (self.p >> j) & 1:
                self.gate("X", q)

    def mapped(self, ops, j, reverse=False):
        e, s = self.history[2*j:2*j+2]
        for op in reversed(ops) if reverse else ops:
            yield (op[0], *(e if q == self.e else s if q == self.s else q for q in op[1:]))

    def blocks(self, multiply=False):
        yield "setup", iter(self.init_ops)
        for j in range(self.rounds):
            yield "value_forward", self.mapped(self.value_ops, j)
        if multiply:
            yield "endpoint", reversed(self.endpoint_ops)
            for j in reversed(range(self.rounds)):
                yield "coefficient_inverse", self.mapped(self.coeff_ops, j, True)
        else:
            for j in range(self.rounds):
                yield "coefficient_forward", self.mapped(self.coeff_ops, j)
            yield "endpoint", iter(self.endpoint_ops)
        for j in reversed(range(self.rounds)):
            yield "value_inverse", self.mapped(self.value_ops, j, True)
        yield "teardown", reversed(self.init_ops)

    def emit_file(self, path):
        digest, counts, phases = hashlib.sha256(), Counter(), {}
        max_wire = -1
        with path.open("wb") as stream:
            for phase, ops in self.blocks():
                phase_counts = phases.setdefault(phase, Counter())
                lines = []
                for op in ops:
                    counts[op[0]] += 1
                    phase_counts[op[0]] += 1
                    max_wire = max(max_wire, *op[1:])
                    lines.append(op[0] + " " + " ".join("q" + str(q) for q in op[1:]) + "\n")
                data = "".join(lines).encode()
                stream.write(data)
                digest.update(data)
        assert max_wire + 1 == self.size
        return {"Q_static_allocated": self.size, "static_T": counts["CCX"],
                "gate_counts": dict(counts), "phase_gate_counts": phases,
                "sha256": digest.hexdigest(), "bytes": path.stat().st_size}

    def fixtures(self, path, cases, multiply=False):
        def encode(z, c):
            bits = ["0"] * self.size
            for reg, value in ((self.z, z), (self.b, c)):
                for j, q in enumerate(reg):
                    bits[q] = str((value >> j) & 1)
            return "".join(bits)
        with path.open("w") as stream:
            for z, c in cases:
                expected = z * c % self.p if multiply else pow(z, -1, self.p) * c % self.p
                stream.write(encode(z, c) + " " + encode(z, expected) + "\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--prime", type=int, default=SECP256K1_P)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    circuit = Full(args.prime)
    report = circuit.emit_file(args.output / "div.kmx")
    if args.prime < 128:
        cases = [(z, c) for z in range(1, args.prime) for c in range(args.prime)]
    else:
        rng = random.Random(202609221350)
        p = args.prime
        cases = [(z, c) for z in (1, 2, 3, p-1, p-2, (p+1)//2)
                 for c in (0, 1, 2, p-1, p-2)]
        cases += [(rng.randrange(1, p), rng.randrange(p)) for _ in range(98)]
    circuit.fixtures(args.output / "div-vectors.txt", cases)
    circuit.fixtures(args.output / "mul-vectors.txt", cases, True)
    report.update({"label": "unoptimized canonical coherent safegcd DIV/MUL reference",
                   "prime": str(args.prime), "n": circuit.n, "rounds": circuit.rounds,
                   "cases_each_direction": len(cases),
                   "multiply_stream": "exact reverse of div.kmx",
                   "denominator_wires": circuit.z, "payload_wires": circuit.b,
                   "coefficient_lowering": "frozen canonical contracts; measurement-free Cuccaro",
                   "full_point_addition": False,
                   "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()})
    (args.output / "emission.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k not in ("denominator_wires", "payload_wires")}, indent=2))


if __name__ == "__main__":
    main()
