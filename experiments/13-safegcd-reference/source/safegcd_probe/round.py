"""Isolated exact X/CX/CCX controller/value divstep. No payload lowering yet.

Cuccaro MAJ/UMA follows src/point_add/arith/adder.rs, without measurement.
All runtime decisions are wires. Generator branches depend only on widths.
"""

from collections import Counter
import hashlib
import json
from pathlib import Path
import random
import sys


class Round:
    def __init__(self, n, d):
        self.n, self.d, self.w = n, d, n + 2
        self.ops = []
        self.size = 0
        self.delta = self.alloc(d)
        self.f = self.alloc(self.w)
        self.g = self.alloc(self.w)
        self.e, self.s = self.alloc(2)
        self.temp = self.alloc(max(self.w, d + 1))
        self.carry = self.alloc(1)[0]
        self.emit()

    def alloc(self, n):
        q = list(range(self.size, self.size + n))
        self.size += n
        return q

    def gate(self, kind, *q):
        assert len(q) == len(set(q))
        self.ops.append((kind, *q))

    def mcx(self, controls, target):
        k = len(controls)
        if k <= 2:
            self.gate(("X", "CX", "CCX")[k], *controls, target)
            return
        a = self.temp[:k - 2]
        assert not set(a) & set(controls + [target])
        self.gate("CCX", controls[0], controls[1], a[0])
        for j in range(1, k - 2):
            self.gate("CCX", a[j - 1], controls[j + 1], a[j])
        self.gate("CCX", a[-1], controls[-1], target)
        for j in reversed(range(1, k - 2)):
            self.gate("CCX", a[j - 1], controls[j + 1], a[j])
        self.gate("CCX", controls[0], controls[1], a[0])

    def add(self, a, b):
        c = self.carry
        def maj(x, y, w):
            self.gate("CX", w, y)
            self.gate("CX", w, x)
            self.gate("CCX", x, y, w)
        def uma(x, y, w):
            self.gate("CCX", x, y, w)
            self.gate("CX", w, x)
            self.gate("CX", x, y)
        maj(c, b[0], a[0])
        for i in range(1, len(a) - 1):
            maj(a[i - 1], b[i], a[i])
        self.gate("CX", a[-2], b[-1])
        self.gate("CX", a[-1], b[-1])
        for i in reversed(range(1, len(a) - 1)):
            uma(a[i - 1], b[i], a[i])
        uma(c, b[0], a[0])

    def increment(self, reg, control=None):
        a = self.temp[:len(reg)]
        if control is None:
            self.gate("X", a[0])
        else:
            self.gate("CX", control, a[0])
        self.add(a, reg)
        if control is None:
            self.gate("X", a[0])
        else:
            self.gate("CX", control, a[0])

    def cneg(self, reg, control):
        for q in reg:
            self.gate("CX", control, q)
        self.increment(reg, control)

    def emit(self):
        self.gate("CX", self.g[0], self.e)
        # s = e & !sign(delta), with the delta==0 case toggled back off.
        self.gate("X", self.delta[-1])
        self.gate("CCX", self.e, self.delta[-1], self.s)
        for q in self.delta[:-1]:
            self.gate("X", q)
        self.mcx([self.e] + self.delta, self.s)
        for q in self.delta[:-1]:
            self.gate("X", q)
        self.gate("X", self.delta[-1])
        self.cneg(self.delta, self.s)
        self.increment(self.delta)
        for a, b in zip(self.f, self.g):
            self.gate("CX", b, a)
            self.gate("CCX", self.s, a, b)
            self.gate("CX", b, a)
        self.cneg(self.g, self.s)
        for a, t in zip(self.f, self.temp):
            self.gate("CCX", self.e, a, t)
        self.add(self.temp[:self.w], self.g)
        for a, t in zip(self.f, self.temp):
            self.gate("CCX", self.e, a, t)
        # Even signed numerator: rotate its known-zero LSB to the top, then
        # reconstruct the sign extension. Every operation is reversible.
        for i in range(self.w - 1):
            a, b = self.g[i:i + 2]
            self.gate("CX", a, b)
            self.gate("CX", b, a)
            self.gate("CX", a, b)
        self.gate("CX", self.g[-2], self.g[-1])

    def simulate(self, states):
        lanes = len(states)
        mask = (1 << lanes) - 1
        bits = [0] * self.size
        def put(reg, value, lane):
            for j, q in enumerate(reg):
                bits[q] |= ((value >> j) & 1) << lane
        for lane, (delta, f, g) in enumerate(states):
            put(self.delta, delta, lane)
            put(self.f, f, lane)
            put(self.g, g, lane)
        original = bits.copy()
        def run(ops):
            for op in ops:
                if op[0] == "X":
                    bits[op[1]] ^= mask
                elif op[0] == "CX":
                    bits[op[2]] ^= bits[op[1]]
                else:
                    bits[op[3]] ^= bits[op[1]] & bits[op[2]]
        def signed(reg, lane):
            u = sum(((bits[q] >> lane) & 1) << j for j, q in enumerate(reg))
            return u - (1 << len(reg)) if u >> (len(reg) - 1) else u
        run(self.ops)
        assert not any(bits[q] for q in self.temp + [self.carry])
        for lane, (delta, f, g) in enumerate(states):
            e, s = g & 1, int(delta > 0 and g & 1)
            expected = (1 - delta, g, (g - f) // 2) if s else (1 + delta, f, (g + e * f) // 2)
            got = tuple(signed(reg, lane) for reg in (self.delta, self.f, self.g))
            assert got == expected, (states[lane], got, expected)
            assert ((bits[self.e] >> lane) & 1, (bits[self.s] >> lane) & 1) == (e, s)
        run(reversed(self.ops))
        assert bits == original, "inverse failed to restore data/history/scratch"


def main():
    small = Round(4, 6)
    cases = [(d, f, g) for d in range(-8, 9)
             for f in range(-15, 16, 2) for g in range(-15, 16)]
    small.simulate(cases)
    big = Round(256, 11)
    rng = random.Random(20260922)
    p = 2**256 - 2**32 - 977
    cases256 = [(d, f, g) for d in (-741, -1, 0, 1, 741)
                for f in (1, -1, p, -p) for g in (0, 1, -1, p, -p)]
    cases256 += [(rng.randrange(-741, 742), rng.randrange(-p, p) | 1,
                  rng.randrange(-p, p)) for _ in range(1024)]
    big.simulate(cases256)
    # Verify chained rounds and every intermediate scalar state through the
    # same physical circuit, including padded states after convergence.
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] /
        "research/qip-oral-20260922/safegcd"))
    from scalar import Value, forward, iterations
    trajectory = []
    for z in [1, 2, p - 1] + [rng.randrange(1, p) for _ in range(29)]:
        v = Value(1, p, z)
        for _ in range(iterations(256)):
            trajectory.append((v.delta, v.f, v.g))
            v, _ = forward(v)
    for offset in range(0, len(trajectory), 512):
        big.simulate(trajectory[offset:offset + 512])
    root = Path(__file__).resolve().parent
    def export(circuit, cases, prefix):
        (root / (prefix + ".kmx")).write_text("\n".join(
            op[0] + " " + " ".join("q" + str(q) for q in op[1:])
            for op in circuit.ops) + "\n")
        def encode(values, record):
            bits = ["0"] * circuit.size
            for reg, value in zip((circuit.delta, circuit.f, circuit.g), values):
                for j, q in enumerate(reg):
                    bits[q] = str((value >> j) & 1)
            bits[circuit.e], bits[circuit.s] = map(str, record)
            return "".join(bits)
        with (root / (prefix + "-vectors.txt")).open("w") as stream:
            for delta, f, g in cases:
                new, record = forward(Value(delta, f, g))
                stream.write(encode((delta, f, g), (0, 0)) + " " +
                             encode((new.delta, new.f, new.g), record) + "\n")
    export(small, cases, "round-small")
    export(big, cases256 + trajectory, "round-256")
    out = root / "round-256.json"
    out.write_text(json.dumps({"registers": {"delta": big.delta, "f": big.f,
        "g": big.g, "parity": big.e, "swap": big.s, "scratch": big.temp + [big.carry]},
        "ops": big.ops}, separators=(",", ":")) + "\n")
    counts = dict(Counter(op[0] for op in big.ops))
    report = {"status": "PASS", "scope": "one controller/value round only; no coefficient gates or PA",
              "width_n": 256, "signed_value_wires_each": big.w, "delta_wires": 11,
              "peak_qubits_including_2_history_bits": big.size,
              "clean_scratch_wires": len(big.temp) + 1,
              "forward_gate_counts": counts, "inverse_gate_counts": counts,
              "small_exhaustive_states": len(cases), "secp_local_states": len(cases256),
              "secp_trajectory_states": len(trajectory), "phase": "X/CX/CCX only: exact phase-free permutation",
              "classical_routing": False, "output_sha256": hashlib.sha256(out.read_bytes()).hexdigest(),
              "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    (root / "round-results.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
