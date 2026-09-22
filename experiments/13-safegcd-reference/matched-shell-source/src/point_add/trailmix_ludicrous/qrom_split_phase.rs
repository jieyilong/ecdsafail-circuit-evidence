//! Exact X-basis payload removal with a split-address phase correction.
//! See Gidney, arXiv:1905.07682, Section 2. Both one-hot decoders here are
//! uncomputed unitarily, trading a small constant in Toffolis for simple cleanup.
use super::*;
use crate::circuit::Op;

struct PhaseColumn<'a> {
    measurements: &'a [BitId],
    table: &'a [Vec<BitId>],
    stride: usize,
    offset: usize,
}

fn decode(circ: &mut B, address: &[QubitId]) -> Vec<QubitId> {
    let root = circ.alloc_qubit();
    circ.x(root);
    let mut flags = vec![root];
    for &bit in address {
        let count = flags.len();
        for row in 0..count {
            let child = circ.alloc_qubit();
            circ.ccx(flags[row], bit, child);
            circ.cx(child, flags[row]);
            flags.push(child);
        }
    }
    flags
}

fn clear_decoder(circ: &mut B, address: &[QubitId], flags: Vec<QubitId>) {
    assert_eq!(flags.len(), 1usize << address.len());
    for level in (0..address.len()).rev() {
        let count = 1usize << level;
        for row in (0..count).rev() {
            let child = flags[count + row];
            circ.cx(child, flags[row]);
            circ.ccx(flags[row], address[level], child);
            circ.zero_and_free(child);
        }
    }
    circ.x(flags[0]);
    circ.zero_and_free(flags[0]);
}

fn fixup_cost(width: usize) -> usize {
    let low = 1usize << (width / 2);
    let high = 1usize << (width - width / 2);
    2 * (low + high) - 4
}

fn fixup(circ: &mut B, address: &[QubitId], columns: &[PhaseColumn<'_>]) {
    let rows = 1usize << address.len();
    for column in columns {
        assert_eq!(column.table.len(), rows * column.stride);
        assert!(column.offset < column.stride);
        assert!(column
            .table
            .iter()
            .all(|word| word.len() == column.measurements.len()));
    }
    let split = address.len() / 2;
    let low = decode(circ, &address[..split]);
    let high = decode(circ, &address[split..]);

    // All these diagonal corrections commute. Hoist the measurement condition
    // across rows and use the primitive's second classical condition for table data.
    for column in columns {
        for (bit, &measurement) in column.measurements.iter().enumerate() {
            circ.push_condition(measurement);
            for (hi, &hi_flag) in high.iter().enumerate() {
                for (lo, &lo_flag) in low.iter().enumerate() {
                    let row = (hi * low.len() + lo) * column.stride + column.offset;
                    let mut op = Op::empty();
                    op.kind = OperationType::CZ;
                    op.q_control1 = hi_flag;
                    op.q_target = lo_flag;
                    op.c_condition = column.table[row][bit];
                    circ.push_op(op);
                }
            }
            circ.pop_condition();
        }
    }
    clear_decoder(circ, &address[split..], high);
    clear_decoder(circ, &address[..split], low);
}

fn measure_payload(circ: &mut B, payload: &[QubitId]) -> Vec<BitId> {
    payload
        .iter()
        .map(|&qubit| {
            let measurement = circ.alloc_bit();
            circ.hmr(qubit, measurement);
            circ.zero_and_free(qubit);
            measurement
        })
        .collect()
}

pub(super) fn unload_word(
    circ: &mut B,
    address: &[QubitId],
    target: &[QubitId],
    table: &[Vec<BitId>],
    workspace: QromWorkspace,
    measure_phase: &'static str,
    clear_phase: &'static str,
) {
    assert!(
        std::env::var_os("WINDOWED_QROM_COUNT_ONLY").is_none(),
        "split cleanup requires real emission"
    );
    assert_eq!(table.len(), 1usize << address.len());
    circ.set_phase(measure_phase);
    QROM_CALLS.fetch_add(1, Ordering::Relaxed);
    match workspace {
        QromWorkspace::Unary => {
            let measurements = measure_payload(circ, target);
            circ.set_phase(clear_phase);
            fixup(
                circ,
                address,
                &[PhaseColumn {
                    measurements: &measurements,
                    table,
                    stride: 1,
                    offset: 0,
                }],
            );
            QROM_TOFFOLIS.fetch_add(fixup_cost(address.len()) as u64, Ordering::Relaxed);
            for measurement in measurements {
                circ.bit_store0(measurement);
            }
        }
        QromWorkspace::Qroam2(junk) => {
            assert!(!address.is_empty());
            assert_eq!(junk.len(), target.len());
            for (&selected, &other) in target.iter().zip(&junk) {
                circ.cswap(address[0], selected, other);
            }
            let even = measure_payload(circ, target);
            let odd = measure_payload(circ, &junk);
            circ.set_phase(clear_phase);
            fixup(
                circ,
                &address[1..],
                &[
                    PhaseColumn {
                        measurements: &even,
                        table,
                        stride: 2,
                        offset: 0,
                    },
                    PhaseColumn {
                        measurements: &odd,
                        table,
                        stride: 2,
                        offset: 1,
                    },
                ],
            );
            QROM_TOFFOLIS.fetch_add(
                (fixup_cost(address.len() - 1) + target.len()) as u64,
                Ordering::Relaxed,
            );
            for measurement in even.into_iter().chain(odd) {
                circ.bit_store0(measurement);
            }
        }
    }
}

pub(super) fn unload_two_words(
    circ: &mut B,
    address: &[QubitId],
    left: &[QubitId],
    left_table: &[Vec<BitId>],
    right: &[QubitId],
    right_table: &[Vec<BitId>],
    workspace: QromWorkspace,
    measure_phase: &'static str,
    clear_phase: &'static str,
) {
    assert!(
        std::env::var_os("WINDOWED_QROM_COUNT_ONLY").is_none(),
        "split cleanup requires real emission"
    );
    assert!(matches!(workspace, QromWorkspace::Unary));
    circ.set_phase(measure_phase);
    let left_measurements = measure_payload(circ, left);
    let right_measurements = measure_payload(circ, right);
    circ.set_phase(clear_phase);
    fixup(
        circ,
        address,
        &[
            PhaseColumn {
                measurements: &left_measurements,
                table: left_table,
                stride: 1,
                offset: 0,
            },
            PhaseColumn {
                measurements: &right_measurements,
                table: right_table,
                stride: 1,
                offset: 0,
            },
        ],
    );
    QROM_CALLS.fetch_add(1, Ordering::Relaxed);
    QROM_TOFFOLIS.fetch_add(fixup_cost(address.len()) as u64, Ordering::Relaxed);
    for measurement in left_measurements.into_iter().chain(right_measurements) {
        circ.bit_store0(measurement);
    }
}
