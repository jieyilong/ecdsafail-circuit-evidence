use std::sync::atomic::{AtomicU64, Ordering};

use super::{BExt, B};
use crate::circuit::{BitId, OperationType, QubitId};

#[path = "qrom_branch_tests.rs"]
mod branch_tests;

#[path = "qrom_split_phase.rs"]
mod split_phase;

pub(crate) fn branch_selfcheck() {
    branch_tests::exhaustive_split_branches();
    if std::env::var_os("WINDOWED_QROM_EXHAUSTIVE_ONLY").is_some() { return; }
    branch_tests::windowed_qrom_coherent_branches();
    branch_tests::windowed_qrom_all_addresses();
}

static QROM_CALLS: AtomicU64 = AtomicU64::new(0);
static QROM_TOFFOLIS: AtomicU64 = AtomicU64::new(0);
static QROM_PAYLOAD_CX: AtomicU64 = AtomicU64::new(0);

#[derive(Clone, Copy, Debug, Default)]
pub struct QromStats {
    pub calls: u64,
    pub toffolis: u64,
    pub payload_cx: u64,
}

#[derive(Debug)]
pub enum QromWorkspace {
    Unary,
    Qroam2(Vec<QubitId>),
}

impl QromWorkspace {
    pub fn retains_payload_bank(&self) -> bool {
        matches!(self, Self::Qroam2(_))
    }
}

pub fn reset_stats() {
    QROM_CALLS.store(0, Ordering::Relaxed);
    QROM_TOFFOLIS.store(0, Ordering::Relaxed);
    QROM_PAYLOAD_CX.store(0, Ordering::Relaxed);
}

pub fn stats() -> QromStats {
    QromStats {
        calls: QROM_CALLS.load(Ordering::Relaxed),
        toffolis: QROM_TOFFOLIS.load(Ordering::Relaxed),
        payload_cx: QROM_PAYLOAD_CX.load(Ordering::Relaxed),
    }
}

fn payload_operation_count(table: &[Vec<BitId>]) -> usize {
    table.iter().map(Vec::len).sum()
}

fn payload_operation_count_two(left: &[Vec<BitId>], right: &[Vec<BitId>]) -> usize {
    payload_operation_count(left) + payload_operation_count(right)
}

fn mbu_clear_and(circ: &mut B, target: QubitId, a: QubitId, b: QubitId) {
    let measurement = circ.alloc_bit();
    circ.hmr(target, measurement);
    circ.cz_if_bit(a, b, measurement);
    circ.zero_and_free(target);
}

fn xor_payload(circ: &mut B, selector: QubitId, target: &[QubitId], word: &[BitId]) {
    assert_eq!(target.len(), word.len());
    for (&qubit, &table_bit) in target.iter().zip(word) {
        circ.cx_if(selector, qubit, table_bit);
    }
}

fn xor_payload_without_selector(circ: &mut B, target: &[QubitId], word: &[BitId]) {
    assert_eq!(target.len(), word.len());
    for (&qubit, &table_bit) in target.iter().zip(word) {
        circ.x_if_bit(qubit, table_bit);
    }
}

fn xor_payload_pair(
    circ: &mut B,
    selector: QubitId,
    target: &[QubitId],
    junk: &[QubitId],
    table: &[Vec<BitId>],
    row: usize,
) {
    xor_payload(circ, selector, target, &table[2 * row]);
    xor_payload(circ, selector, junk, &table[2 * row + 1]);
}

/// Unary iteration over one address half. The CNOT reflection turns
/// `ctrl & top` into `ctrl & !top`, so each internal node needs one Toffoli
/// instead of constructing separate selectors for its two children.
fn load_tree(
    circ: &mut B,
    ctrl: QubitId,
    bits: &[QubitId],
    base: usize,
    target: &[QubitId],
    table: &[Vec<BitId>],
) {
    if bits.is_empty() {
        xor_payload(circ, ctrl, target, &table[base]);
        return;
    }

    let top = bits[bits.len() - 1];
    let rest = &bits[..bits.len() - 1];
    let half = 1usize << rest.len();
    let child = circ.alloc_qubit();
    circ.ccx(ctrl, top, child);
    load_tree(circ, child, rest, base + half, target, table);
    circ.cx(ctrl, child);
    load_tree(circ, child, rest, base, target, table);
    circ.cx(ctrl, child);
    mbu_clear_and(circ, child, ctrl, top);
}

fn emit_load(circ: &mut B, address: &[QubitId], target: &[QubitId], table: &[Vec<BitId>]) {
    if address.is_empty() {
        xor_payload_without_selector(circ, target, &table[0]);
        return;
    }
    let top = address[address.len() - 1];
    let rest = &address[..address.len() - 1];
    let half = 1usize << rest.len();
    load_tree(circ, top, rest, half, target, table);
    circ.x(top);
    load_tree(circ, top, rest, 0, target, table);
    circ.x(top);
}

fn load_two_tree(
    circ: &mut B,
    ctrl: QubitId,
    bits: &[QubitId],
    base: usize,
    left_target: &[QubitId],
    left_table: &[Vec<BitId>],
    right_target: &[QubitId],
    right_table: &[Vec<BitId>],
) {
    if bits.is_empty() {
        xor_payload(circ, ctrl, left_target, &left_table[base]);
        xor_payload(circ, ctrl, right_target, &right_table[base]);
        return;
    }

    let top = bits[bits.len() - 1];
    let rest = &bits[..bits.len() - 1];
    let half = 1usize << rest.len();
    let child = circ.alloc_qubit();
    circ.ccx(ctrl, top, child);
    load_two_tree(
        circ,
        child,
        rest,
        base + half,
        left_target,
        left_table,
        right_target,
        right_table,
    );
    circ.cx(ctrl, child);
    load_two_tree(
        circ,
        child,
        rest,
        base,
        left_target,
        left_table,
        right_target,
        right_table,
    );
    circ.cx(ctrl, child);
    mbu_clear_and(circ, child, ctrl, top);
}

fn emit_two_load(
    circ: &mut B,
    address: &[QubitId],
    left_target: &[QubitId],
    left_table: &[Vec<BitId>],
    right_target: &[QubitId],
    right_table: &[Vec<BitId>],
) {
    if address.is_empty() {
        xor_payload_without_selector(circ, left_target, &left_table[0]);
        xor_payload_without_selector(circ, right_target, &right_table[0]);
        return;
    }
    let top = address[address.len() - 1];
    let rest = &address[..address.len() - 1];
    let half = 1usize << rest.len();
    load_two_tree(
        circ,
        top,
        rest,
        half,
        left_target,
        left_table,
        right_target,
        right_table,
    );
    circ.x(top);
    load_two_tree(
        circ,
        top,
        rest,
        0,
        left_target,
        left_table,
        right_target,
        right_table,
    );
    circ.x(top);
}

fn load_pair_tree(
    circ: &mut B,
    ctrl: QubitId,
    bits: &[QubitId],
    base: usize,
    target: &[QubitId],
    junk: &[QubitId],
    table: &[Vec<BitId>],
) {
    if bits.is_empty() {
        xor_payload_pair(circ, ctrl, target, junk, table, base);
        return;
    }

    let top = bits[bits.len() - 1];
    let rest = &bits[..bits.len() - 1];
    let half = 1usize << rest.len();
    let child = circ.alloc_qubit();
    circ.ccx(ctrl, top, child);
    load_pair_tree(circ, child, rest, base + half, target, junk, table);
    circ.cx(ctrl, child);
    load_pair_tree(circ, child, rest, base, target, junk, table);
    circ.cx(ctrl, child);
    mbu_clear_and(circ, child, ctrl, top);
}

fn emit_qroam2_load(
    circ: &mut B,
    address: &[QubitId],
    target: &[QubitId],
    junk: &[QubitId],
    table: &[Vec<BitId>],
) {
    let high = &address[1..];
    let top = high[high.len() - 1];
    let rest = &high[..high.len() - 1];
    let half = 1usize << rest.len();
    load_pair_tree(circ, top, rest, half, target, junk, table);
    circ.x(top);
    load_pair_tree(circ, top, rest, 0, target, junk, table);
    circ.x(top);

    for (target_bit, junk_bit) in target.iter().zip(junk) {
        circ.cswap(address[0], *target_bit, *junk_bit);
    }
}

fn emit_qroam2_replay_unload(
    circ: &mut B,
    address: &[QubitId],
    target: &[QubitId],
    junk: &[QubitId],
    table: &[Vec<BitId>],
) {
    for (target_bit, junk_bit) in target.iter().zip(junk) {
        circ.cswap(address[0], *target_bit, *junk_bit);
    }

    let high = &address[1..];
    let top = high[high.len() - 1];
    let rest = &high[..high.len() - 1];
    let half = 1usize << rest.len();
    load_pair_tree(circ, top, rest, half, target, junk, table);
    circ.x(top);
    load_pair_tree(circ, top, rest, 0, target, junk, table);
    circ.x(top);
}

fn model_load(
    circ: &mut B,
    address: &[QubitId],
    table: &[Vec<BitId>],
    walk_phase: &'static str,
    clear_phase: &'static str,
) {
    let rows = table.len();
    let nodes = rows.saturating_sub(2);
    let payload_cx = payload_operation_count(table);

    circ.set_phase(walk_phase);
    let path = circ.alloc_qubits(address.len().saturating_sub(1));
    for qubit in path.into_iter().rev() {
        circ.loan_zero_qubit(qubit);
    }
    circ.add_counted_kind(OperationType::CCX, nodes);
    circ.add_counted_kind(
        OperationType::CX,
        2 * nodes + if address.is_empty() { 0 } else { payload_cx },
    );
    circ.add_counted_kind(OperationType::Hmr, nodes);
    circ.add_counted_kind(OperationType::CZ, nodes);
    circ.add_counted_kind(OperationType::R, nodes);
    circ.add_counted_kind(
        OperationType::X,
        if address.is_empty() { payload_cx } else { 2 },
    );
    circ.set_phase(clear_phase);
}

fn model_qroam2_load(
    circ: &mut B,
    address: &[QubitId],
    target: &[QubitId],
    table: &[Vec<BitId>],
    walk_phase: &'static str,
    clear_phase: &'static str,
) {
    let rows = table.len();
    let nodes = (rows / 2).saturating_sub(2);
    let payload_cx = payload_operation_count(table);

    circ.set_phase(walk_phase);
    let path = circ.alloc_qubits(address.len().saturating_sub(2));
    for qubit in path.into_iter().rev() {
        circ.loan_zero_qubit(qubit);
    }
    circ.add_counted_kind(OperationType::CCX, nodes + target.len());
    circ.add_counted_kind(OperationType::CX, 2 * nodes + payload_cx + 2 * target.len());
    circ.add_counted_kind(OperationType::Hmr, nodes);
    circ.add_counted_kind(OperationType::CZ, nodes);
    circ.add_counted_kind(OperationType::R, nodes);
    circ.add_counted_kind(OperationType::X, 2);
    circ.set_phase(clear_phase);
}

fn model_two_load(
    circ: &mut B,
    address: &[QubitId],
    left_table: &[Vec<BitId>],
    right_table: &[Vec<BitId>],
    walk_phase: &'static str,
    clear_phase: &'static str,
) {
    let rows = left_table.len();
    let nodes = rows.saturating_sub(2);
    let payload_cx = payload_operation_count_two(left_table, right_table);

    circ.set_phase(walk_phase);
    let path = circ.alloc_qubits(address.len().saturating_sub(1));
    for qubit in path.into_iter().rev() {
        circ.loan_zero_qubit(qubit);
    }
    circ.add_counted_kind(OperationType::CCX, nodes);
    circ.add_counted_kind(
        OperationType::CX,
        2 * nodes + if address.is_empty() { 0 } else { payload_cx },
    );
    circ.add_counted_kind(OperationType::Hmr, nodes);
    circ.add_counted_kind(OperationType::CZ, nodes);
    circ.add_counted_kind(OperationType::R, nodes);
    circ.add_counted_kind(
        OperationType::X,
        if address.is_empty() { payload_cx } else { 2 },
    );
    circ.set_phase(clear_phase);
}

fn prefer_qroam2(address: &[QubitId], target: &[QubitId]) -> bool {
    match std::env::var("WINDOWED_QROM_MODE").ok().as_deref() {
        Some("unary") => return false,
        Some("qroam2") => return address.len() >= 3 && target.len() == 256,
        _ => {}
    }
    address.len() >= 10 && target.len() == 256
}

/// XOR-loads one 256-bit word selected by the coherent little-endian address.
/// A full `2^w` table uses `2^w - 2` Toffolis and `w - 1` routing ancillas.
pub fn load_word(
    circ: &mut B,
    address: &[QubitId],
    target: &[QubitId],
    table: &[Vec<BitId>],
    walk_phase: &'static str,
    clear_phase: &'static str,
) -> QromWorkspace {
    assert_eq!(target.len(), 256);
    assert_eq!(table.len(), 1usize << address.len());

    let payload_cx = payload_operation_count(table);

    if prefer_qroam2(address, target) {
        let junk = circ.alloc_qubits(target.len());
        let nodes = (table.len() / 2).saturating_sub(2);
        let toffolis = nodes + target.len();
        QROM_CALLS.fetch_add(1, Ordering::Relaxed);
        QROM_TOFFOLIS.fetch_add(toffolis as u64, Ordering::Relaxed);
        QROM_PAYLOAD_CX.fetch_add(payload_cx as u64, Ordering::Relaxed);

        if std::env::var_os("WINDOWED_QROM_COUNT_ONLY").is_some() || circ.count_only {
            model_qroam2_load(circ, address, target, table, walk_phase, clear_phase);
        } else {
            circ.set_phase(walk_phase);
            emit_qroam2_load(circ, address, target, &junk, table);
            circ.set_phase(clear_phase);
        }
        return QromWorkspace::Qroam2(junk);
    }

    let nodes = table.len().saturating_sub(2);
    QROM_CALLS.fetch_add(1, Ordering::Relaxed);
    QROM_TOFFOLIS.fetch_add(nodes as u64, Ordering::Relaxed);
    QROM_PAYLOAD_CX.fetch_add(payload_cx as u64, Ordering::Relaxed);

    if std::env::var_os("WINDOWED_QROM_COUNT_ONLY").is_some() || circ.count_only {
        model_load(circ, address, table, walk_phase, clear_phase);
        return QromWorkspace::Unary;
    }

    circ.set_phase(walk_phase);
    emit_load(circ, address, target, table);
    circ.set_phase(clear_phase);
    QromWorkspace::Unary
}

/// XOR-loads two 256-bit columns selected by the same coherent address. The
/// columns share one unary address traversal and therefore use the same width
/// as a K=2 single-column lookup, but avoid duplicating its routing work.
pub fn load_two_words(
    circ: &mut B,
    address: &[QubitId],
    left_target: &[QubitId],
    left_table: &[Vec<BitId>],
    right_target: &[QubitId],
    right_table: &[Vec<BitId>],
    walk_phase: &'static str,
    clear_phase: &'static str,
) -> QromWorkspace {
    assert_eq!(left_target.len(), 256);
    assert_eq!(right_target.len(), 256);
    assert_eq!(left_table.len(), 1usize << address.len());
    assert_eq!(right_table.len(), left_table.len());

    let nodes = left_table.len().saturating_sub(2);
    let payload_cx = payload_operation_count_two(left_table, right_table);
    QROM_CALLS.fetch_add(1, Ordering::Relaxed);
    QROM_TOFFOLIS.fetch_add(nodes as u64, Ordering::Relaxed);
    QROM_PAYLOAD_CX.fetch_add(payload_cx as u64, Ordering::Relaxed);

    if std::env::var_os("WINDOWED_QROM_COUNT_ONLY").is_some() || circ.count_only {
        model_two_load(
            circ,
            address,
            left_table,
            right_table,
            walk_phase,
            clear_phase,
        );
        return QromWorkspace::Unary;
    }

    circ.set_phase(walk_phase);
    emit_two_load(
        circ,
        address,
        left_target,
        left_table,
        right_target,
        right_table,
    );
    circ.set_phase(clear_phase);
    QromWorkspace::Unary
}

fn deposit_phase_pair(
    circ: &mut B,
    a: QubitId,
    b: QubitId,
    measurements: &[BitId],
    word: &[BitId],
) {
    assert_eq!(measurements.len(), word.len());
    for (&measurement, &table_bit) in measurements.iter().zip(word) {
        circ.push_condition(table_bit);
        circ.cz_if_bit(a, b, measurement);
        circ.pop_condition();
    }
}

fn deposit_phase_single(
    circ: &mut B,
    selector: QubitId,
    measurements: &[BitId],
    word: &[BitId],
) {
    assert_eq!(measurements.len(), word.len());
    for (&measurement, &table_bit) in measurements.iter().zip(word) {
        circ.push_condition(table_bit);
        circ.z_if_bit(selector, measurement);
        circ.pop_condition();
    }
}

fn deposit_phase_without_selector(circ: &mut B, measurements: &[BitId], word: &[BitId]) {
    assert_eq!(measurements.len(), word.len());
    for (&measurement, &table_bit) in measurements.iter().zip(word) {
        circ.push_condition(table_bit);
        circ.push_condition(measurement);
        circ.neg();
        circ.pop_condition();
        circ.pop_condition();
    }
}

/// Phase-only unary iteration used after X-basis measurement of the lookup
/// target. At the bottom level the selected leaf is an AND of two live
/// selectors, so its phase can be deposited directly with a classically
/// conditioned CZ and the final selector ancilla is never materialized.
fn discharge_tree(
    circ: &mut B,
    ctrl: QubitId,
    bits: &[QubitId],
    base: usize,
    measurements: &[BitId],
    table: &[Vec<BitId>],
) {
    if bits.len() == 1 {
        let bit = bits[0];
        deposit_phase_pair(circ, ctrl, bit, measurements, &table[base + 1]);
        circ.x(bit);
        deposit_phase_pair(circ, ctrl, bit, measurements, &table[base]);
        circ.x(bit);
        return;
    }

    let top = bits[bits.len() - 1];
    let rest = &bits[..bits.len() - 1];
    let half = 1usize << rest.len();
    let child = circ.alloc_qubit();
    circ.ccx(ctrl, top, child);
    discharge_tree(circ, child, rest, base + half, measurements, table);
    circ.cx(ctrl, child);
    discharge_tree(circ, child, rest, base, measurements, table);
    circ.cx(ctrl, child);
    mbu_clear_and(circ, child, ctrl, top);
}

fn emit_discharge(
    circ: &mut B,
    address: &[QubitId],
    measurements: &[BitId],
    table: &[Vec<BitId>],
) {
    if address.is_empty() {
        deposit_phase_without_selector(circ, measurements, &table[0]);
        return;
    }
    let top = address[address.len() - 1];
    let rest = &address[..address.len() - 1];
    if rest.is_empty() {
        deposit_phase_single(circ, top, measurements, &table[1]);
        circ.x(top);
        deposit_phase_single(circ, top, measurements, &table[0]);
        circ.x(top);
        return;
    }

    let half = 1usize << rest.len();
    discharge_tree(circ, top, rest, half, measurements, table);
    circ.x(top);
    discharge_tree(circ, top, rest, 0, measurements, table);
    circ.x(top);
}

fn discharge_two_tree(
    circ: &mut B,
    ctrl: QubitId,
    bits: &[QubitId],
    base: usize,
    left_measurements: &[BitId],
    left_table: &[Vec<BitId>],
    right_measurements: &[BitId],
    right_table: &[Vec<BitId>],
) {
    if bits.len() == 1 {
        let bit = bits[0];
        deposit_phase_pair(
            circ,
            ctrl,
            bit,
            left_measurements,
            &left_table[base + 1],
        );
        deposit_phase_pair(
            circ,
            ctrl,
            bit,
            right_measurements,
            &right_table[base + 1],
        );
        circ.x(bit);
        deposit_phase_pair(circ, ctrl, bit, left_measurements, &left_table[base]);
        deposit_phase_pair(circ, ctrl, bit, right_measurements, &right_table[base]);
        circ.x(bit);
        return;
    }

    let top = bits[bits.len() - 1];
    let rest = &bits[..bits.len() - 1];
    let half = 1usize << rest.len();
    let child = circ.alloc_qubit();
    circ.ccx(ctrl, top, child);
    discharge_two_tree(
        circ,
        child,
        rest,
        base + half,
        left_measurements,
        left_table,
        right_measurements,
        right_table,
    );
    circ.cx(ctrl, child);
    discharge_two_tree(
        circ,
        child,
        rest,
        base,
        left_measurements,
        left_table,
        right_measurements,
        right_table,
    );
    circ.cx(ctrl, child);
    mbu_clear_and(circ, child, ctrl, top);
}

fn emit_two_discharge(
    circ: &mut B,
    address: &[QubitId],
    left_measurements: &[BitId],
    left_table: &[Vec<BitId>],
    right_measurements: &[BitId],
    right_table: &[Vec<BitId>],
) {
    if address.is_empty() {
        deposit_phase_without_selector(circ, left_measurements, &left_table[0]);
        deposit_phase_without_selector(circ, right_measurements, &right_table[0]);
        return;
    }
    let top = address[address.len() - 1];
    let rest = &address[..address.len() - 1];
    if rest.is_empty() {
        deposit_phase_single(circ, top, left_measurements, &left_table[1]);
        deposit_phase_single(circ, top, right_measurements, &right_table[1]);
        circ.x(top);
        deposit_phase_single(circ, top, left_measurements, &left_table[0]);
        deposit_phase_single(circ, top, right_measurements, &right_table[0]);
        circ.x(top);
        return;
    }
    let half = 1usize << rest.len();
    discharge_two_tree(
        circ,
        top,
        rest,
        half,
        left_measurements,
        left_table,
        right_measurements,
        right_table,
    );
    circ.x(top);
    discharge_two_tree(
        circ,
        top,
        rest,
        0,
        left_measurements,
        left_table,
        right_measurements,
        right_table,
    );
    circ.x(top);
}

fn deposit_phase_pair_banks(
    circ: &mut B,
    a: QubitId,
    b: QubitId,
    target_measurements: &[BitId],
    junk_measurements: &[BitId],
    table: &[Vec<BitId>],
    row: usize,
) {
    deposit_phase_pair(circ, a, b, target_measurements, &table[2 * row]);
    deposit_phase_pair(circ, a, b, junk_measurements, &table[2 * row + 1]);
}

fn discharge_pair_tree(
    circ: &mut B,
    ctrl: QubitId,
    bits: &[QubitId],
    base: usize,
    target_measurements: &[BitId],
    junk_measurements: &[BitId],
    table: &[Vec<BitId>],
) {
    if bits.len() == 1 {
        let bit = bits[0];
        deposit_phase_pair_banks(
            circ,
            ctrl,
            bit,
            target_measurements,
            junk_measurements,
            table,
            base + 1,
        );
        circ.x(bit);
        deposit_phase_pair_banks(
            circ,
            ctrl,
            bit,
            target_measurements,
            junk_measurements,
            table,
            base,
        );
        circ.x(bit);
        return;
    }

    let top = bits[bits.len() - 1];
    let rest = &bits[..bits.len() - 1];
    let half = 1usize << rest.len();
    let child = circ.alloc_qubit();
    circ.ccx(ctrl, top, child);
    discharge_pair_tree(
        circ,
        child,
        rest,
        base + half,
        target_measurements,
        junk_measurements,
        table,
    );
    circ.cx(ctrl, child);
    discharge_pair_tree(
        circ,
        child,
        rest,
        base,
        target_measurements,
        junk_measurements,
        table,
    );
    circ.cx(ctrl, child);
    mbu_clear_and(circ, child, ctrl, top);
}

fn emit_qroam2_discharge(
    circ: &mut B,
    address: &[QubitId],
    target_measurements: &[BitId],
    junk_measurements: &[BitId],
    table: &[Vec<BitId>],
) {
    let high = &address[1..];
    let top = high[high.len() - 1];
    let rest = &high[..high.len() - 1];
    let half = 1usize << rest.len();
    discharge_pair_tree(
        circ,
        top,
        rest,
        half,
        target_measurements,
        junk_measurements,
        table,
    );
    circ.x(top);
    discharge_pair_tree(
        circ,
        top,
        rest,
        0,
        target_measurements,
        junk_measurements,
        table,
    );
    circ.x(top);
}

fn model_measurement_unload(
    circ: &mut B,
    address: &[QubitId],
    target: &[QubitId],
    table: &[Vec<BitId>],
    measure_phase: &'static str,
    discharge_phase: &'static str,
) {
    let rows = table.len();
    let nodes = (rows / 2).saturating_sub(2);
    let payload_cz = payload_operation_count(table);

    circ.set_phase(measure_phase);
    circ.add_counted_kind(OperationType::Hmr, target.len());
    circ.add_counted_kind(OperationType::R, target.len());
    for qubit in target.iter().rev() {
        circ.loan_zero_qubit(*qubit);
    }

    circ.set_phase(discharge_phase);
    let path = circ.alloc_qubits(address.len().saturating_sub(2));
    for qubit in path.into_iter().rev() {
        circ.loan_zero_qubit(qubit);
    }
    circ.add_counted_kind(OperationType::CCX, nodes);
    circ.add_counted_kind(OperationType::CX, 2 * nodes);
    circ.add_counted_kind(OperationType::Hmr, nodes);
    circ.add_counted_kind(OperationType::CZ, nodes + payload_cz);
    circ.add_counted_kind(OperationType::R, nodes);
    circ.add_counted_kind(OperationType::X, 2 + 4 * (rows / 2));
    circ.add_counted_kind(OperationType::BitStore0, target.len());
}

fn model_qroam2_measurement_unload(
    circ: &mut B,
    address: &[QubitId],
    target: &[QubitId],
    junk: &[QubitId],
    table: &[Vec<BitId>],
    measure_phase: &'static str,
    discharge_phase: &'static str,
) {
    let rows = table.len();
    let nodes = (rows / 4).saturating_sub(2);
    let payload_cz = payload_operation_count(table);

    circ.set_phase(measure_phase);
    circ.add_counted_kind(OperationType::CCX, target.len());
    circ.add_counted_kind(OperationType::CX, 2 * target.len());
    circ.add_counted_kind(OperationType::Hmr, target.len() + junk.len());
    circ.add_counted_kind(OperationType::R, target.len() + junk.len());
    for qubit in target.iter().chain(junk).rev() {
        circ.loan_zero_qubit(*qubit);
    }

    circ.set_phase(discharge_phase);
    let path = circ.alloc_qubits(address.len().saturating_sub(3));
    for qubit in path.into_iter().rev() {
        circ.loan_zero_qubit(qubit);
    }
    circ.add_counted_kind(OperationType::CCX, nodes);
    circ.add_counted_kind(OperationType::CX, 2 * nodes);
    circ.add_counted_kind(OperationType::Hmr, nodes);
    circ.add_counted_kind(OperationType::CZ, nodes + payload_cz);
    circ.add_counted_kind(OperationType::R, nodes);
    circ.add_counted_kind(OperationType::X, 2 + 4 * (rows / 4));
    circ.add_counted_kind(OperationType::BitStore0, target.len() + junk.len());
}

fn model_two_measurement_unload(
    circ: &mut B,
    address: &[QubitId],
    left_target: &[QubitId],
    left_table: &[Vec<BitId>],
    right_target: &[QubitId],
    right_table: &[Vec<BitId>],
    measure_phase: &'static str,
    discharge_phase: &'static str,
) {
    let rows = left_table.len();
    let nodes = (rows / 2).saturating_sub(2);
    let payload_cz = payload_operation_count_two(left_table, right_table);

    circ.set_phase(measure_phase);
    circ.add_counted_kind(OperationType::Hmr, left_target.len() + right_target.len());
    circ.add_counted_kind(OperationType::R, left_target.len() + right_target.len());
    for qubit in left_target.iter().chain(right_target).rev() {
        circ.loan_zero_qubit(*qubit);
    }

    circ.set_phase(discharge_phase);
    let path = circ.alloc_qubits(address.len().saturating_sub(2));
    for qubit in path.into_iter().rev() {
        circ.loan_zero_qubit(qubit);
    }
    circ.add_counted_kind(OperationType::CCX, nodes);
    circ.add_counted_kind(OperationType::CX, 2 * nodes);
    circ.add_counted_kind(OperationType::Hmr, nodes);
    circ.add_counted_kind(OperationType::CZ, nodes + payload_cz);
    circ.add_counted_kind(OperationType::R, nodes);
    circ.add_counted_kind(OperationType::X, 2 + 4 * (rows / 2));
    circ.add_counted_kind(OperationType::BitStore0, left_target.len() + right_target.len());
}

/// Uncomputes a QROM-loaded target by X-basis measurement and phase-only
/// unary iteration. The target qubits are reset and released by this call.
/// A full `2^w` table with `w >= 2` uses `2^(w-1) - 2` Toffolis.
pub fn measurement_unload_word(
    circ: &mut B,
    address: &[QubitId],
    target: &[QubitId],
    table: &[Vec<BitId>],
    workspace: QromWorkspace,
    measure_phase: &'static str,
    discharge_phase: &'static str,
) {
    assert_eq!(target.len(), 256);
    assert_eq!(table.len(), 1usize << address.len());

    if let QromWorkspace::Qroam2(junk) = workspace {
        assert_eq!(junk.len(), target.len());
        let nodes = (table.len() / 4).saturating_sub(2);
        let toffolis = nodes + target.len();
        QROM_CALLS.fetch_add(1, Ordering::Relaxed);
        QROM_TOFFOLIS.fetch_add(toffolis as u64, Ordering::Relaxed);

        if std::env::var_os("WINDOWED_QROM_COUNT_ONLY").is_some() || circ.count_only {
            model_qroam2_measurement_unload(
                circ,
                address,
                target,
                &junk,
                table,
                measure_phase,
                discharge_phase,
            );
            return;
        }

        circ.set_phase(measure_phase);
        for (target_bit, junk_bit) in target.iter().zip(&junk) {
            circ.cswap(address[0], *target_bit, *junk_bit);
        }
        let target_measurements: Vec<BitId> = target
            .iter()
            .map(|qubit| {
                let measurement = circ.alloc_bit();
                circ.hmr(*qubit, measurement);
                circ.zero_and_free(*qubit);
                measurement
            })
            .collect();
        let junk_measurements: Vec<BitId> = junk
            .iter()
            .map(|qubit| {
                let measurement = circ.alloc_bit();
                circ.hmr(*qubit, measurement);
                circ.zero_and_free(*qubit);
                measurement
            })
            .collect();

        circ.set_phase(discharge_phase);
        emit_qroam2_discharge(
            circ,
            address,
            &target_measurements,
            &junk_measurements,
            table,
        );
        for measurement in target_measurements.into_iter().chain(junk_measurements) {
            circ.bit_store0(measurement);
        }
        return;
    }

    let nodes = (table.len() / 2).saturating_sub(2);
    QROM_CALLS.fetch_add(1, Ordering::Relaxed);
    QROM_TOFFOLIS.fetch_add(nodes as u64, Ordering::Relaxed);

    if std::env::var_os("WINDOWED_QROM_COUNT_ONLY").is_some() || circ.count_only {
        model_measurement_unload(circ, address, target, table, measure_phase, discharge_phase);
        return;
    }

    circ.set_phase(measure_phase);
    let measurements: Vec<BitId> = target
        .iter()
        .map(|qubit| {
            let measurement = circ.alloc_bit();
            circ.hmr(*qubit, measurement);
            circ.zero_and_free(*qubit);
            measurement
        })
        .collect();

    circ.set_phase(discharge_phase);
    emit_discharge(circ, address, &measurements, table);
    for measurement in measurements {
        circ.bit_store0(measurement);
    }
}

pub fn measurement_unload_two_words(
    circ: &mut B,
    address: &[QubitId],
    left_target: &[QubitId],
    left_table: &[Vec<BitId>],
    right_target: &[QubitId],
    right_table: &[Vec<BitId>],
    workspace: QromWorkspace,
    measure_phase: &'static str,
    discharge_phase: &'static str,
) {
    assert!(matches!(workspace, QromWorkspace::Unary));
    assert_eq!(left_target.len(), 256);
    assert_eq!(right_target.len(), 256);
    assert_eq!(left_table.len(), 1usize << address.len());
    assert_eq!(right_table.len(), left_table.len());

    let nodes = (left_table.len() / 2).saturating_sub(2);
    QROM_CALLS.fetch_add(1, Ordering::Relaxed);
    QROM_TOFFOLIS.fetch_add(nodes as u64, Ordering::Relaxed);

    if std::env::var_os("WINDOWED_QROM_COUNT_ONLY").is_some() || circ.count_only {
        model_two_measurement_unload(
            circ,
            address,
            left_target,
            left_table,
            right_target,
            right_table,
            measure_phase,
            discharge_phase,
        );
        return;
    }

    circ.set_phase(measure_phase);
    let left_measurements: Vec<BitId> = left_target
        .iter()
        .map(|qubit| {
            let measurement = circ.alloc_bit();
            circ.hmr(*qubit, measurement);
            circ.zero_and_free(*qubit);
            measurement
        })
        .collect();
    let right_measurements: Vec<BitId> = right_target
        .iter()
        .map(|qubit| {
            let measurement = circ.alloc_bit();
            circ.hmr(*qubit, measurement);
            circ.zero_and_free(*qubit);
            measurement
        })
        .collect();

    circ.set_phase(discharge_phase);
    emit_two_discharge(
        circ,
        address,
        &left_measurements,
        left_table,
        &right_measurements,
        right_table,
    );
    for measurement in left_measurements.into_iter().chain(right_measurements) {
        circ.bit_store0(measurement);
    }
}

fn replay_unload_word(
    circ: &mut B,
    address: &[QubitId],
    target: &[QubitId],
    table: &[Vec<BitId>],
    workspace: QromWorkspace,
    replay_phase: &'static str,
    clear_phase: &'static str,
) {
    assert_eq!(target.len(), 256);
    assert_eq!(table.len(), 1usize << address.len());

    match workspace {
        QromWorkspace::Qroam2(junk) => {
            let nodes = (table.len() / 2).saturating_sub(2);
            let toffolis = nodes + target.len();
            QROM_CALLS.fetch_add(1, Ordering::Relaxed);
            QROM_TOFFOLIS.fetch_add(toffolis as u64, Ordering::Relaxed);
            QROM_PAYLOAD_CX.fetch_add(payload_operation_count(table) as u64, Ordering::Relaxed);

            if std::env::var_os("WINDOWED_QROM_COUNT_ONLY").is_some() || circ.count_only {
                circ.set_phase(replay_phase);
                let path = circ.alloc_qubits(address.len().saturating_sub(2));
                for qubit in path.into_iter().rev() {
                    circ.loan_zero_qubit(qubit);
                }
                circ.add_counted_kind(OperationType::CCX, toffolis);
                circ.add_counted_kind(
                    OperationType::CX,
                    2 * nodes + payload_operation_count(table) + 2 * target.len(),
                );
                circ.add_counted_kind(OperationType::Hmr, nodes);
                circ.add_counted_kind(OperationType::CZ, nodes);
                circ.add_counted_kind(OperationType::R, nodes + target.len() + junk.len());
                circ.add_counted_kind(OperationType::X, 2);
                for qubit in target.iter().chain(&junk).rev() {
                    circ.loan_zero_qubit(*qubit);
                }
                circ.set_phase(clear_phase);
                return;
            }

            circ.set_phase(replay_phase);
            emit_qroam2_replay_unload(circ, address, target, &junk, table);
            circ.set_phase(clear_phase);
            for qubit in target.iter().chain(&junk).rev() {
                circ.zero_and_free(*qubit);
            }
        }
        QromWorkspace::Unary => {
            let nodes = table.len().saturating_sub(2);
            QROM_CALLS.fetch_add(1, Ordering::Relaxed);
            QROM_TOFFOLIS.fetch_add(nodes as u64, Ordering::Relaxed);
            QROM_PAYLOAD_CX.fetch_add(payload_operation_count(table) as u64, Ordering::Relaxed);

            if std::env::var_os("WINDOWED_QROM_COUNT_ONLY").is_some() || circ.count_only {
                model_load(circ, address, table, replay_phase, clear_phase);
                circ.add_counted_kind(OperationType::R, target.len());
                for qubit in target.iter().rev() {
                    circ.loan_zero_qubit(*qubit);
                }
                return;
            }

            circ.set_phase(replay_phase);
            emit_load(circ, address, target, table);
            circ.set_phase(clear_phase);
            for &qubit in target.iter().rev() {
                circ.zero_and_free(qubit);
            }
        }
    }
}

fn replay_unload_two_words(
    circ: &mut B,
    address: &[QubitId],
    left_target: &[QubitId],
    left_table: &[Vec<BitId>],
    right_target: &[QubitId],
    right_table: &[Vec<BitId>],
    workspace: QromWorkspace,
    replay_phase: &'static str,
    clear_phase: &'static str,
) {
    assert!(matches!(workspace, QromWorkspace::Unary));
    assert_eq!(left_target.len(), 256);
    assert_eq!(right_target.len(), 256);
    assert_eq!(left_table.len(), 1usize << address.len());
    assert_eq!(right_table.len(), left_table.len());

    let nodes = left_table.len().saturating_sub(2);
    let payload_cx = payload_operation_count_two(left_table, right_table);
    QROM_CALLS.fetch_add(1, Ordering::Relaxed);
    QROM_TOFFOLIS.fetch_add(nodes as u64, Ordering::Relaxed);
    QROM_PAYLOAD_CX.fetch_add(payload_cx as u64, Ordering::Relaxed);

    if std::env::var_os("WINDOWED_QROM_COUNT_ONLY").is_some() || circ.count_only {
        model_two_load(
            circ,
            address,
            left_table,
            right_table,
            replay_phase,
            clear_phase,
        );
        circ.add_counted_kind(OperationType::R, left_target.len() + right_target.len());
        for qubit in left_target.iter().chain(right_target).rev() {
            circ.loan_zero_qubit(*qubit);
        }
        return;
    }

    circ.set_phase(replay_phase);
    emit_two_load(
        circ,
        address,
        left_target,
        left_table,
        right_target,
        right_table,
    );
    circ.set_phase(clear_phase);
    for qubit in left_target.iter().chain(right_target).rev() {
        circ.zero_and_free(*qubit);
    }
}

pub fn unload_word(
    circ: &mut B,
    address: &[QubitId],
    target: &[QubitId],
    table: &[Vec<BitId>],
    workspace: QromWorkspace,
    unload_phase: &'static str,
    clear_phase: &'static str,
) {
    if std::env::var("WINDOWED_QROM_UNLOAD").ok().as_deref() == Some("split") {
        split_phase::unload_word(circ, address, target, table, workspace, unload_phase, clear_phase);
    } else if std::env::var("WINDOWED_QROM_UNLOAD").ok().as_deref() == Some("measurement") {
        measurement_unload_word(
            circ,
            address,
            target,
            table,
            workspace,
            unload_phase,
            clear_phase,
        );
    } else {
        replay_unload_word(
            circ,
            address,
            target,
            table,
            workspace,
            unload_phase,
            clear_phase,
        );
    }
}

pub fn unload_two_words(
    circ: &mut B,
    address: &[QubitId],
    left_target: &[QubitId],
    left_table: &[Vec<BitId>],
    right_target: &[QubitId],
    right_table: &[Vec<BitId>],
    workspace: QromWorkspace,
    unload_phase: &'static str,
    clear_phase: &'static str,
) {
    if std::env::var("WINDOWED_QROM_UNLOAD").ok().as_deref() == Some("split") {
        split_phase::unload_two_words(
            circ, address, left_target, left_table, right_target, right_table,
            workspace, unload_phase, clear_phase,
        );
    } else if std::env::var("WINDOWED_QROM_UNLOAD").ok().as_deref() == Some("measurement") {
        measurement_unload_two_words(
            circ,
            address,
            left_target,
            left_table,
            right_target,
            right_table,
            workspace,
            unload_phase,
            clear_phase,
        );
    } else {
        replay_unload_two_words(
            circ,
            address,
            left_target,
            left_table,
            right_target,
            right_table,
            workspace,
            unload_phase,
            clear_phase,
        );
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use alloy_primitives::U256;
    use crate::circuit::QubitOrBit;
    use crate::sim::Simulator;
    use sha3::{digest::ExtendableOutput, Shake256};

    fn run_qrom(unload: bool) -> (Vec<u64>, u64, Vec<QubitId>, Vec<QubitId>, u32) {
        let mut circ = B::new();
        let address = circ.alloc_qubits(3);
        let target = circ.alloc_qubits(256);
        let table_values: Vec<U256> =
            (0..8usize).map(|row| U256::from(row * 37 + 5)).collect();
        let table: Vec<Vec<BitId>> = (0..8usize).map(|_| circ.alloc_bits(256)).collect();
        let workspace = load_word(
            &mut circ,
            &address,
            &target,
            &table,
            "test_load_walk",
            "test_load_clear",
        );
        if unload {
            measurement_unload_word(
                &mut circ,
                &address,
                &target,
                &table,
                workspace,
                "test_unload_measure",
                "test_unload_discharge",
            );
        }

        let shake = Shake256::default();
        let mut xof = shake.finalize_xof();
        let mut sim = Simulator::new(circ.next_qubit as usize, circ.next_bit as usize, &mut xof);
        let address_reg: Vec<QubitOrBit> = address.iter().copied().map(QubitOrBit::Qubit).collect();
        let table_regs: Vec<Vec<QubitOrBit>> = table
            .iter()
            .map(|word| word.iter().copied().map(QubitOrBit::Bit).collect())
            .collect();
        for row in 0..8usize {
            sim.set_register(&address_reg, U256::from(row), row);
            for (table_reg, &value) in table_regs.iter().zip(&table_values) {
                sim.set_register(table_reg, value, row);
            }
        }
        sim.apply_iter(circ.ops.iter());
        (sim.qubits, sim.phase, address, target, circ.next_qubit)
    }

    fn lane_value(qubits: &[u64], register: &[QubitId], lane: usize) -> U256 {
        let mut value = U256::ZERO;
        for (bit, qubit) in register.iter().enumerate() {
            if (qubits[qubit.0 as usize] >> lane) & 1 != 0 {
                value.set_bit(bit, true);
            }
        }
        value
    }

    #[test]
    fn unary_qrom_selects_each_row_and_cleans_routing() {
        let (qubits, phase, address, target, total_qubits) = run_qrom(false);
        assert_eq!(
            phase & 0xff,
            0,
            "lookup must not leave address-dependent phase"
        );
        for row in 0..8usize {
            assert_eq!(lane_value(&qubits, &address, row), U256::from(row));
            assert_eq!(lane_value(&qubits, &target, row), U256::from(row * 37 + 5));
        }
        for qubit in (address.len() + target.len()) as u32..total_qubits {
            assert_eq!(
                qubits[qubit as usize] & 0xff,
                0,
                "routing q{qubit} is dirty"
            );
        }
    }

    #[test]
    fn measurement_unload_clears_target_and_phase() {
        let (qubits, phase, address, target, total_qubits) = run_qrom(true);
        assert_eq!(
            phase & 0xff,
            0,
            "unload must remove address-dependent phase"
        );
        for row in 0..8usize {
            assert_eq!(lane_value(&qubits, &address, row), U256::from(row));
            assert_eq!(lane_value(&qubits, &target, row), U256::ZERO);
        }
        for qubit in (address.len() + target.len()) as u32..total_qubits {
            assert_eq!(
                qubits[qubit as usize] & 0xff,
                0,
                "routing q{qubit} is dirty"
            );
        }
    }
}
