# 04. Coordinate-Phase Diagnostic

[Repository overview](../../README.md) | [Generated results](RESULTS.md) | [Stage CSV](stages.csv) | [Development runs](../01-development/README.md)

**Purpose:** localize the phase-only failure at development input **6828**, shared by the first four parameter configurations. This is diagnostic support for **Section 7.4**, not another accuracy experiment.

## What the Trace Shows

The [original trace](trace.log) evaluates development batch **106** and splits the unchanged operations at balanced phase boundaries. With 64 cases per batch, index 6828 is lane **44**: `106 * 64 + 44 = 6828`. The generated [case record](case-6828.json) collects this input's outcomes across all five development configurations.

The initial `start` row has zero delta and zero cumulative phase. The first **nonzero** delta appears at `tlm_coord_x_sub`: `0x0000100000000000`, marking lane 44. All later stage deltas are zero, and the cumulative mask retains that bit. The failure is localized to the initial x-coordinate subtraction. Zero net delta at later boundaries does not prove that every internal phase operation was correct.

The diagnosis identifies a 19-bit high-prefix carry check that misses a carry from lower bits. The documented fifth development configuration sets `TLM_MSBS=40`, clearing this failure on the development corpus for about 72 additional mean Toffolis and no additional peak qubits. Compare the complete [fourth](../01-development/runs/04-wider-replay-guards/summary.json) and [fifth](../01-development/runs/05-wider-coordinate-check/summary.json) summaries for those resource and outcome claims.

## Reading the Log Safely

`QIP_PHASE_TRACE` lines contain the selected `batch`, operation boundaries `start` and `end`, a stage name in `phase`, a stage-local `delta` mask, and a `cumulative` phase mask. The stage name is not a numerical phase value.

**Do not use the log's printed 16,384-shot denominator, percentages, average work, or final "OK" banner as experiment totals.** They are inherited from the full evaluator, but this diagnostic executes only the selected batch. Only the stage masks support the localization. The five complete development ledgers supply the reported accuracy and resource totals.

The [frozen protocol amendment](../../sources/frozen-tools/bounded_qip/PROTOCOL.md) records the diagnosis and its timing before the final freeze. The [diagnostic evaluator source](../../sources/trees/conservative-pingpong/src/bin/eval_phase_diagnostic.rs) is preserved for inspection. This repository's fresh `run` command does not use it.

This explains one development input, not every historical phase failure. A 40-bit coordinate-prefix check is still truncated, and the unrelated post-hoc [zero-payload diagnostic](../05-zero-payload/README.md) must be interpreted separately.
