"""Small numerical checks, not certification of an emitted ECDSA.Fail circuit.

Requires NumPy. All matrices use system-major, environment-minor ordering.
Run directly to print JSON, or use run_checks.py for saved evidence.
"""

import json
import math

import numpy as np


TOL = 2e-7


def bound(epsilon):
    if not 0 <= epsilon <= 1:
        raise ValueError("Bad weight must lie in [0, 1]")
    return 2 * math.sqrt(epsilon * (1 - epsilon)) if epsilon <= 0.5 else 1.0


def ket_density(psi):
    return np.outer(psi, psi.conj())


def trace_distance(rho, sigma):
    delta = rho - sigma
    return float(np.abs(np.linalg.eigvalsh((delta + delta.conj().T) / 2)).sum() / 2)


def sqrt_psd(rho):
    eigenvalues, vectors = np.linalg.eigh((rho + rho.conj().T) / 2)
    assert eigenvalues.min() >= -1e-10
    return (vectors * np.sqrt(np.maximum(eigenvalues, 0))) @ vectors.conj().T


def purified_distance(rho, sigma):
    root = sqrt_psd(rho)
    eigenvalues = np.linalg.eigvalsh(root @ sigma @ root)
    fidelity = float(np.sqrt(np.maximum(eigenvalues, 0)).sum())
    return math.sqrt(max(0, 1 - min(1, fidelity) ** 2))


def pure_distance(psi, phi):
    return math.sqrt(max(0, 1 - min(1, abs(np.vdot(psi, phi))) ** 2))


def apply_channel(kraus, rho):
    return sum(op @ rho @ op.conj().T for op in kraus)


def random_complex(rng, shape):
    return rng.normal(size=shape) + 1j * rng.normal(size=shape)


def random_unitary(rng, dimension):
    vectors, _ = np.linalg.qr(random_complex(rng, (dimension, dimension)))
    return vectors


def trace_environment(psi, system_dim, environment_dim, reference_dim):
    tensor = psi.reshape(system_dim, environment_dim, reference_dim)
    matrix = tensor.transpose(0, 2, 1).reshape(system_dim * reference_dim, environment_dim)
    return matrix @ matrix.conj().T


def check_counterexamples():
    identity = np.eye(2)
    phase = np.diag([1.0, -1.0])
    plus = np.array([1.0, 1.0]) / math.sqrt(2)
    rho = ket_density(plus)
    random_phase = [identity / math.sqrt(2), phase / math.sqrt(2)]
    for basis in identity:
        basis_rho = ket_density(basis)
        assert np.allclose(phase @ basis_rho @ phase, basis_rho)
        assert np.allclose(apply_channel(random_phase, basis_rho), basis_rho)
    for op in random_phase:
        # Uniform probabilities for EVERY input, not just basis states.
        assert np.allclose(op.conj().T @ op, identity / 2)
    coherent_error = trace_distance(phase @ rho @ phase, rho)
    dephased = apply_channel(random_phase, rho)
    measurement_error = trace_distance(dephased, rho)
    measurement_purified = purified_distance(dephased, rho)
    assert abs(coherent_error - 1) < TOL
    assert abs(measurement_error - 0.5) < TOL
    assert abs(measurement_purified - math.sqrt(0.5)) < TOL
    return {
        "basis_output_success": 1.0,
        "Z_vs_identity_on_plus_trace_distance": coherent_error,
        "uniform_random_I_Z_trace_distance": measurement_error,
        "uniform_random_I_Z_purified_distance": measurement_purified,
        "uniform_branch_probabilities": [0.5, 0.5],
        "lesson": "Basis outputs AND input-independent probabilities do not imply common branch amplitudes.",
    }


def check_sharpness():
    rows = []
    for epsilon in [0, 1e-8, 1e-4, 0.01, 0.1, 0.25, 0.5, 0.6, 0.9, 1]:
        psi = np.array([math.sqrt(1 - epsilon), math.sqrt(epsilon), 0])
        if epsilon <= 0.5:
            implemented = np.diag([1.0, -1.0, 1.0])
        else:
            cosine = -(1 - epsilon) / epsilon
            sine = math.sqrt(1 - cosine * cosine)
            implemented = np.array([[1, 0, 0], [0, cosine, -sine], [0, sine, cosine]])
        assert np.allclose(implemented.T @ implemented, np.eye(3))
        assert np.allclose(implemented[:, 0], [1, 0, 0])
        error = trace_distance(ket_density(implemented @ psi), ket_density(psi))
        assert abs(error - bound(epsilon)) < TOL
        rows.append({"epsilon": epsilon, "trace_distance": error, "sharp_bound": bound(epsilon)})
    return rows


def check_random_stinespring(seed=20260922, trials=150):
    rng = np.random.default_rng(seed)
    dimension, good_dim, environment_dim, reference_dim = 4, 2, 3, 3
    maximum_isometry_residual = 0.0
    maximum_bound_violation = 0.0
    minimum_reduction_gain = 1.0
    for trial in range(trials):
        ideal = random_unitary(rng, dimension)
        environment = np.array([[1], [0], [0]])
        ideal_dilation = np.kron(ideal, environment)
        good = ideal_dilation[:, :good_dim]
        trial_bad = random_complex(rng, (dimension * environment_dim, dimension - good_dim))
        trial_bad -= good @ (good.conj().T @ trial_bad)
        bad, _ = np.linalg.qr(trial_bad)
        dilation = np.column_stack([good, bad])
        residual = float(np.linalg.norm(dilation.conj().T @ dilation - np.eye(dimension)))
        maximum_isometry_residual = max(maximum_isometry_residual, residual)
        assert residual < 1e-10
        epsilon = [0, 1e-6, 0.01, 0.1, 0.49, 0.5, 0.9, 1][trial % 8]
        vector = random_complex(rng, (dimension, reference_dim))
        vector[:good_dim] *= math.sqrt(1 - epsilon) / np.linalg.norm(vector[:good_dim])
        vector[good_dim:] *= math.sqrt(epsilon) / np.linalg.norm(vector[good_dim:])
        psi = vector.reshape(-1)
        actual_pure = np.kron(dilation, np.eye(reference_dim)) @ psi
        ideal_pure = np.kron(ideal_dilation, np.eye(reference_dim)) @ psi
        pure_error = pure_distance(actual_pure, ideal_pure)
        norm_error = float(np.linalg.norm(actual_pure - ideal_pure))
        actual_rho = trace_environment(actual_pure, dimension, environment_dim, reference_dim)
        ideal_rho = trace_environment(ideal_pure, dimension, environment_dim, reference_dim)
        reduced_d = trace_distance(actual_rho, ideal_rho)
        reduced_p = purified_distance(actual_rho, ideal_rho)
        assert pure_error <= bound(epsilon) + TOL
        assert norm_error <= 2 * math.sqrt(epsilon) + TOL
        assert reduced_d <= reduced_p + TOL
        assert reduced_p <= pure_error + TOL
        maximum_bound_violation = max(maximum_bound_violation, pure_error - bound(epsilon))
        minimum_reduction_gain = min(minimum_reduction_gain, pure_error - reduced_d)
    return {
        "seed": seed,
        "trials": trials,
        "input_dimension": dimension,
        "reference_dimension": reference_dim,
        "environment_dimension": environment_dim,
        "maximum_isometry_residual": maximum_isometry_residual,
        "maximum_bound_violation_within_numerical_tolerance": maximum_bound_violation,
        "minimum_purification_to_reduced_trace_distance_gain": minimum_reduction_gain,
    }


def check_qrom():
    address_dim, accumulator_dim, payload_dim = 4, 3, 4
    payload_words = [0, 1, 3, 2]
    addends = [0, 1, 2, 1]
    dimension = address_dim * accumulator_dim
    ideal = np.zeros((dimension, dimension))
    for address in range(address_dim):
        for accumulator in range(accumulator_dim):
            ideal[address * accumulator_dim + (accumulator + addends[address]) % accumulator_dim,
                  address * accumulator_dim + accumulator] = 1
    corrected, uncorrected = [], []
    split_phase_checks = 0
    for outcome in range(payload_dim):
        signs = [(-1) ** ((outcome & word).bit_count() % 2) for word in payload_words]
        before = ideal @ np.diag(np.repeat(signs, accumulator_dim)) / math.sqrt(payload_dim)
        correction = np.diag(np.repeat(signs, accumulator_dim))
        after = correction @ before
        assert np.allclose(after, ideal / math.sqrt(payload_dim))
        # For w=2, verify the low/high one-hot CZ construction on every address.
        for address in range(address_dim):
            sign = 1
            for row in range(address_dim):
                if signs[row] == -1 and (address & 1) == (row & 1) and (address >> 1) == (row >> 1):
                    sign *= -1
            assert sign == signs[address]
            split_phase_checks += 1
        corrected.append(after)
        uncorrected.append(before)
    assert np.allclose(sum(op.conj().T @ op for op in corrected), np.eye(dimension))
    assert np.allclose(sum(op.conj().T @ op for op in uncorrected), np.eye(dimension))
    psi = np.zeros(dimension)
    psi[::accumulator_dim] = 1 / math.sqrt(address_dim)
    ideal_rho = ket_density(ideal @ psi)
    corrected_error = trace_distance(apply_channel(corrected, ket_density(psi)), ideal_rho)
    omitted_error = trace_distance(apply_channel(uncorrected, ket_density(psi)), ideal_rho)
    assert corrected_error < TOL
    assert abs(omitted_error - 0.75) < TOL
    return {
        "system_dimension": dimension,
        "measurement_branches": payload_dim,
        "branch_factor": 0.5,
        "split_phase_checks": split_phase_checks,
        "corrected_trace_distance": corrected_error,
        "omitted_correction_trace_distance": omitted_error,
        "scope": "Restored-payload abstract lookup/use/unlookup, not emitted arithmetic.",
    }


def check_ideal_prefix_hybrid():
    theta, steps = 0.03, 5
    ideal = np.array([[math.cos(theta), -math.sin(theta)], [math.sin(theta), math.cos(theta)]])
    implemented = ideal @ np.diag([1.0, -1.0])
    sigma = np.array([1.0, 0.0])
    rho = sigma.copy()
    ideal_weights, actual_weights, local_errors = [], [], []
    for _ in range(steps):
        epsilon = float(abs(sigma[1]) ** 2)
        ideal_weights.append(epsilon)
        actual_weights.append(float(abs(rho[1]) ** 2))
        local_errors.append(pure_distance(implemented @ sigma, ideal @ sigma))
        assert local_errors[-1] <= bound(epsilon) + TOL
        sigma, rho = ideal @ sigma, implemented @ rho
    final_error = pure_distance(sigma, rho)
    certificate = min(1.0, sum(bound(value) for value in ideal_weights))
    assert final_error <= certificate + TOL
    assert not np.allclose(ideal_weights, actual_weights)
    # H_j = E^(m-j) U^j |0>, so each adjacent pair has an IDEAL prefix.
    start = np.array([1.0, 0.0])
    hybrids = [np.linalg.matrix_power(implemented, steps - j) @ np.linalg.matrix_power(ideal, j) @ start
               for j in range(steps + 1)]
    adjacent = [pure_distance(hybrids[j], hybrids[j + 1]) for j in range(steps)]
    assert np.allclose(adjacent, local_errors, atol=TOL)
    return {
        "steps": steps,
        "theta": theta,
        "ideal_prefix_bad_weights": ideal_weights,
        "implemented_prefix_bad_weights_NOT_used": actual_weights,
        "local_trace_distances": local_errors,
        "adjacent_hybrid_distances": adjacent,
        "final_trace_distance": final_error,
        "ideal_prefix_hybrid_bound": certificate,
    }


def run():
    return {
        "status": "PASS",
        "numerical_tolerance": TOL,
        "counterexamples": check_counterexamples(),
        "sharpness": check_sharpness(),
        "random_reference_entangled_isometries": check_random_stinespring(),
        "corrected_qrom": check_qrom(),
        "ideal_prefix_hybrid": check_ideal_prefix_hybrid(),
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
