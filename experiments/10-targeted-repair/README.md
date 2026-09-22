# 10. Targeted Zero-Payload Repair

This is the **September 22, 2026 single-candidate study**, separate from experiment 02's three-circuit comparison. The candidate repairs the tested zero-payload and zero-slope failures while retaining approximate arithmetic and explicit supported-input failures.

| Measurement | Result |
| --- | ---: |
| Mixed peak, same arithmetic | 1,402 qubits |
| Windowed peak, w=16 | 1,419 qubits |
| Windowing overhead at fixed arithmetic | 17 qubits |
| Serialized static CCX+CCZ | 1,524,503 |
| Mean executed Toffolis | 1,356,324.32985 |
| Q x T | 1,924,624,224.05715 |
| Fresh inputs across nine tables | 100,000 |
| Output / phase / ancilla failures | 0 / 0 / 0 |
| Retained identity-addend rows | 4 |

The increase from the older conservative windowed width 1,392 to 1,419 is a separate arithmetic change: 32 more transcript qubits, six fewer terminal value qubits, and one zero-payload flag. It does not increase the measured 17-qubit lookup-interface overhead.

## Find the evidence

| Question | File or directory |
| --- | --- |
| Full precision, uncertainty, and per-stratum counts | [verified-results.json](fresh-study/verified-results.json) |
| What was fixed before seed generation? | [freeze.json](fresh-study/freeze.json) |
| Table points, shifts, seeds, and sample sizes | [plan.json](fresh-study/plan.json) |
| Every input, output, and failure flag | [fresh-study/](fresh-study/) (`stratum-0` through `stratum-8`, `checkpoint/inputs.tsv.gz`) |
| Batch gate totals and checkpoint metadata | Each stratum's `checkpoint/batches.tsv` and `manifest.tsv` |
| Actual static count | [w=16 stream count](diagnostics/masked_chunk_coords-w16/stats.stdout) |
| Known zero-slope and smoke tests | [w=4](diagnostics/masked_chunk_coords-w4/), [w=16](diagnostics/masked_chunk_coords-w16/) |
| Remaining supported-domain failures | [48-lane outcomes](diagnostics/schedule-points-w4.tsv), [six input pairs](diagnostics/schedule-points.tsv) |
| Frozen circuit and evaluator | [source](source/), [repair explanation](source/QIP_TARGETED_REPAIR.md) |
| Initial local cell attempts, including failures | [cell-summary.json](diagnostics/cell-summary.json) |
| Import identities and lossless compression | [publication path map](../../provenance/v1.4.0-import-map.json) |

The builder's 1,530,647 bookkeeping count includes 6,144 forward gates discarded during inverse-coordinate construction. The serialized count above is authoritative. `T` is an executed mean and includes every trial.

## Scope

Zero observed failures gives a one-sided 95% upper bound of approximately **0.00300%** under the stated independent sampling model. It is not a quantum-channel error bound. Six supported points with input denominators 1, 3, and 2^255 still fail all 48 tested output lanes, with 25 phase flags. The 48 lanes repeat six points; they are not independent random inputs. See [schedule audit](../12-schedule-audit/README.md).

The zero-payload flag is uncomputed correctly when the actual input and output words preserve the zero predicate. Other arithmetic failures can invalidate that condition. This is a targeted repair, not a canonical or all-input-safe replay implementation.

## Verify and reproduce

From the repository root, Python 3.11+:

```sh
python3 scripts/verify_latest.py
```

This read-only check reconciles all 100,000 records, every selected table point and expected affine result with independent Python arithmetic, all batch totals, negative fixtures, source hashes, and preserved earlier scientific files. It does not execute a quantum circuit. Large streams and native binaries are omitted.

For rebuilding, all writes go under `.work/`:

```sh
python3 scripts/reproduce_latest.py prepare
python3 scripts/reproduce_latest.py build
python3 scripts/reproduce_latest.py emit --width 4
python3 scripts/reproduce_latest.py targeted --width 4
python3 scripts/reproduce_latest.py emit --width 16
python3 scripts/reproduce_latest.py targeted --width 16
python3 scripts/reproduce_latest.py study --stratum 0
```

Repeat the final command for strata 1 through 8 to replay the complete retained corpus. Execution needs Rust dependencies, roughly 24 GB free RAM for w=16, disk space, and substantial runtime. The wrapper checks emitted identity and retained outcomes. A new random study is distinct from reproducing these fixed seeds. Original workspace scripts under `provenance/` are preserved for inspection, not intended to be run in the published directories.
