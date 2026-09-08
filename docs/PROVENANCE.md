# Provenance and Artifact Identity

## Additive v1.1.0 Release

Experiments 01-05, all original source archives/trees, and the pre-study freeze are byte-identical to v1.0.0. The preceding publication inventory is retained in [v1.0.0-publication-manifest.json](../provenance/v1.0.0-publication-manifest.json). `scripts/verify_mechanism.py` checks the old scientific files against it. The current publication inventory adds the new files and updated reader tools. It is not a rewritten experimental freeze.

Experiments [06](../experiments/06-resource-accounting/README.md) and [07](../experiments/07-boundary-diagnosis/README.md) are copied from separately verified portable supplements, with their own manifests, source lineage, raw records, and documented exclusions. Their staging notes and embedded paths remain historical records. The current publication status is described in the root [changelog](../CHANGELOG.md), not those archived staging statements.

[Repository overview](../README.md) | [Reproduction](REPRODUCTION.md)

## Preserved Records, New Layout

This repository reorganizes an existing evidence ZIP for readers. Its imported files are relocated **byte for byte**, not remeasured or rewritten. [path-map.json](../provenance/path-map.json) maps every original bundle path to its new repository-relative path and records its byte count and SHA-256 hash. It also records the original ZIP hash.

The [original bundle README](../provenance/original-bundle/README.md), [release index](../provenance/original-bundle/release-index.json), and [packaging/verifying script](../provenance/original-bundle/package_evidence.py) remain intact. The root documentation and new `scripts/` wrappers are later reader and reproduction conveniences. The experiment scripts in [sources/frozen-tools](../sources/frozen-tools/) remain the original scripts, including the frozen statistical analysis.

Some archived logs, documentation, and cached bytecode retain historical local paths. They are provenance, not public download locations or required working directories. Follow [the portable reproduction commands](REPRODUCTION.md) instead of rewriting archived paths.

## Common Path Translations

| Original bundle path | Repository path |
|---|---|
| `freeze.json` | [provenance/freeze.json](../provenance/freeze.json) |
| `fresh-corpus-spec.json` | [experiments/02-fresh-windowed/corpus-spec.json](../experiments/02-fresh-windowed/corpus-spec.json) |
| `analysis.json` | [experiments/02-fresh-windowed/analysis.json](../experiments/02-fresh-windowed/analysis.json) |
| `corpus/` | [experiments/02-fresh-windowed/data/corpus/](../experiments/02-fresh-windowed/data/corpus/) |
| `results/<candidate>/<stratum>/` | [experiments/02-fresh-windowed/runs/](../experiments/02-fresh-windowed/runs/), using the reader-facing candidate names |
| `supplementary/development/` | [experiments/01-development/runs/](../experiments/01-development/runs/) |
| `supplementary/evaluator-equivalence/` | [experiments/03-evaluator-equivalence/runs/](../experiments/03-evaluator-equivalence/runs/) |
| `supplementary/coordinate-phase-trace.log` | [experiments/04-coordinate-phase/trace.log](../experiments/04-coordinate-phase/trace.log) |
| `artifacts/code/experiments/` | [sources/frozen-tools/](../sources/frozen-tools/) |
| `artifacts/source.tar.gz` | [sources/archives/conservative-pingpong.tar.gz](../sources/archives/conservative-pingpong.tar.gz) |
| `supplementary/representation-probe.tar.gz` | [sources/archives/zero-payload-probe.tar.gz](../sources/archives/zero-payload-probe.tar.gz) |

Use the complete path map for individual files. Original candidate keys `pingpong_base` and `pingpong_conservative` are preserved inside frozen JSON, even though their directories are named `original-pingpong` and `conservative-pingpong`.

## Sources and Freeze

| Snapshot | Circuit source identity | Role |
|---|---|---|
| [original-pingpong](../sources/trees/original-pingpong/) | `2e0187c99fef038f079aaf76b6d36f64cce7481e` | Original split-cleanup circuit |
| [conservative-pingpong](../sources/trees/conservative-pingpong/) | `345c23fcf1073b7559a9d41e113f755259545bf2` | Selected guarded circuit and auxiliary evaluator |
| [jump2](../sources/trees/jump2/) | `080452804328698214f36655d95c9883be6a3080` | Jump-2 split-cleanup circuit |
| [zero-payload-probe](../sources/trees/zero-payload-probe/) | Diagnostic derived from `345c23fcf1073b7559a9d41e113f755259545bf2`, identified by its own archive hash | Post-hoc instrumentation, not the frozen final-study stream |

All four original archives are retained in [sources/archives](../sources/archives/). [source-trees.json](../provenance/source-trees.json) records each archive hash, member hashes, and `omitted_cached_bytecode`. Browsable trees expose the same member bytes except for the explicitly listed `.pyc` cache members. Those omissions apply only to the browsable trees. The original archives still contain their original members and are byte-identical.

[freeze.json](../provenance/freeze.json) records settings, peak width, static counts, operation-stream hashes and decoded fingerprints, evaluator and trusted-core hashes, analysis hashes, and the original Rust version. Its `frozen_utc` is `2026-09-08T06:45:42.983722+00:00`. The [fresh corpus specification](../experiments/02-fresh-windowed/corpus-spec.json) records the subsequent generation time `2026-09-08T06:45:43.146102+00:00` and binds itself to the freeze hash.

The [operator-reproduction receipt](../provenance/operator-reproduction.json) and [build log](../provenance/operator-reproduction.log) record a byte-identical conservative operation-stream rebuild. This receipt is evidence of that recorded rebuild, not another accuracy experiment or a guarantee of identical native binaries on every platform.

## Verification Chain

`python3 scripts/verify.py` checks the relocated files and source trees, reconstructs the original bundle layout in temporary storage, and runs the original verifier there. That verifier expands shared corpus fields and `=` outcome markers to recover the 27 original raw final ledgers, verifies their hashes and checkpoint offsets, and reruns the frozen analysis. Development and evaluator-equivalence checks remain part of that original verification.

Thus there are distinct identities to inspect: original ZIP, imported file, source archive, archive member, native binary, compressed operation stream, decoded operation fingerprint, and original raw ledger. Matching one does not automatically prove all the others match. Newly executed ledgers may have a different completion order even when their indexed outcomes and batch work agree.

Large operation streams and platform-specific binaries are intentionally omitted. Their original hashes remain in the freeze and the release index's `omitted_large_artifacts` list. Rebuild them under `.work/` when execution is needed. Never replace frozen hashes or originals with new build products.

## Attribution and Notices

See [attribution and reuse](../THIRD_PARTY_NOTICES.md), the restored [upstream notice](../sources/UPSTREAM_NOTICE.txt), and the notices accompanying the source materials. This documentation does not apply a new blanket license to the imported code or records. Historical claims and paths inside preserved source notes should be read in their original context, not as new claims about the scope of this repository.
