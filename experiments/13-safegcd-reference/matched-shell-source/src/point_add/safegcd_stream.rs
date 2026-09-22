//! Callback adapter only. Coordinate shell, square and QROM remain frozen.
use super::*;
use crate::circuit::{Circuit, NO_BIT, NO_QUBIT};
use std::sync::OnceLock;

pub(super) fn apply(b: &mut B, denominator: &[QubitId], payload: &[QubitId], divide: bool) {
    static STREAM: OnceLock<Circuit> = OnceLock::new();
    let circuit = STREAM.get_or_init(|| {
        let path = std::env::var("QIP_SAFEGCD_KMX").expect("safegcd stream path");
        let c = Circuit::from_kmx(path).expect("read frozen safegcd stream");
        assert_eq!(c.num_qubits, 3300);
        assert_eq!(c.num_bits, 0);
        assert_eq!(c.operations.iter().filter(|op| op.kind == OperationType::CCX).count(), 7_501_932);
        for op in &c.operations {
            assert!(matches!(op.kind, OperationType::X | OperationType::CX | OperationType::CCX));
            assert_eq!(op.c_condition, NO_BIT);
        }
        c
    });
    assert_eq!(denominator.len(), 256);
    assert_eq!(payload.len(), 256);
    let scratch = b.alloc_qubits(circuit.num_qubits as usize - 512);
    let map: Vec<QubitId> = denominator.iter().chain(payload).chain(&scratch).copied().collect();
    let mut emit = |op: &Op| {
        let mut mapped = *op;
        for q in [&mut mapped.q_target, &mut mapped.q_control1, &mut mapped.q_control2] {
            if *q != NO_QUBIT { *q = map[q.0 as usize]; }
        }
        b.push_op(mapped);
    };
    if divide {
        for op in &circuit.operations { emit(op); }
    } else {
        for op in circuit.operations.iter().rev() { emit(op); }
    }
    // Complete component tests check these wires before any allocator reset.
    b.free_vec(&scratch);
}
