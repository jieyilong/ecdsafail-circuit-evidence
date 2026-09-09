# Citing This Evidence

[Repository overview](../README.md) | [Paper map](PAPER_MAP.md)

## Versioned Reference

The public repository is [jieyilong/ecdsafail-circuit-evidence](https://github.com/jieyilong/ecdsafail-circuit-evidence), with additive release **v1.3.0**:

- [Release v1.3.0](https://github.com/jieyilong/ecdsafail-circuit-evidence/releases/tag/v1.3.0)
- [Repository tree at v1.3.0](https://github.com/jieyilong/ecdsafail-circuit-evidence/tree/v1.3.0)
- [Preserved v1.0.0 release](https://github.com/jieyilong/ecdsafail-circuit-evidence/releases/tag/v1.0.0)

Cite the release version and record its full repository commit for an exact checkout. Machine-readable metadata is in [CITATION.cff](../CITATION.cff). Cite the manuscript for scientific contributions and the artifact release for the preserved evidence. Do not substitute an upstream circuit-source revision for this evidence repository's release commit. They identify different objects.

A concise evidence reference is:

> Jieyi Long. ECDSA.Fail Circuit Validation Evidence, version v1.3.0, 2026. Repository: jieyilong/ecdsafail-circuit-evidence.

For a specific result, add its repository-relative path and, when relevant, candidate, stratum, and index. Use `experiments/02-fresh-windowed/analysis.json` for the frozen study (Table 9), `experiments/06-resource-accounting/` for Tables 4-6, `experiments/07-boundary-diagnosis/` for Appendix C.3, and `experiments/08-followup-diagnostics/` for Appendix C.4. The unchanged frozen study may still cite v1.0.0. The mechanism studies were first published in v1.1.0. The new Appendix C.4 diagnostics require v1.2.0. Always distinguish the evidence-release commit from the circuit-source commit.

## Cite the Right Dataset

The September 7 replay/split comparisons have different evidence releases. Use their pinned commits and relative experiment directories in [PAPER_MAP.md](PAPER_MAP.md#separate-september-7-evidence), not `v1.0.0` of this repository. This release does not contain their complete seven-circuit, 700,000-row dataset.

For a new reproduction, report the original release and the new run's source, toolchain, settings, operation comparison, and output receipt. Do not present the new run as the originally frozen binary or ledger.

No Zenodo DOI is asserted here. A future deposit can add a verified version-specific DOI after it exists, alongside the GitHub release and commit. No paper arXiv identifier, paper upload, or paper PDF is supplied by this repository.

For the alternate 34-page correctness-reference manuscript, cite v1.3.0 and
`experiments/09-canonical-reference/`. Its 4,096-input pilot is separate from the
original 100,000-input study. The 35-page low-cost manuscript remains correctly
pinned to v1.2.0 when it does not discuss the reference implementation.
