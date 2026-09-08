//! Observation-only entrypoints. The original Simulator and arithmetic oracle are used verbatim.
use super::*;
use std::cell::{Cell, RefCell};

#[derive(Clone)]
struct Mark {
    index: usize,
    label: &'static str,
    round: usize,
    registers: Vec<Vec<QubitOrBit>>,
}

thread_local! {
    static ENABLED: Cell<bool> = const { Cell::new(false) };
    static ROUND: Cell<usize> = const { Cell::new(0) };
    static MARKS: RefCell<Vec<Mark>> = const { RefCell::new(Vec::new()) };
}

pub(super) fn round(value: usize) { ROUND.with(|v| v.set(value)); }

pub(super) fn mark(b: &B, label: &'static str, registers: &[&[QubitId]]) {
    if !ENABLED.with(|v| v.get()) { return; }
    MARKS.with(|v| v.borrow_mut().push(Mark {
        index: b.ops.len(), label, round: ROUND.with(|v| v.get()),
        registers: registers.iter().map(|r| reg(r)).collect(),
    }));
}

fn reg(q: &[QubitId]) -> Vec<QubitOrBit> {
    q.iter().copied().map(QubitOrBit::Qubit).collect()
}

pub(super) fn seed_window() -> usize {
    if std::env::var("QIP_BOUNDARY_VARIANT").as_deref() == Ok("full_width") { N } else { 32 }
}

fn zero_into(b: &mut B, value: &[QubitId], output: QubitId) {
    for &q in value { b.x(q); }
    let mut products = Vec::new();
    products.push(and_clean(b, value[0], value[1]));
    for &q in &value[2..] {
        products.push(and_clean(b, *products.last().unwrap(), q));
    }
    b.cx(*products.last().unwrap(), output);
    for i in (1..products.len()).rev() {
        and_uncompute(b, products[i], products[i - 1], value[i + 1]);
    }
    and_uncompute(b, products[0], value[0], value[1]);
    for &q in value { b.x(q); }
}

// Only a local canonical-input negation candidate, never installed in replay.
fn canonical_negate_exact(b: &mut B, control: QubitId, value: &[QubitId]) {
    let zero = b.alloc_qubit();
    zero_into(b, value, zero);
    b.x(zero);
    let effective = and_clean(b, control, zero);
    for &q in value { b.cx(effective, q); }
    csub_nbit_const_direct_trunc_fast(b, value, U256::MAX - SECP256K1_P, effective, N);
    and_uncompute(b, effective, control, zero);
    b.x(zero);
    zero_into(b, value, zero);
    b.free(zero);
}

fn cells() {
    let p = SECP256K1_P;
    let f = U256::MAX - p + U256::from(1);
    let values = [U256::ZERO, U256::from(1), U256::from(2), f - U256::from(1), f,
        f + U256::from(1), p / U256::from(2), p - U256::from(2), p - U256::from(1), p];
    println!("CELL_HEADER kernel,sign,source,target,got,expected,word_bad,field_bad,phase,ancilla,source_bad,control_bad,toffoli_sum64,peak,emitted_toffoli");
    for kernel in ["negate", "canonical_negate_exact", "seed", "halve", "double", "signed_add", "fused_halve", "fused_double"] {
        let mut b = B::new();
        let sign = b.alloc_qubit();
        let source = b.alloc_qubits(N);
        let target = b.alloc_qubits(N);
        let live = b.active_qubits;
        match kernel {
            "negate" => conditional_mod_negate(&mut b, sign, &target),
            "canonical_negate_exact" => canonical_negate_exact(&mut b, sign, &target),
            "seed" => seed_round_one(&mut b, sign, &source, &target),
            "halve" => mod_halve_pm(&mut b, &target),
            "double" => mod_double_pm(&mut b, &target),
            "signed_add" => signed_mod_add_pm(&mut b, sign, &source, &target),
            "fused_halve" => signed_mod_add_pm_halve_fused(&mut b, sign, &source, &target),
            "fused_double" => signed_mod_double_add_pm_fused(&mut b, sign, &source, &target),
            _ => unreachable!(),
        }
        assert_eq!(b.active_qubits, live);
        let peak = b.peak_qubits;
        let nq = b.next_qubit as usize;
        let nb = b.next_bit as usize;
        let ops = b.take_ops();
        let emitted = ops.iter().filter(|o| matches!(o.kind, OperationType::CCX | OperationType::CCZ)).count();
        let sr = reg(&source);
        let tr = reg(&target);
        let mut cases = Vec::new();
        for s in 0..2 {
            for &a in &values {
                for &t in &values {
                    if kernel == "seed" && t != U256::ZERO { continue; }
                    if ["negate", "canonical_negate_exact", "halve", "double"].contains(&kernel) && a != U256::ZERO { continue; }
                    cases.push((s, a, t));
                }
            }
        }
        for batch in cases.chunks(64) {
            let mut hash = Shake256::default();
            hash.update(b"qip-boundary-cells-v1");
            let mut reader = hash.finalize_xof();
            let mut sim = Simulator::new(nq, nb, &mut reader);
            for (lane, &(s, a, t)) in batch.iter().enumerate() {
                sim.set_register(&sr, a, lane);
                sim.set_register(&tr, t, lane);
                *sim.qubit_mut(sign) |= (s as u64) << lane;
            }
            sim.apply_iter(ops.iter());
            let dirty = sim.qubits.iter().enumerate().filter(|(i, _)| *i > 512).fold(0, |a, (_, &v)| a | v);
            for (lane, &(s, a, t)) in batch.iter().enumerate() {
                let a0 = a % p;
                let t0 = t % p;
                let signed = if s == 0 || a0 == U256::ZERO { a0 } else { p - a0 };
                let inv2 = (p >> 1) + U256::from(1);
                let expected = match kernel {
                    "negate" | "canonical_negate_exact" => if s == 0 || t0 == U256::ZERO { t0 } else { p - t0 },
                    "seed" => signed,
                    "halve" => t0.mul_mod(inv2, p),
                    "double" => t0.add_mod(t0, p),
                    "signed_add" => t0.add_mod(signed, p),
                    "fused_halve" => t0.add_mod(signed, p).mul_mod(inv2, p),
                    "fused_double" => t0.add_mod(t0, p).add_mod(signed, p),
                    _ => unreachable!(),
                };
                let got = sim.get_register(&tr, lane);
                println!("CELL {kernel},{s},{a:#x},{t:#x},{got:#x},{expected:#x},{},{},{},{},{},{},{},{peak},{emitted}",
                    u8::from(got != expected), u8::from(got % p != expected), (sim.phase >> lane) & 1,
                    (dirty >> lane) & 1, u8::from(sim.get_register(&sr, lane) != a),
                    u8::from(((sim.qubit(sign) >> lane) & 1) != s as u64), sim.stats.toffoli_gates);
            }
        }
    }
}

fn component() {
    ENABLED.with(|v| v.set(true));
    let text = std::fs::read_to_string("probe-denominators.txt").unwrap();
    let values: Vec<U256> = text.lines().map(|s| U256::from_str_radix(s.trim_start_matches("0x"), 16).unwrap()).collect();
    for direction in [PingPongDirection::Divide, PingPongDirection::Multiply] {
        MARKS.with(|v| v.borrow_mut().clear());
        round(0);
        let mut b = B::new();
        let d = b.alloc_qubits(N);
        let n = b.alloc_qubits(N);
        pingpong_mod_mul_div_in_place(&mut b, &d, &n, direction);
        let nq = b.next_qubit as usize;
        let nb = b.next_bit as usize;
        let peak = b.peak_qubits;
        let ops = b.take_ops();
        assert!(ops.len() * std::mem::size_of::<Op>() < 900_000_000, "component memory cap");
        let marks = MARKS.with(|v| std::mem::take(&mut *v.borrow_mut()));
        let dr = reg(&d);
        let nr = reg(&n);
        let mut hash = Shake256::default();
        hash.update(b"qip-posthoc-zero-payload-probe-v1");
        let mut reader = hash.finalize_xof();
        let mut sim = Simulator::new(nq, nb, &mut reader);
        for (lane, &value) in values.iter().enumerate() { sim.set_register(&dr, value, lane); }
        let mut start = 0;
        let mut previous_phase = 0;
        for m in &marks {
            let slice = &ops[start..m.index];
            assert_balanced(slice);
            sim.apply_iter(slice.iter());
            if m.label == "coefficient_before_free" {
                let mask = m.registers[0].iter().fold(0u64, |a, q| match q {
                    QubitOrBit::Qubit(q) => a | sim.qubit(*q), _ => unreachable!(),
                });
                println!("PRERESET {direction:?} coefficient_nonzero={mask:#018x} phase={:#018x}", sim.phase);
            }
            if m.label == "coefficient_after_free" {
                println!("POSTRESET {direction:?} phase={:#018x}", sim.phase);
            }
            // Lane 0 is the smallest fixture index, lane 2 the first Divide output-p case.
            for lane in [0, 2, 4] {
                let words: Vec<_> = m.registers.iter().map(|r| format!("{:#x}", sim.get_register(r, lane))).collect();
                println!("TRACE {direction:?} lane={lane} round={} op={} label={} regs={} phase={}",
                    m.round, m.index, m.label, words.join(":"), (sim.phase >> lane) & 1);
            }
            if sim.phase != previous_phase {
                println!("PHASE_DELTA {direction:?} round={} start={start} end={} label={} mask={:#018x}", m.round, m.index, m.label, sim.phase ^ previous_phase);
            }
            previous_phase = sim.phase;
            start = m.index;
        }
        assert_balanced(&ops[start..]);
        sim.apply_iter(ops[start..].iter());
        let mut out = 0u64;
        let mut denom = 0u64;
        let mut noncanonical = 0u64;
        for (lane, &value) in values.iter().enumerate() {
            let got = sim.get_register(&nr, lane);
            if got != U256::ZERO { out |= 1 << lane; }
            if got == SECP256K1_P { noncanonical |= 1 << lane; }
            if sim.get_register(&dr, lane) != value { denom |= 1 << lane; }
        }
        let dirty = sim.qubits[512..].iter().fold(0, |a, v| a | v);
        println!("COMPONENT {direction:?} output={out:#018x} output_p={noncanonical:#018x} denominator={denom:#018x} phase={:#018x} ancilla={dirty:#018x} peak={peak} toffoli_sum64={} ops={} bytes={}",
            sim.phase, sim.stats.toffoli_gates, ops.len(), ops.len() * std::mem::size_of::<Op>());
        let mut hash = Shake256::default();
        hash.update(b"qip-posthoc-zero-payload-probe-v1");
        let mut reader2 = hash.finalize_xof();
        let mut whole = Simulator::new(nq, nb, &mut reader2);
        for (lane, &value) in values.iter().enumerate() { whole.set_register(&dr, value, lane); }
        whole.apply_iter(ops.iter());
        assert_eq!(whole.phase, sim.phase);
        assert_eq!(whole.qubits, sim.qubits);
        assert_eq!(whole.bits, sim.bits);
        assert_eq!(whole.stats, sim.stats);
        println!("SPLIT_EQ_UNSPLIT {direction:?} phase,qubits,bits,stats");
    }
}

struct SingleDraw { hot: usize, tick: usize }

impl XofReader for SingleDraw {
    fn read(&mut self, out: &mut [u8]) {
        assert_eq!(out.len(), 8);
        out.fill(if self.tick == self.hot { 255 } else { 0 });
        self.tick += 1;
    }
}

fn witnesses() {
    std::env::set_var("TRACE_OP_SITES", "1");
    ENABLED.with(|v| v.set(true));
    let p = SECP256K1_P;
    for (name, s, a, t) in [
        ("signed_add", 1, U256::from(1), U256::ZERO),
        ("fused_halve", 1, U256::from(2), U256::ZERO),
        ("fused_halve", 0, p, U256::ZERO),
        ("fused_halve", 0, p, p),
        ("fused_double", 0, p, p),
        ("fused_double", 1, p, p),
    ] {
        MARKS.with(|v| v.borrow_mut().clear());
        let mut b = B::new();
        let sign = b.alloc_qubit();
        let source = b.alloc_qubits(N);
        let target = b.alloc_qubits(N);
        match name {
            "signed_add" => signed_mod_add_pm(&mut b, sign, &source, &target),
            "fused_halve" => signed_mod_add_pm_halve_fused(&mut b, sign, &source, &target),
            "fused_double" => signed_mod_double_add_pm_fused(&mut b, sign, &source, &target),
            _ => unreachable!(),
        }
        let nq = b.next_qubit as usize;
        let nb = b.next_bit as usize;
        let ops = b.take_ops();
        let sites = take_last_op_sites();
        assert_eq!(sites.len(), ops.len());
        let marks = MARKS.with(|v| std::mem::take(&mut *v.borrow_mut()));
        let random_ops: Vec<_> = ops.iter().enumerate().filter(|(_, o)| matches!(o.kind, OperationType::Hmr | OperationType::R)).collect();
        println!("WITNESS {name} sign={s} source={a:#x} target={t:#x} ops={} randomness_events={}", ops.len(), random_ops.len());
        let mut uncancelled = Vec::new();
        for hot in 0..=random_ops.len() {
            let mut reader = SingleDraw { hot, tick: 0 };
            let mut sim = Simulator::new(nq, nb, &mut reader);
            *sim.qubit_mut(sign) = if s == 1 { u64::MAX } else { 0 };
            for lane in 0..64 {
                sim.set_register(&reg(&source), a, lane);
                sim.set_register(&reg(&target), t, lane);
            }
            sim.apply_iter(ops.iter());
            if sim.phase != 0 || hot == random_ops.len() {
                if hot < random_ops.len() {
                    uncancelled.push(hot);
                    let (index, op) = random_ops[hot];
                    let label = marks.iter().rev().find(|m| m.index <= index).map(|m| m.label).unwrap_or("entry");
                    println!("UNCANCELLED hot={hot} op={index} kind={:?} qubit={} bit={} site={}:{} context={label} phase={:#018x}",
                        op.kind, op.q_target.0, op.c_target.0, sites[index].0, sites[index].1, sim.phase);
                    let mut paired_reader = SingleDraw { hot, tick: 0 };
                    let mut paired = Simulator::new(nq, nb, &mut paired_reader);
                    *paired.qubit_mut(sign) = if s == 1 { u64::MAX } else { 0 };
                    for lane in 32..64 {
                        paired.set_register(&reg(&source), a, lane);
                        paired.set_register(&reg(&target), t, lane);
                    }
                    paired.apply_iter(ops.iter());
                    assert_eq!(paired.phase, 0xffff_ffff_0000_0000, "input-dependent, not a common global phase");
                    println!("PAIRED hot={hot} zero_controls_vs_witness phase={:#018x}", paired.phase);
                } else {
                    println!("ALL_ZERO_RANDOM phase={:#018x} got={:#x}", sim.phase, sim.get_register(&reg(&target), 0));
                }
            }
        }
        for seed in 0u8..8 {
            let mut h = Shake256::default();
            h.update(b"qip-boundary-phase-rule-v1");
            h.update(&[seed]);
            let mut r = h.clone().finalize_xof();
            let mut oracle_random = h.finalize_xof();
            let mut predicted = 0u64;
            for tick in 0..random_ops.len() {
                let mut buf = [0u8; 8];
                oracle_random.read(&mut buf);
                if uncancelled.contains(&tick) { predicted ^= u64::from_le_bytes(buf); }
            }
            let mut sim = Simulator::new(nq, nb, &mut r);
            *sim.qubit_mut(sign) = if s == 1 { u64::MAX } else { 0 };
            for lane in 0..64 {
                sim.set_register(&reg(&source), a, lane);
                sim.set_register(&reg(&target), t, lane);
            }
            sim.apply_iter(ops.iter());
            assert_eq!(sim.phase, predicted, "one-hot phase rule on random measurement assignments");
        }
        println!("PHASE_RULE_CHECK seeds=8 lanes_per_seed=64 matched=true");
    }
}

fn local_regression() {
    let p = SECP256K1_P;
    let f = U256::MAX - p + U256::from(1);
    let mut values: Vec<U256> = (0u64..64).map(U256::from).collect();
    values.extend([f - U256::from(1), f, f + U256::from(1), p >> 1, (p >> 1) + U256::from(1), p - U256::from(2), p - U256::from(1)]);
    for i in 0..256 {
        let x = U256::from(1) << i;
        values.push(x);
        values.push(p - x);
    }
    values.sort();
    values.dedup();
    let mut b = B::new();
    let sign = b.alloc_qubit();
    let target = b.alloc_qubits(N);
    canonical_negate_exact(&mut b, sign, &target);
    assert_eq!(b.active_qubits, 257);
    let peak = b.peak_qubits;
    let nq = b.next_qubit as usize;
    let nb = b.next_bit as usize;
    let ops = b.take_ops();
    let emitted = ops.iter().filter(|o| matches!(o.kind, OperationType::CCX | OperationType::CCZ)).count();
    let cases: Vec<_> = [0u64, 1].into_iter().flat_map(|s| values.iter().map(move |&t| (s, t))).collect();
    let tr = reg(&target);
    let mut total_toffoli = 0;
    for seed in 0u8..8 {
        for (batch_index, batch) in cases.chunks(64).enumerate() {
            let mut h = Shake256::default();
            h.update(b"qip-canonical-negation-boundary-regression-v1");
            h.update(&[seed]);
            h.update(&(batch_index as u64).to_le_bytes());
            let mut r = h.finalize_xof();
            let mut sim = Simulator::new(nq, nb, &mut r);
            for (lane, &(s, t)) in batch.iter().enumerate() {
                *sim.qubit_mut(sign) |= s << lane;
                sim.set_register(&tr, t, lane);
            }
            let mask = if batch.len() == 64 { u64::MAX } else { (1 << batch.len()) - 1 };
            sim.apply_iter_masked(ops.iter(), mask);
            assert_eq!(sim.phase & mask, 0);
            for q in &sim.qubits[257..] { assert_eq!(q & mask, 0); }
            for (lane, &(s, t)) in batch.iter().enumerate() {
                let expected = if s == 0 || t == U256::ZERO { t } else { p - t };
                assert_eq!(sim.get_register(&tr, lane), expected);
                assert_eq!((sim.qubit(sign) >> lane) & 1, s);
            }
            total_toffoli += sim.stats.toffoli_gates;
        }
    }
    println!("LOCAL_REGRESSION kernel=canonical_negate_exact canonical_values={} sign_cases={} seeds=8 total_shots={} word_bad=0 field_bad=0 phase=0 ancilla=0 control_bad=0 peak={peak} emitted_toffoli={emitted} toffoli_sum={total_toffoli} mean_toffoli={}",
        values.len(), cases.len(), cases.len() * 8, total_toffoli as f64 / (cases.len() * 8) as f64);
    println!("SCOPE canonical-input negation only; not inserted in replay; noncanonical input p is outside contract and its negative test is retained in cells logs");
}

fn assert_balanced(ops: &[Op]) {
    let mut depth = 0i32;
    for o in ops {
        match o.kind {
            OperationType::PushCondition => depth += 1,
            OperationType::PopCondition => depth -= 1,
            _ => {},
        }
        assert!(depth >= 0);
    }
    assert_eq!(depth, 0);
}

pub(crate) fn run() {
    match std::env::var("QIP_BOUNDARY_MODE").unwrap().as_str() {
        "cells" => cells(),
        "component" => component(),
        "witnesses" => witnesses(),
        "local_regression" => local_regression(),
        other => panic!("unsupported bounded mode {other}"),
    }
}
