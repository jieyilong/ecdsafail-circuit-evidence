# Retrieval and provenance

Workspace indices searched (read-only):

- `research/index.json`
- `research/alternative-inversion-2026-09/index.json`, BY19 entry
- `research/sub1000-sub10m-feasibility/index.json`
- `research/alternative-inversion-2026-09/search_results/safegcd_and_non_gcd.json`
- `research/alternative-inversion-2026-09/extracts/safegcd_and_non_gcd.md`

The existing extract supplied the successor collision, the two-bit-history
warning, and the distinction between original divsteps and other recurrences.
This pass independently read the primary theorem and implemented the exact
field-payload sandwich and executable tests. No literature index was modified.

Primary sources retrieved September 22, 2026:

- Bernstein-Yang original paper, [primary-paper mirror](https://d-nb.info/1205834052/34),
  PDF pages 20-21 and 25-27 (journal pp. 360-361 and 365-367): recurrence,
  signed bounds, exact stopping theorem, modular inverse interpretation.
  Original [author-hosted URL](https://troll.iis.sinica.edu.tw/by-publ/recent/safegcd.pdf)
  returned timeout; `gcd.cr.yp.to` returned HTTP 502. Mirror text was available.
- [libsecp256k1 author implementation notes](https://github.com/bitcoin-core/secp256k1/blob/master/doc/safegcd_implementation.md),
  Sections 1-3 and 5, independently corroborate recurrence and modular
  coefficient maps. Do not import its CPU speedups or shorter iteration bound.

Frozen code parent: `345c23fcf1073b7559a9d41e113f755259545bf2`.
New detached sibling: `ecdsafail-qip-safegcd-20260922`.
Shared Git worktree registration is the only parent metadata change; existing
parent working files and manuscript files were not edited.
