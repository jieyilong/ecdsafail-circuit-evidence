# Targeted zero-payload repair

This branch extends the frozen 345c23f circuit with observation-only probes from evidence v1.3.0 and a separately tested targeted repair. It is not a challenge submission and does not claim all-input correctness.

Candidate emission flags:

```sh
QIP_PINGPONG_PROFILE=guarded768 QIP_ZERO_PAYLOAD_MASK=1 \
QIP_EXACT_CHUNK_CARRY=1 QIP_CANONICAL_COORDS=1 TLM_MSBS=40 \
CONSTPROP_DISABLE=1 SINGLE_CCX_FANOUT_DISABLE=1 \
WINDOWED_MODE=1 WINDOW_BITS=16 WINDOWED_QROM_UNLOAD=split \
./target/release/build_circuit
```

The zero-payload flag masks forward, inverse, and terminal signs. The exact chunk cleanup includes the incoming carry on equality and processes boundaries in reverse order. Canonical coordinate subtraction repairs the separate shell phase witness. Other replay and coordinate approximations remain. The zero flag's cleanup assumes that actual input/output words preserve the zero predicate.

Serialized w=16 resources: 1,419 qubits, 1,524,503 static CCX+CCZ. The builder's temporary bookkeeping includes 6,144 discarded forward gates; use stats_stream on ops.bin. Both known zero-slope points (32 measurement lanes each) and the 64-case smoke test pass at w=4 and w=16. Six supported points with denominators 1,3,2^255 still fail all48 output lanes. The source's inherited comments about clean release are conditional on successful arithmetic; the targeted diagnostics inspect the redundant coefficient before reset.

The companion research directory research/qip-oral-20260922 contains the frozen fresh-study driver, all retained outcomes, source hashes, repair comparisons, and independent affine-output verification. The original simulator and field oracle are unchanged. The optional canonical reference and canonical-endpoint flags are diagnostic alternatives and are NOT enabled in this candidate.
