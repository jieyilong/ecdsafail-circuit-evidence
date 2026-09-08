# Citing This Evidence

[Repository overview](../README.md) | [Paper map](PAPER_MAP.md)

## Versioned Reference

The public repository is [jieyilong/ecdsafail-circuit-evidence](https://github.com/jieyilong/ecdsafail-circuit-evidence), with additive release **v1.1.0**:

- [Release v1.1.0](https://github.com/jieyilong/ecdsafail-circuit-evidence/releases/tag/v1.1.0)
- [Repository tree at v1.1.0](https://github.com/jieyilong/ecdsafail-circuit-evidence/tree/v1.1.0)
- [Preserved v1.0.0 release](https://github.com/jieyilong/ecdsafail-circuit-evidence/releases/tag/v1.0.0)

Cite the release version and record its full repository commit for an exact checkout. Machine-readable metadata is in [CITATION.cff](../CITATION.cff). Cite the manuscript for scientific contributions and the artifact release for the preserved evidence. Do not substitute an upstream circuit-source revision for this evidence repository's release commit. They identify different objects.

A concise evidence reference is:

> Jieyi Long. ECDSA.Fail Circuit Validation Evidence, version v1.1.0, 2026. Repository: jieyilong/ecdsafail-circuit-evidence.

For a specific result, add its repository-relative path and, when relevant, candidate, stratum, and index. Use `experiments/02-fresh-windowed/analysis.json` for the frozen study (Table 9), `experiments/06-resource-accounting/` for Tables 4-6, and `experiments/07-boundary-diagnosis/` for Appendix C.3. The unchanged frozen study may still cite v1.0.0. New mechanism results must cite v1.1.0, not the older release. Always distinguish the evidence-release commit from the circuit-source commit.

## Cite the Right Dataset

The September 7 replay/split comparisons have different evidence releases. Use their pinned commits and relative experiment directories in [PAPER_MAP.md](PAPER_MAP.md#separate-september-7-evidence), not `v1.0.0` of this repository. This release does not contain their complete seven-circuit, 700,000-row dataset.

For a new reproduction, report the original release and the new run's source, toolchain, settings, operation comparison, and output receipt. Do not present the new run as the originally frozen binary or ledger.

No Zenodo DOI is asserted here. A future deposit can add a verified version-specific DOI after it exists, alongside the GitHub release and commit. No paper arXiv identifier, paper upload, or paper PDF is supplied by this repository.
