# Local Replay Cell and Scalar Algebra

These unchanged manuscript-source files support Figure 2, Table 1 (`tab:local-replay-cell`), and the ideal-recurrence argument. They are separate from the new full-backend ablation and from the frozen random-input study.

- [Recorded cell counts](evidence/replay-cell-probe.json): 512 source-default unfused, 446 range-matched unfused, and 393 fused inverse static Toffolis.
- [Scalar checks](evidence/replay-algebra-checks.json): small signed recurrence and guarded fusion identities, not emitted-circuit accuracy.

From this directory, check the algebra offline without changing records:

```sh
python3 scripts/check_replay_algebra.py --check
```

Optional source emission requires Rust/Cargo dependencies and a challenge Git checkout containing commit `897dda2b0cf267151ecd973252d2a5078cbf1b63` from [the public challenge repository](https://github.com/Layr-Labs/ecdsafail-challenge/commit/897dda2b0cf267151ecd973252d2a5078cbf1b63):

```sh
python3 scripts/probe_replay_cells.py --source-checkout /path/to/ecdsafail-challenge --work-dir /tmp/new-replay-probe --check
```

The work directory must be new. The script archives the pinned source into that directory without editing the supplied checkout. Cargo defaults to locked offline mode. The source-emission result is a preserved earlier receipt, not a newly rerun v1.1.0 measurement. Matching correction width does not prove matching failure sets, and 393 does not count the Euclidean value round.
