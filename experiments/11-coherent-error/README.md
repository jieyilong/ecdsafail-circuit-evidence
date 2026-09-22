# 11. Conditional Coherent-Error Analysis

[Proof PDF](coherent_error_theorem.pdf) | [LaTeX source](coherent_error_theorem.tex) | [Applicability report](applicability_report.md) | [Recorded checks](check_results.json)

For corrected Kraus branches satisfying `K_m Pi = gamma_m U Pi` with common input-independent complex amplitudes, bad-subspace weight q bounds trace distance by `min(1, 2 sqrt(q))`. The note proves a sharper bound and an ideal-prefix hybrid composition argument that permits correlated calls and entangled references.

This is a conditional mathematical result. The complete arithmetic good set and its weights under the full Shor schedule have not been certified. Correct basis outputs and input-independent measurement probabilities alone are insufficient. The first accumulator after a 16-bit initialization is not uniform on the whole curve.

To rerun the pure matrix and prefix checks in memory (NumPy required):

```sh
python3 scripts/check_latest_theory.py
```

The 150 matrix tests and 39,402 small-curve pair checks are regression evidence supporting the derivation. They are not simulation of the production arithmetic circuit. The original context-aware runner and its workspace locators remain as provenance; use the portable command above from this checkout.
