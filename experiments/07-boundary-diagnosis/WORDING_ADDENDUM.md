# P2 Wording Correction: Nonzero Is Not Necessarily p

An independent review correctly identified an overstatement in the first
diagnosis report: the 35/64 pre-release coefficient count is a **nonzero count**,
not a count of registers proven equal to the word `p`.

The observer bitwise-ORs the coefficient wires. It therefore detects whether a
register has at least one set bit but cannot classify its complete value.
Fixture index 4 is explicitly traced and confirmed to contain `p`. The retained
aggregate observation does not establish that all 35 nonzero registers contain
`p`, or even classify all their field values. The published final-output `p`
counts, 28 for division and 46 for multiplication, are separate observations
and are unchanged.

The scientific report and portable report now say "35 nonzero" and identify
fixture 4 separately. The component-summary metadata already uses
`coefficient_prereset_nonzero_count` and does not require numerical changes.
No raw logs, source, simulator, evaluator, reference, or experiment was changed.
No additional circuit experiment was run for this correction.

Within the portable package, the original report remains byte-for-byte in
`provenance/original/REPORT.md`; it is historical and superseded by this addendum.
Original manifests and original verification receipts remain unchanged. The
corrected scientific report is retained in `provenance/corrected/REPORT.md`, with
the exact editorial changes recorded in `provenance/editorial-correction.json`
and `patches/scientific-wording-correction.diff`. The portable formatting/path
adaptation has its own diff. The new stage manifest and stage verification are
regenerated after correction; they are not replacements for frozen v1 evidence.

The established findings remain scoped to raw emitted cells and isolated
components, not an entire-kernel zero-error result or a general repair.
