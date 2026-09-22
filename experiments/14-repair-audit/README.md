# 14. Repair Audit and Independent Checks

[Initial audit](AUDIT.md) | [Follow-up audit](FOLLOWUP_AUDIT.md) | [Algebra checks](algebra-results.json) | [Gate-transcription checks](followup-transcription-results.json)

The audit records remaining nonzero replay defects, the raw/complemented correction distinction, the need for phase-correct coherence hypotheses, and the conditional nature of zero-flag erasure. It also checks the new zero detector, sign mask, and equality-aware chunk cleanup independently.

The gate checks are independent transcriptions, not additional execution of the emitted production stream. Original scripts are retained beside their results. Run them in a scratch copy because their original main routines write local result files. No audit claim replaces the frozen full-call study or establishes complete Shor correctness.
