# 12. Schedule and Width Counterexamples

[Detailed report](REPORT.md) | [Structured cases](structured_witnesses.json) | [Exact model](model.py) | [Width schedule](width_schedule.csv)

**768 rounds is not an all-input bound.** Exact denominator 3 requires 1,135 transitions, and 2^255 requires 1,239. Denominator 1 terminates in 512 transitions but violates the margin-20 pre-halving width at index177. These field inputs were lifted to supported curve pairs in [experiment 10](../10-targeted-repair/diagnostics/schedule-points.tsv).

Signed 258-bit arithmetic suffices for ordinary pre-halving sums in the ideal recurrence. Keeping the source's 259-bit values prevents that truncation mechanism, but costs more storage and does not prove 768-round termination.

The frozen ten-million-denominator histogram is reused from [experiment 08](../08-followup-diagnostics/tail-10000000.json), not rerun. A new independent 10,000-input sample and the reproduced frozen pilot are retained here, along with structured traces. Their counts are not pooled. The original driver records its compiler/GMP requirements and workspace paths in [the report](REPORT.md).

Portable, read-only recurrence checks:

```sh
python3 scripts/check_latest_theory.py --schedule-only
```

This checks the explicit long walks and width counterexample using the retained model. The native input files, source, and receipts support deeper reproduction. A small random sample or a complete mathematical range bound does not certify the tapered emitted circuit.
