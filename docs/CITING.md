# Citing This Evidence

[Repository overview](../README.md) | [Paper map](PAPER_MAP.md)

## Versioned Reference

The public repository is [jieyilong/ecdsafail-circuit-evidence](https://github.com/jieyilong/ecdsafail-circuit-evidence), with release **v1.0.0**:

- [Release v1.0.0](https://github.com/jieyilong/ecdsafail-circuit-evidence/releases/tag/v1.0.0)
- [Repository tree at v1.0.0](https://github.com/jieyilong/ecdsafail-circuit-evidence/tree/v1.0.0)

Cite the release version and record its full repository commit for an exact checkout. Machine-readable metadata is in [CITATION.cff](../CITATION.cff). Cite the manuscript for scientific contributions and the artifact release for the preserved evidence. Do not substitute an upstream circuit-source revision for this evidence repository's release commit. They identify different objects.

A concise evidence reference is:

> Jieyi Long. ECDSA.Fail Circuit Validation Evidence, version v1.0.0, 2026. Repository: jieyilong/ecdsafail-circuit-evidence. Dataset: experiments/02-fresh-windowed/.

For a specific result, add its repository-relative path and, when relevant, candidate, stratum, and index. For example, use `experiments/02-fresh-windowed/analysis.json` for Table 6 or `experiments/01-development/runs/` for Table 5. This gives a reader a public version first and an unambiguous location within it second.

## Cite the Right Dataset

The September 7 replay/split comparisons have different evidence releases. Use their pinned commits and relative experiment directories in [PAPER_MAP.md](PAPER_MAP.md#separate-september-7-evidence), not `v1.0.0` of this repository. This release does not contain their complete seven-circuit, 700,000-row dataset.

For a new reproduction, report the original release and the new run's source, toolchain, settings, operation comparison, and output receipt. Do not present the new run as the originally frozen binary or ledger.

No Zenodo DOI is asserted here. A future deposit can add a verified version-specific DOI after it exists, alongside the GitHub release and commit. No paper arXiv identifier, paper upload, or paper PDF is supplied by this repository.
