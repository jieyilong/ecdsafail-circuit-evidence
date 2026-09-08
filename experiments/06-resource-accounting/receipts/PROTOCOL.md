# Bounded resource accounting protocol

All writes are confined to this directory. Frozen source, evidence, paper, simulator,
and scoring logic are read-only inputs. New results are exploratory diagnostics.

1. Copy each requested source tree, preserving its bytes and a SHA-256 manifest.
2. Build unchanged emitters and the unchanged conservative `eval_bounded` offline.
3. Instrument copied allocation and phase reporting only. Verify emitted stream
   identity against unchanged builds for bounded mixed/small-window instances.
4. Compare actual emission with count-only output at the same settings before
   using count-only 16-bit-window accounting. Count-only is precompiler accounting;
   never substitute it for final-stream costs unless verified.
5. Use `SUB4_LEGACY_SQUARE=1` for a square-only ablation on original ping-pong.
   Same Euclidean backend, shell, source defaults and absent postcompiler. No nonce
   search. A backend 2x2 is optional and must not silently change compiler paths.
6. Smoke-test on a shared seed, 64 common inputs, small window, unchanged evaluator.
   Retain classical, phase, ancilla failures and raw outcomes. Costs and accuracy
   evidence remain separate. A clean smoke test is not a correctness proof.

Resource ceiling: 8 threads, 32 GiB. Runs are serial. No anticipated >12 GB run
without notifying the parent. Implementation is timeboxed to bounded feasible work;
unsupported combinations and failed attempts remain in the result ledger.
