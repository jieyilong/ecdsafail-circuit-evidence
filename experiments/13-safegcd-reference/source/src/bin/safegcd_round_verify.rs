//! Reads a frozen KMX stream and independent scalar input/output vectors.
//! Uses the repository's original parser and simulator, not emitter simulation.
use quantum_ecc::circuit::{Circuit, OperationType, NO_BIT};
use quantum_ecc::sim::Simulator;
use sha3::{digest::ExtendableOutput, Shake256};
use std::fs::File;
use std::io::{BufRead, BufReader};

fn main() {
    let args: Vec<_> = std::env::args().collect();
    assert_eq!(args.len(), 4, "kmx vectors result.json");
    let mut circuit = Circuit::from_kmx(&args[1]).unwrap();
    if std::env::var_os("VERIFY_REVERSE").is_some() {
        circuit.operations.reverse();
    }
    let static_t = circuit.operations.iter()
        .filter(|op| op.kind == OperationType::CCX).count() as u64;
    for op in &circuit.operations {
        assert!(matches!(op.kind, OperationType::X | OperationType::CX | OperationType::CCX));
        assert_eq!(op.c_condition, NO_BIT);
    }
    assert_eq!(circuit.num_bits, 0);
    let mut reader = Shake256::default().finalize_xof();
    let mut sim = Simulator::new(circuit.num_qubits as usize, 0, &mut reader);
    let mut lines = BufReader::new(File::open(&args[2]).unwrap()).lines();
    let mut cases = 0_u64;
    let report_failures = std::env::var_os("VERIFY_REPORT_FAILURES").is_some();
    let mut output_failures = 0_u64;
    let mut scratch_failures = 0_u64;
    let mut any_failures = 0_u64;
    loop {
        let mut batch = Vec::new();
        for _ in 0..64 {
            match lines.next() {
                Some(line) => {
                    let line = line.unwrap();
                    let (input, output) = line.split_once(' ').unwrap();
                    assert_eq!(input.len(), sim.num_qubits);
                    assert_eq!(output.len(), sim.num_qubits);
                    batch.push((input.as_bytes().to_vec(), output.as_bytes().to_vec()));
                }
                None => break,
            }
        }
        if batch.is_empty() { break; }
        sim.clear_for_shot();
        let mask = if batch.len() == 64 { u64::MAX } else { (1_u64 << batch.len()) - 1 };
        for (lane, (input, _)) in batch.iter().enumerate() {
            for (q, bit) in input.iter().enumerate() {
                assert!(*bit == b'0' || *bit == b'1');
                sim.qubits[q] |= ((*bit == b'1') as u64) << lane;
            }
        }
        let before = sim.qubits.clone();
        let t0 = sim.stats.toffoli_gates;
        sim.apply_iter_masked(circuit.operations.iter(), mask);
        assert_eq!(sim.phase, 0, "forward phase garbage");
        for (lane, (_, output)) in batch.iter().enumerate() {
            let mut output_bad = false;
            let mut scratch_bad = false;
            for (q, bit) in output.iter().enumerate() {
                assert!(*bit == b'0' || *bit == b'1');
                let bad = (sim.qubits[q] >> lane) & 1 != (*bit == b'1') as u64;
                if report_failures {
                    if q < 512 { output_bad |= bad; } else { scratch_bad |= bad; }
                } else {
                    assert!(!bad, "forward mismatch case={} q={}", cases + lane as u64, q);
                }
            }
            output_failures += output_bad as u64;
            scratch_failures += scratch_bad as u64;
            any_failures += (output_bad || scratch_bad) as u64;
        }
        assert_eq!(sim.stats.toffoli_gates - t0, static_t * batch.len() as u64);
        sim.apply_iter_masked(circuit.operations.iter().rev(), mask);
        assert_eq!(sim.qubits, before, "inverse failed exact full-wire restoration");
        assert_eq!(sim.phase, 0, "inverse phase garbage");
        assert_eq!(sim.stats.toffoli_gates - t0, 2 * static_t * batch.len() as u64);
        cases += batch.len() as u64;
    }
    let scope = std::env::var("VERIFY_SCOPE").unwrap_or_else(|_| "controller/value round only".to_string());
    let result = format!(
        "{{\n  \"status\": \"PASS\",\n  \"simulator\": \"original quantum_ecc::sim::Simulator\",\n  \"scope\": \"{}\",\n  \"Q\": {},\n  \"static_T_forward\": {},\n  \"static_T_inverse\": {},\n  \"forward_inverse_cases\": {},\n  \"executed_Toffolis_all_cases_both_directions\": {},\n  \"phase_and_all_scratch_restored\": true\n}}\n",
        scope, circuit.num_qubits, static_t, static_t, cases, sim.stats.toffoli_gates);
    let result = if report_failures {
        let status = if any_failures == 0 { "PASS" } else { "FAIL" };
        format!("{{\"status\":\"{}\",\"scope\":\"{}\",\"Q\":{},\"static_T\":{},\"cases\":{},\"output_failures\":{},\"scratch_failures\":{},\"any_failures\":{},\"inverse_restoration\":true,\"phase_failures\":0}}\n",
                status, scope, circuit.num_qubits, static_t, cases, output_failures, scratch_failures, any_failures)
    } else { result };
    std::fs::write(&args[3], &result).unwrap();
    print!("{}", result);
}
