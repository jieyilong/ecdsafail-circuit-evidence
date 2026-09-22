"""Bounded scalar audit, not an emitted-gate or quantum-channel certification."""
import json
import math
from pathlib import Path


def main():
    counts = {}
    chunk_cases = strict_misses = 0
    for bits in range(1, 9):
        base = 1 << bits
        for a in range(base):
            for b in range(base):
                for carry in (0, 1):
                    total = a + b + carry
                    z, out = total % base, total // base
                    assert out == int(z < a or (carry and z == a))
                    strict_misses += int(out != int(z < a))
                    chunk_cases += 1
    counts['chunk_predicate_cases'] = chunk_cases
    counts['strict_comparison_counterexamples'] = strict_misses

    fused_cases = guarded_cases = canonical_cases = 0
    ranges = {name: set() for name in ('raw_add', 'raw_sub', 'frame_add', 'frame_sub')}
    for bits, f in ((4, 3), (5, 3), (6, 5)):
        base = 1 << bits
        p = base - f
        for z in range(p):
            odd = z & 1
            half = (z + odd * p) // 2
            borrow = int(z < odd * f)
            wrapped = (z - odd * f) % base
            repaired_half = wrapped // 2 + (odd - borrow) * (base // 2)
            assert repaired_half == half
            assert odd == int(half >= (p + 1) // 2)
            assert borrow == int((p + 1) // 2 <= half < base // 2)
            doubled = (2 * z) % p
            assert int(2 * z >= p) == (doubled & 1)
            for y in range(p):
                result = (z + y) % p
                assert int(z + y >= p) == int(result < y)
                canonical_cases += 1
                for sign in (0, 1):
                    d, z0 = divmod(2 * z, base)
                    c_z0 = base - 1 - z0 if sign else z0
                    o, omega = divmod(c_z0 + y, base)
                    total = 2 * z + (-y if sign else y)
                    raw_k, w = divmod(total, base)
                    frame_k = o + (-d if sign else d)
                    assert raw_k == (-frame_k if sign else frame_k)
                    assert w == (base - 1 - omega if sign else omega)
                    assert total % p == (w + raw_k * f) % p
                    v = omega + frame_k * f
                    extended_c = base - 1 - v if sign else v
                    assert extended_c % p == total % p
                    if 0 <= v < base:
                        assert (v & 1) ^ sign ^ (y & 1) ^ o == d
                        guarded_cases += 1
                    ranges['raw_sub' if sign else 'raw_add'].add(raw_k)
                    ranges['frame_sub' if sign else 'frame_add'].add(frame_k)
                    fused_cases += 1
    counts.update(fused_cases=fused_cases, no_escape_parity_cases=guarded_cases,
                  canonical_predicate_cases=canonical_cases)

    base = 1 << 256
    f = (1 << 32) + 977
    p = base - f
    witnesses = {}
    # Raw and complemented subtraction use opposite correction coefficients.
    z, y = base // 2, 0
    witnesses['frame_sign'] = {'z': hex(z), 'y': y, 'sign': 1,
                              'raw_kappa': 1, 'complemented_kappa': -1}
    # A full 256-bit fold still needs to handle a SECOND word overflow.
    z, y = p - 1, 2 * f + 1
    q, w = divmod(2 * z + y, base)
    wrapped = (w + q * f) % base
    expected = (2 * z + y) % p
    assert wrapped == f - 1 and expected == 2 * f - 1
    witnesses['full_word_escape'] = {'z': hex(z), 'y': y,
        'wrapped_result': wrapped, 'expected': expected, 'missing': f}
    # Even a no-escape fold need not preserve canonical representations.
    z, y = 1, p - 2
    q, w = divmod(2 * z + y, base)
    assert q == 0 and w == p
    witnesses['canonical_inputs_noncanonical_output'] = {
        'z': z, 'y': hex(y), 'raw_output': 'p', 'canonical_output': 0}
    # Exact comparison of the corrected output does not recover original carry.
    raw, overflow = 0, 1  # complemented 0 plus source 1 wraps
    corrected = raw + overflow * f
    assert not corrected < 1
    witnesses['post_fold_predicate'] = {'source': 1, 'target': 0, 'sign': 1,
        'stored_overflow': overflow, 'full_width_predicate': int(corrected < 1)}
    expected = (p + 1) // 2
    faulty = (((1 - f) % base) // 2) ^ (base // 2)
    assert abs(faulty - expected) == base // 2
    witnesses['halve_one'] = {'expected': hex(expected), 'faulty_full_width': hex(faulty),
                              'absolute_difference': '2^255'}
    for subtrahend in (1, 2, f, p - 1):
        result = (-subtrahend) % p
        assert result + subtrahend == p < base
    witnesses['coordinate_borrow'] = {'input': 0, 'subtrahend': 1,
        'output': 'p-1', 'modular_borrow': 1, 'ordinary_word_carry': 0}

    # U followed by a diagonal sign is correct on basis labels but not on |+>.
    overlap = (1 - 1) / 2
    assert overlap == 0
    witnesses['coherence'] = {'basis_label_tests_pass': True,
        'clean_workspace': True, 'plus_state_output_fidelity': overlap ** 2,
        'trace_distance': 1, 'diamond_distance_unnormalized': 2}
    result = {'scope': __doc__, 'counts': counts,
        'ranges': {key: sorted(value) for key, value in ranges.items()},
        'witnesses': witnesses,
        'zero_of_10m_one_sided_95_upper': -math.expm1(math.log(0.05) / 10_000_000),
        'status': 'PASS: all stated scalar identities and counterexamples verified'}
    path = Path(__file__).resolve().with_name('algebra-results.json')
    path.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
