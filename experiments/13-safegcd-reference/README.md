# 13. Reversible Safegcd References

[Full report](FULL_BASELINE_REPORT.md) | [Specification](SPECIFICATION.md) | [Primitive-matched results](common-component-results.json) | [All evidence](full-results.json)

Complete DIV/MUL components use the same canonical payload primitives and full-width allocation conventions:

| Component | Rounds | Q | Static Toffolis per DIV or MUL | Failures on 128 common cases per direction |
| --- | ---: | ---: | ---: | ---: |
| Safegcd | 741, proved round bound | 3,300 | 7,501,932 | 0 |
| Ping-pong | 768, conditional | 2,320 | 6,289,400 | 12 |
| Ping-pong | 1,536, conditional | 3,088 | 12,574,712 | 0 |

These are deliberately unoptimized references. The ordering changes with the paid horizon. The 1,536-round ping-pong budget covers this test set but is not a proved all-input bound. Do not compare these component counts directly with complete windowed point-addition counts.

Complete w=4 point-addition shells also pass 64 common inputs. That comparison matches the shell, but its callbacks use different arithmetic lowering and therefore do not isolate the recurrence. The [full report](FULL_BASELINE_REPORT.md) retains both results and all scope distinctions.

## Reproduce in scratch space

The [source](source/) includes actual gate emitters and the unchanged original simulator. The [matched shell source](matched-shell-source/) provides the separate integration experiment. Generated large KMX streams, vector sets, native binaries, and Cargo outputs are omitted. Regenerate them using:

```sh
python3 scripts/reproduce_latest.py prepare-safegcd
cd .work/latest-safegcd/ecdsafail-qip-safegcd-20260922
cargo build --release --locked --bin safegcd_round_verify -j 2
python3 safegcd_probe/full.py --output safegcd_probe/full-secp256k1
python3 safegcd_probe/test_full.py
python3 safegcd_probe/test_coefficients.py
python3 safegcd_probe/test_pingpong.py
python3 safegcd_probe/common_components.py
```

Read each generator's help and the full report for full-size versus small-prime tests. Reproduction requires substantial memory and time. All output is confined to the prepared scratch copy. Local scalar checks and emitted-gate simulations are distinct evidence.
