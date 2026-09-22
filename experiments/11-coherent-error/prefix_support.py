"""Exact scalar-prefix counts and independent small elliptic-curve checks.

The production-size counts concern specified model schedules only. They do not
test the ECDSA.Fail operation stream or classify its complete arithmetic bad set.
No third-party dependencies. Run directly to print JSON.
"""

from collections import Counter
from fractions import Fraction
import itertools
import json


FIELD = 2**256 - 2**32 - 977
ORDER = int("FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141", 16)
GENERATOR = (
    int("79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798", 16),
    int("483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8", 16),
)
BETA = int("7AE96A2B657C07106E64479EAC3434E99CF0497512F58995C1396C28719501EE", 16)
# The scalar endomorphism is zeta, not lambda (reserved for the affine slope).
ZETA = int("5363AD4CC05C30E0A5261C028812645A122E22EA20816678DF02967C1B23BD72", 16)


def ec_add(left, right, field):
    if left is None:
        return right
    if right is None:
        return left
    x, y = left
    a, b = right
    if x == a and (y + b) % field == 0:
        return None
    slope = ((3 * x * x) * pow(2 * y, -1, field) if left == right
             else (y - b) * pow(x - a, -1, field)) % field
    out_x = (slope * slope - x - a) % field
    return out_x, (slope * (a - out_x) - b) % field


def ec_mul(scalar, point, field):
    if scalar < 0:
        return ec_mul(-scalar, (point[0], -point[1] % field), field)
    result = None
    while scalar:
        if scalar & 1:
            result = ec_add(result, point, field)
        point = ec_add(point, point, field)
        scalar >>= 1
    return result


def rational(value):
    return {"numerator": value.numerator, "denominator": value.denominator, "decimal": float(value)}


def geometric_classes(scalar, addend, order, zeta):
    if addend == 0:
        return set()
    classes = set()
    for label, target in [
        ("R_identity", 0), ("R_equals_A", addend),
        ("R_equals_minus_A", -addend % order), ("R_equals_minus_2A", -2 * addend % order),
        ("zero_slope_1", zeta * addend % order),
        ("zero_slope_2", zeta * zeta * addend % order),
    ]:
        if scalar == target:
            classes.add(label)
    return classes


def secp_endomorphism_checks():
    assert pow(BETA, 3, FIELD) == 1 and BETA != 1
    assert (ZETA * ZETA + ZETA + 1) % ORDER == 0 and ZETA != 1
    assert (GENERATOR[1] ** 2 - GENERATOR[0] ** 3 - 7) % FIELD == 0
    assert ec_mul(ORDER, GENERATOR, FIELD) is None
    witnesses = []
    for exponent in [1, 2]:
        point = (pow(BETA, exponent, FIELD) * GENERATOR[0] % FIELD, GENERATOR[1])
        assert ec_mul(pow(ZETA, exponent, ORDER), GENERATOR, FIELD) == point
        out = ec_add(point, GENERATOR, FIELD)
        assert point[0] != GENERATOR[0] and out[0] != GENERATOR[0]
        assert point not in [GENERATOR, ec_mul(-1, GENERATOR, FIELD), ec_mul(-2, GENERATOR, FIELD)]
        witnesses.append({"R": [hex(value) for value in point], "output": [hex(value) for value in out]})
    return {"status": "PASS", "witnesses_for_A_equals_G": witnesses}


def secp_ascending_g_prefixes():
    radix = 2**16
    rows = []
    for t in range(1, 16):
        support_size = radix**t
        assert support_size < ORDER
        counts = Counter()
        union_count = 0
        for address in range(1, radix):
            addend = address * support_size % ORDER
            targets = {
                "R_identity": 0,
                "R_equals_A": addend,
                "R_equals_minus_A": -addend % ORDER,
                "R_equals_minus_2A": -2 * addend % ORDER,
                "zero_slope_1": ZETA * addend % ORDER,
                "zero_slope_2": ZETA * ZETA * addend % ORDER,
            }
            hits = set()
            for label, scalar in targets.items():
                if scalar < support_size:
                    counts[label] += 1
                    hits.add(scalar)
            union_count += len(hits)
        # There is one (R=O, j=0) pair not covered by the nonidentity geometry.
        # Include it conservatively because that kernel case lacks a proof here.
        rows.append({
            "call_after_direct_initialization": t,
            "current_window_shift": 16 * t,
            "prefix_support_size": support_size,
            "uniform_on_group": False,
            "sample_space_size": support_size * radix,
            "geometric_pair_counts": dict(counts),
            "geometric_union_weight": rational(Fraction(union_count, support_size * radix)),
            "including_unproved_identity_identity_weight": rational(Fraction(union_count + 1, support_size * radix)),
        })
    assert rows[0]["geometric_pair_counts"] == {"R_identity": radix - 1}
    assert rows[0]["geometric_union_weight"]["numerator"] == radix - 1
    deficit = 2**256 - ORDER
    assert 0 < deficit < ORDER
    total_variation = Fraction(deficit * (ORDER - deficit), 2**256 * ORDER)
    return {
        "schedule": "unsigned disjoint windows, G shifts 0,16,...,240, direct initialization from shift 0, no additive offset",
        "scope": "Geometry plus zero-slope set ONLY, not the complete arithmetic bad set",
        "rows": rows,
        "post_G_dyadic_bias": {
            "N": 2**256,
            "r": ORDER,
            "N_minus_r": deficit,
            "residue_multiplicities": "2 for 0 <= z < N-r, 1 otherwise",
            "total_variation_from_uniform": rational(total_variation),
            "maximum_atom": rational(Fraction(2, 2**256)),
            "at_most_six_points_per_nonidentity_address_bound": rational(Fraction(12, 2**256)),
        },
    }


def toy_curve_checks():
    field, order, generator, radix = 211, 199, (3, 33), 4
    points = [None]
    for _ in range(1, order):
        points.append(ec_add(points[-1], generator, field))
    assert len(set(points)) == order
    assert ec_add(points[-1], generator, field) is None
    all_affine = [(x, y) for x in range(field) for y in range(field)
                  if (y * y - x**3 - 7) % field == 0]
    assert set(all_affine) == set(points[1:])
    beta = next(value for value in range(2, field) if pow(value, 3, field) == 1)
    zeta = points.index((beta * generator[0] % field, generator[1]))
    # Cross-check the scalar bad-set formula against curve coordinates for ALL pairs.
    checked_pairs = 0
    for addend in range(1, order):
        affine_a = points[addend]
        for scalar in range(order):
            affine_r = points[scalar]
            output = ec_add(affine_r, affine_a, field)
            domain_bad = (affine_r is None or affine_r[0] == affine_a[0] or
                          output is None or output[0] == affine_a[0])
            zero_slope = (not domain_bad and affine_r[1] == affine_a[1])
            labels = geometric_classes(scalar, addend, order, zeta)
            assert domain_bad == bool(labels - {"zero_slope_1", "zero_slope_2"})
            assert zero_slope == bool(labels & {"zero_slope_1", "zero_slope_2"})
            checked_pairs += 1
    k = 7
    schedules = {
        "G_then_P_ascending": [1, 4, 16, k, 4 * k, 16 * k],
        "G_then_P_descending": [16, 4, 1, 16 * k, 4 * k, k],
        "interleaved": [1, k, 4, 4 * k, 16, 16 * k],
    }
    output_rows = {}
    for name, coefficients in schedules.items():
        distribution = Counter({0: 1})
        denomin = 1
        rows = []
        for position, coefficient in enumerate(coefficients):
            pair_count = sum(multiplicity for scalar, multiplicity in distribution.items()
                             for address in range(radix)
                             if geometric_classes(scalar, coefficient * address % order, order, zeta))
            # Independent full-prefix enumeration checks multiplicities, not just support.
            brute = Counter(sum(c * j for c, j in zip(coefficients[:position], digits)) % order
                            for digits in itertools.product(range(radix), repeat=position))
            assert brute == distribution
            rows.append({
                "window_position": position,
                "direct_initialization_not_arithmetic": position == 0,
                "prefix_paths": denomin,
                "prefix_support_size": len(distribution),
                "maximum_atom": rational(Fraction(max(distribution.values()), denomin)),
                "geometric_union_weight": rational(Fraction(pair_count, denomin * radix)),
            })
            updated = Counter()
            for scalar, multiplicity in distribution.items():
                for address in range(radix):
                    updated[(scalar + coefficient * address) % order] += multiplicity
            distribution, denomin = updated, denomin * radix
        output_rows[name] = rows
    assert output_rows["G_then_P_ascending"][1]["geometric_union_weight"] == rational(Fraction(3, 16))
    return {"p": field, "r": order, "G": generator, "zeta": zeta,
            "all_curve_pair_checks": checked_pairs, "schedules": output_rows}


def run():
    return {
        "status": "PASS",
        "secp256k1_endomorphism": secp_endomorphism_checks(),
        "secp256k1_prefixes": secp_ascending_g_prefixes(),
        "small_curve_exhaustive": toy_curve_checks(),
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
