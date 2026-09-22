# Coherent Error Certificate Research

All files are confined to this directory. No manuscript edits or circuit repairs were made.

## Deliverables

- `coherent_error_theorem.tex`: standalone theorem, proof, counterexamples, ideal-prefix hybrid, and Shor-prefix formulas. No manuscript dependencies.
- `coherent_error_theorem.pdf`: compiled standalone note.
- `manuscript_short_result.tex`: proposed compact section-05 replacement, with explicit scope limitations. Not inserted into the manuscript.
- `applicability_report.md`: source-backed assessment of sections 05/12, complete-bad-set obligations, exact prefix support, and remaining certification gaps.
- `matrix_checks.py`: small matrix counterexamples, sharpness, entangled-reference Stinespring tests, corrected QROM, and a hybrid test.
- `prefix_support.py`: exact small-curve checks and production-size secp256k1 prefix membership counts for a specified schedule.
- `run_checks.py`: reproducible runner, input/script hashes, and results output.
- `check_results.json`: passing numerical and exact-integer evidence, plus checks of the parent task's targeted repair and schedule records. The running 100k study is not reported as complete.
- `search_plan.json`: primary-source retrieval scope and links.

## Main Result

For corrected Kraus operators satisfying `K_mu Pi = gamma_mu U Pi` with input-independent complex `gamma_mu`, bad weight `epsilon` bounds output purified and trace distance by

`b(epsilon) = sqrt(1 - max(0, 1 - 2 epsilon)^2)`.

This is sharp. Composition is bounded by `min(1, sum_i b(epsilon_i))`, with all weights measured on **ideal pre-call states**. Correct basis outputs and uniform measurement probabilities are insufficient.

The unshifted ascending `w=16` schedule has first post-initialization exceptional weight `65535/2^32`, not order `1/r`. The two zero-slope witnesses do not characterize the complete bad set. No full-Shor guarantee for the current circuits is claimed.

## Reproduce

From this directory, with Python 3.10+ and NumPy:

```sh
python3 -B run_checks.py
```

The machine's default Python lacks NumPy. The verified interpreter is:

```sh
/Users/jieyilong/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -B run_checks.py
```

The exact prefix/curve checks have no third-party dependencies:

```sh
python3 -B prefix_support.py
```

Build the standalone LaTeX with a standard installation using `pdflatex`, or Tectonic:

```sh
tectonic --keep-logs coherent_error_theorem.tex
```

For strict write confinement, the recorded local build uses a copied Tectonic cache inside `.build/` and `TECTONIC_CACHE_DIR` pointing there. It passes the copied bundle directory explicitly to avoid a local system-proxy initialization failure:

```sh
TECTONIC_CACHE_DIR="$PWD/.build/tectonic-cache" tectonic \
  --bundle .build/tectonic-cache/bundles/data/6ffe055852f8faf66c0acbe1a7fb27f87b869a90bad1204f3bf4d9683f597c7c \
  --only-cached --keep-logs coherent_error_theorem.tex
```

The local directory bundle has a `SHA256SUM` identity marker for the copied cache. Numerical regression checks are not a substitute for the analytical proof or an emitted-circuit validation. No numerical aggregate full-Shor error bound is provided.
