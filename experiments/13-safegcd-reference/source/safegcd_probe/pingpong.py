"""Primitive-matched full-width ping-pong reference, CONDITIONAL round budget.

Same canonical payload helpers, Cuccaro arithmetic and fixed wire accounting
as full.py. No shrinking schedule or half-size seed special cases.
"""
import argparse
import hashlib
import json
from pathlib import Path
import random

from full import Full, SECP256K1_P


class PingPong(Full):
    def __init__(self, p, rounds):
        self.p, self.n, self.rounds = p, p.bit_length(), rounds
        self.w, self.d = self.n + 2, 0
        self.ops, self.size = [], 0
        self.z = self.alloc(self.n)
        self.b = self.alloc(self.n)
        self.f = self.alloc(self.w)
        self.g = self.z + self.alloc(2)
        self.a = self.alloc(self.n)
        self.history = self.alloc(rounds)
        self.lift = self.alloc(1)[0]
        self.e, self.s = self.lift, self.history[0]
        self.temp = self.alloc(self.w)
        self.carry = self.alloc(1)[0]
        self.mask = []  # No parity-controlled addend in the ping-pong recurrence.
        self.cmp = self.alloc(self.n + 2)
        (self.pad, self.source_high, self.target_high, self.flag,
         self.zero, self.active) = self.alloc(6)
        self.value_ops = [self.capture(lambda j=j: self.value_round(j)) for j in (0, 1)]
        self.coeff_ops = [self.capture(lambda j=j: self.coefficient_round(j)) for j in (0, 1)]
        self.endpoint_ops = self.capture(self.endpoint)
        self.init_ops = self.capture(self.initialize)

    def initialize(self):
        for j, q in enumerate(self.f):
            if (self.p >> j) & 1:
                self.gate("X", q)
        self.gate("X", self.lift)
        self.gate("CX", self.g[0], self.lift)
        self.reverse(lambda: self.const_add(self.g, self.p, self.lift))

    def value_round(self, parity):
        source, target = (self.f, self.g) if parity == 0 else (self.g, self.f)
        self.gate("CX", target[1], self.s)
        self.gate("CX", source[1], self.s)
        for q in target:
            self.gate("CX", self.s, q)
        self.add(source, target)
        for q in target:
            self.gate("CX", self.s, q)
        for j in range(self.w - 1):
            self.swap([target[j]], [target[j+1]])
        self.gate("CX", target[-2], target[-1])

    def coefficient_round(self, parity):
        source, target = (self.a, self.b) if parity == 0 else (self.b, self.a)
        self.negate(self.s, target)
        self.mod_add(source, target)
        self.negate(self.s, target)
        self.halve(target)

    def endpoint(self):
        self.negate(self.f[-1], self.a)
        self.negate(self.g[-1], self.b)
        for a, b in zip(self.a, self.b):
            self.gate("CX", b, a)

    def mapped(self, ops, j, reverse=False):
        sign = self.history[j]
        for op in reversed(ops) if reverse else ops:
            yield (op[0], *(sign if q == self.s else q for q in op[1:]))

    def blocks(self, multiply=False):
        yield "setup", iter(self.init_ops)
        for j in range(self.rounds):
            yield "value_forward", self.mapped(self.value_ops[j % 2], j)
        if multiply:
            yield "endpoint", reversed(self.endpoint_ops)
            for j in reversed(range(self.rounds)):
                yield "coefficient_inverse", self.mapped(self.coeff_ops[j % 2], j, True)
        else:
            for j in range(self.rounds):
                yield "coefficient_forward", self.mapped(self.coeff_ops[j % 2], j)
            yield "endpoint", iter(self.endpoint_ops)
        for j in reversed(range(self.rounds)):
            yield "value_inverse", self.mapped(self.value_ops[j % 2], j, True)
        yield "teardown", reversed(self.init_ops)

    def convergence(self, z):
        f, g = self.p, z if z & 1 else z - self.p
        for j in range(self.rounds):
            if abs(f) == abs(g) == 1:
                return j
            source, target = (f, g) if j % 2 == 0 else (g, f)
            sign = ((source >> 1) ^ (target >> 1)) & 1
            out = (target + (1 - 2 * sign) * source) // 2
            assert out & 1
            if j % 2 == 0:
                g = out
            else:
                f = out
        assert abs(f) == abs(g) == 1, ("budget insufficient", z, f, g)
        return self.rounds


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--prime", type=int, default=SECP256K1_P)
    parser.add_argument("--rounds", type=int)
    parser.add_argument("--allow-insufficient", action="store_true", help="emit a failing fixed horizon for diagnostic comparison")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    n = args.prime.bit_length()
    rounds = args.rounds or (1536 if n == 256 else 8 * n + 16)
    c = PingPong(args.prime, rounds)
    p = args.prime
    if p < 128:
        cases = [(z, x) for z in range(1, p) for x in range(p)]
    else:
        rng = random.Random(202609221350)
        cases = [(z, x) for z in (1, 2, 3, 0xd3, 1 << 255, p-1, p-2, (p+1)//2)
                 for x in (0, 1, 2, p-1, p-2)]
        cases += [(rng.randrange(1, p), rng.randrange(p)) for _ in range(88)]
    convergence = {}
    for z, _ in cases:
        try:
            convergence[str(z)] = c.convergence(z)
        except AssertionError:
            if not args.allow_insufficient:
                raise
            convergence[str(z)] = None
    args.output.mkdir(exist_ok=True, parents=True)
    report = c.emit_file(args.output / "div.kmx")
    c.fixtures(args.output / "div-vectors.txt", cases)
    c.fixtures(args.output / "mul-vectors.txt", cases, True)
    report.update({"label": "unoptimized primitive-matched full-width ping-pong",
                   "prime": str(p), "rounds": rounds, "cases_each_direction": len(cases),
                   "convergence_rounds": convergence, "max_convergence_observed": max(v for v in convergence.values() if v is not None),
                   "known_insufficient_inputs": [z for z, v in convergence.items() if v is None],
                   "universal_256_round_bound_proved": False,
                   "budget_status": "CONDITIONAL at n256; exhaustive input coverage only for enumerated small primes",
                   "same_payload_primitive_implementation": "full.py Full.negate/mod_add/halve",
                   "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()})
    (args.output / "emission.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k != "convergence_rounds"}, indent=2))


if __name__ == "__main__":
    main()
