"""Independent Boolean/phase gate transcriptions, not emitted-Rust validation.

Reads frozen source only for provenance. Writes one result receipt beside this
script. Uses no third-party packages and does not import project modules.
"""

import hashlib
import itertools
import json
import platform
import random
from datetime import datetime, timezone
from pathlib import Path


HERE = Path(__file__).resolve().parent
WORKSPACE = HERE.parents[2]
SOURCE = WORKSPACE / "ecdsafail-qip-oral-repairs-20260922"
FREEZE = HERE.parent / "fresh-zero-mask-100k/freeze.json"


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_freeze():
    freeze = json.loads(FREEZE.read_text())
    observed = {name: sha256(SOURCE / name) for name in freeze["source"]}
    mismatches = [name for name, digest in observed.items()
                  if digest != freeze["source"][name]]
    assert not mismatches, ("Frozen source differs", mismatches)
    return observed


class PhaseSimulator:
    """Basis bits plus the exact sign from specified X-basis outcomes."""

    def __init__(self, seed):
        self.q = []
        self.phase = 0
        self.rng = random.Random(seed)
        self.live = 0
        self.peak = 0
        self.toffoli = 0

    def alloc(self, value=0):
        self.q.append(value)
        self.live += 1
        self.peak = max(self.peak, self.live)
        return len(self.q) - 1

    def free(self, q):
        assert self.q[q] == 0, ("Dirty scratch before release", q)
        self.live -= 1

    def x(self, q):
        self.q[q] ^= 1

    def cx(self, a, b):
        self.q[b] ^= self.q[a]

    def and_clean(self, a, b):
        self.toffoli += 1
        return self.alloc(self.q[a] & self.q[b])

    def and_uncompute(self, out, a, b):
        measurement = self.rng.randrange(2)
        self.phase ^= measurement * self.q[out]
        self.q[out] = 0
        self.phase ^= measurement * (self.q[a] & self.q[b])
        self.free(out)


def and_into(sim, controls, output):
    assert controls
    if len(controls) == 1:
        sim.cx(controls[0], output)
        return
    chain = [sim.and_clean(controls[0], controls[1])]
    for q in controls[2:]:
        chain.append(sim.and_clean(chain[-1], q))
    sim.cx(chain[-1], output)
    for i in range(len(chain) - 1, 0, -1):
        sim.and_uncompute(chain[i], chain[i - 1], controls[i + 1])
    sim.and_uncompute(chain[0], controls[0], controls[1])


def zero_into_blocks(sim, value, output):
    flags = [sim.alloc() for _ in range((len(value) + 31) // 32)]
    for q in value:
        sim.x(q)
    chunks = [value[i:i + 32] for i in range(0, len(value), 32)]
    for chunk, flag in zip(chunks, flags):
        and_into(sim, chunk, flag)
    and_into(sim, flags, output)
    for chunk, flag in reversed(list(zip(chunks, flags))):
        and_into(sim, chunk, flag)
    for q in value:
        sim.x(q)
    for flag in flags:
        sim.free(flag)


def check_zero_helper():
    per_width = {}
    for n in (1, 2, 31, 32, 33, 64, 255, 256):
        values = sorted(set([0, (1 << n) - 1] + [1 << i for i in range(n)]))
        count = 0
        for value in values:
            for initial_output in (0, 1):
                for seed in range(4):
                    sim = PhaseSimulator(seed)
                    qs = [sim.alloc((value >> i) & 1) for i in range(n)]
                    output = sim.alloc(initial_output)
                    zero_into_blocks(sim, qs, output)
                    assert sum(sim.q[q] << i for i, q in enumerate(qs)) == value
                    assert sim.q[output] == initial_output ^ int(value == 0)
                    assert sim.phase == 0 and sim.live == n + 1
                    if n == 256:
                        assert sim.peak - (n + 1) == 39
                        assert sim.toffoli == 503
                    count += 1
        per_width[str(n)] = count
    assert sum(per_width.values()) == 5512
    return {
        "cases": sum(per_width.values()),
        "cases_by_width": per_width,
        "values": "zero, all ones, and each single-set-bit word; deduplicated",
        "initial_output_bits": [0, 1],
        "measurement_seeds": [0, 1, 2, 3],
        "measurement_coverage": "seeded outcomes, not exhaustive branches",
        "n256_temporary_qubits_excluding_input_and_output": 39,
        "n256_ccx_per_zero_test": 503,
        "checks": ["input restored", "output XOR zero predicate", "zero phase",
                   "every released scratch bit zero", "live workspace restored"],
    }


def check_comparator_case(n, a, z, cin, measurements):
    # Transcribes compare.rs forward/inverse with targets=[], outer phase bit=1.
    # The aliased CZ(u[n-1],u[n-1]) is Z in the source builder.
    u = [(z >> i) & 1 for i in range(n)]
    v = [(a >> i) & 1 for i in range(n)]
    carry_in = cin
    carries = [0] * n
    phase = 0
    u = [bit ^ 1 for bit in u]
    v[0] ^= u[0]
    carry_in ^= u[0]
    carries[0] ^= carry_in & v[0]
    u[0] ^= carries[0]
    for i in range(1, n):
        v[i] ^= u[i]
        u[i - 1] ^= u[i]
        carries[i] ^= u[i - 1] & v[i]
        u[i] ^= carries[i]
    phase ^= u[-1]
    for i in range(n - 1, 0, -1):
        u[i] ^= carries[i]
        phase ^= measurements[i] * carries[i]
        carries[i] = 0
        phase ^= measurements[i] * (u[i - 1] & v[i])
        u[i - 1] ^= u[i]
        v[i] ^= u[i]
    u[0] ^= carries[0]
    phase ^= measurements[0] * carries[0]
    carries[0] = 0
    phase ^= measurements[0] * (carry_in & v[0])
    carry_in ^= u[0]
    v[0] ^= u[0]
    u = [bit ^ 1 for bit in u]
    assert sum(bit << i for i, bit in enumerate(u)) == z
    assert sum(bit << i for i, bit in enumerate(v)) == a
    assert carry_in == cin and not any(carries)
    assert phase == int(z < a or (cin and z == a)), (n, a, z, cin, measurements)


def check_comparator():
    per_width = {}
    for n in range(1, 6):
        count = 0
        for a, z, cin in itertools.product(range(1 << n), range(1 << n), (0, 1)):
            for measurements in itertools.product((0, 1), repeat=n):
                check_comparator_case(n, a, z, cin, measurements)
                count += 1
        per_width[str(n)] = count
    assert sum(per_width.values()) == 74896
    rng = random.Random(20260922)
    large_count = 0
    for n in (85, 86):
        for index in range(512):
            a = rng.getrandbits(n)
            z = a if index % 3 == 0 else rng.getrandbits(n)
            cin = rng.randrange(2)
            measurements = [rng.randrange(2) for _ in range(n)]
            check_comparator_case(n, a, z, cin, measurements)
            large_count += 1
    assert large_count == 1024
    return {
        "exhaustive_cases": sum(per_width.values()),
        "exhaustive_cases_by_width": per_width,
        "actual_width_cases": large_count,
        "actual_widths": [85, 86],
        "cases_per_actual_width": 512,
        "actual_width_seed": 20260922,
        "actual_width_equality_sampling": "z=a on every third iteration",
        "outer_phase_condition": "1; condition 0 skips the helper gates",
        "expected_phase_exponent": "[z<a] OR (cin AND [z=a])",
        "restored": ["u", "v", "cin", "clean scratch"],
        "scope": "exhaustive measurement assignments only at widths 1 through 5",
    }


def check_schedule():
    p = (1 << 256) - (1 << 32) - 977
    expected = {1: (512, 177), 3: (1135, 171), 1 << 255: (1239, 80)}
    results = []
    for denominator, (expected_rounds, expected_width_round) in expected.items():
        u, v = p, denominator
        first_width_failure = None
        convergence = None
        for k in range(2000):
            width = min(259, max(8,
                276 - 17 * k // 100 if k < 40 else
                270 - 33 * (k - 40) // 100 if k < 304 else
                183 - 40 * (k - 304) // 100))
            fits = lambda value: -(1 << (width - 1)) <= value < (1 << (width - 1))
            if first_width_failure is None and (not fits(u) or not fits(v)):
                first_width_failure = (k, "input")
            if k == 0:
                v = (denominator // 2 - p + ((denominator >> 1) & 1) * p
                     + (denominator & 1) * ((p + 1) // 2))
            else:
                source, target = (u, v) if k % 2 == 0 else (v, u)
                sign = ((source >> 1) ^ (target >> 1)) & 1
                total = target + (-source if sign else source)
                if first_width_failure is None and not fits(total):
                    first_width_failure = (k, "sum")
                if k % 2 == 0:
                    v = total // 2
                else:
                    u = total // 2
            if abs(u) == abs(v) == 1:
                convergence = k + 1
                break
        assert convergence == expected_rounds
        assert first_width_failure == (expected_width_round, "sum")
        results.append({"denominator": str(denominator), "transitions": convergence,
                        "first_width_failure_zero_based": list(first_width_failure)})
    return results


def main():
    if not __debug__:
        raise RuntimeError("Do not disable assertions with python -O")
    source_hashes = verify_freeze()
    results = {
        "scope": __doc__,
        "zero_helper": check_zero_helper(),
        "comparator": check_comparator(),
        "exact_integer_schedule": check_schedule(),
    }
    assert verify_freeze() == source_hashes
    results["provenance"] = {
        "run_utc": datetime.now(timezone.utc).isoformat(),
        "python_version": platform.python_version(),
        "script_sha256": sha256(Path(__file__).resolve()),
        "freeze_sha256": sha256(FREEZE),
        "source_directory": SOURCE.name,
        "source_files_checked_before_and_after": len(source_hashes),
        "source_hashes": source_hashes,
        "stream_validated": False,
        "fresh_100k_results_read": False,
    }
    results["status"] = "PASS"
    output = HERE / "followup-transcription-results.json"
    output.write_text(json.dumps(results, indent=2) + "\n")
    print(json.dumps({
        "status": results["status"],
        "zero_helper_cases": results["zero_helper"]["cases"],
        "comparator_exhaustive_cases": results["comparator"]["exhaustive_cases"],
        "comparator_actual_width_cases": results["comparator"]["actual_width_cases"],
        "source_files_verified": len(source_hashes),
        "receipt": str(output),
    }, indent=2))


if __name__ == "__main__":
    main()
