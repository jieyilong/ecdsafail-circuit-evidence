# Window-selected ping-pong experiment

Construction and reproduction commands are in [WINDOWED_PINGPONG.md](../../WINDOWED_PINGPONG.md). The circuit freeze is commit `a1373a0582c9554d66633b13c76300d0ecdf81c4`, based on mixed ping-pong `897dda2b0cf267151ecd973252d2a5078cbf1b63`. The two-column lookup donor is `15a29ac9b1e97fc21eb81b9a6f0f6d9c4dc7a92e`.

## Data provenance

The new windowed and reproduced mixed ping-pong circuits are evaluated on the same 100,000-input corpus as Experiment 1. The windowed Jump-2 reference reuses the complete August 9 paired evaluation ledger, not newly sampled outcomes. Its checkpoint fingerprint is checked against the original operation stream with a bounded-memory implementation of the evaluator's fingerprint calculation. The mixed Jump-2 ledger comes from Experiment 1. All four input/expected-output records are compared by input index before statistics are computed.

The corpus was already studied before this adapter was built. This is an exploratory common-corpus comparison. It is not a new blinded confirmation. No circuit setting is changed after the new full evaluation begins.

The evaluator and simulator in this branch are byte-identical to the lookup donor. They are kept separate from the untrusted point-addition source. The test seed, rather than a circuit-derived nonce, determines the corpus and the per-batch measurement randomness. Different circuits contain different measurement sequences, so their phase outcomes are not conditioned on identical physical measurement histories.

## Released ledgers

`results/corpus.tsv.gz` stores every index, address, input point, selected addend, and expected output, sorted by index. Each circuit's `outcomes.tsv.gz` stores every index, observed output, observed address, and all four failure flags. An `=` in an observed-value field means exact equality with the corresponding expected field in the shared corpus. This factors repeated data without dropping successful cases or failure outputs. Batch membership is `index // 64`.

`analyze_results.py` reconstructs every observed value and checks complete index coverage, the failure-channel union, and agreement with every durable 64-input batch record. The release export is accepted only if recomputing statistics from the factored files exactly matches analysis of the original full ledgers. Physical line ordering and redundant text formatting are not preserved. SHA-256 hashes of the original full files are recorded separately.

The uncompressed local operation streams, full original TSV ledgers, build/evaluation logs, pilot runs, and analysis are retained under `outputs/ecdsafail-pingpong-windowed-100k-20260907` in the paper workspace. Compressed operation streams are not checked into Git. Their hashes and static counts are recorded, and they can be regenerated from the frozen source.

## Recompute statistics

From the repository root:

```sh
python3 experiments/windowed_pingpong/analyze_results.py \
  --corpus experiments/windowed_pingpong/results/corpus.tsv.gz \
  --case mixed_pingpong experiments/windowed_pingpong/results/mixed_pingpong \
  --case windowed_pingpong experiments/windowed_pingpong/results/windowed_pingpong \
  --case mixed_jump2 experiments/windowed_pingpong/results/mixed_jump2 \
  --case windowed_jump2 experiments/windowed_pingpong/results/windowed_jump2 \
  --output /tmp/windowed-pingpong-analysis.json

python3 -m unittest discover -s experiments/windowed_pingpong -p 'test_*.py'
```

To analyze newly generated raw checkpoints, pass each checkpoint directory with `--case` and omit `--corpus`. `--export DIR` produces the factored release and verifies its reconstruction. `static_resources.py OPS --output JSON` streams compressed operation files through `zstd` and reports static gate counts without loading the full circuit into Python memory. The optional `stream_fingerprint.py OPS MANIFEST --output JSON` requires NumPy and checks the checkpoint's SHAKE256 operation fingerprint with bounded memory. Statistics and the ledger reconstruction use only Python's standard library.

## Accounting limits

Executed Toffoli counts are logged as exact totals per 64-input batch, including failures, then divided by 100,000. Individual input costs are not available from this bit-parallel evaluator. Its Clifford counter includes CX, CZ, SWAP, HMR, and reset, but excludes tracked X/Z operations. Total serialized operations include register metadata and classical-control instructions, not just quantum gates. Static measurement and reset counts are reported separately. Executed measurement counts, feed-forward rounds, and Toffoli depth have not been measured.

The reported pass fraction is the union of the evaluator's classical-output, phase, and ancilla checks. It is not a state-vector fidelity or a complete-Shor success probability. Paired confidence intervals use a normal approximation and are labeled accordingly. They are unreliable for superiority claims with very few discordant outcomes. For the windowed-versus-mixed ping-pong comparison, an additional conservative exact one-sided bound uses the zero observed candidate-only failures. The noninferiority margin is inherited from the exploratory protocol, not derived from a full-attack error budget.
