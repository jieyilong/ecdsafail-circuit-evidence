//! TRUSTED stage of the challenge harness.
//!
//! Reads the op stream produced by `build_circuit` from `ops.bin`,
//! re-simulates the circuit against the secp256k1 reference adder,
//! enforces the four validity checks (correctness, reversibility, phase,
//! ancilla cleanup), counts gates, writes `score.json`, and appends one
//! row to `results.tsv`.
//!
//! This binary deliberately does NOT import `quantum_ecc::point_add` —
//! contestant code never executes inside the trusted process. `ops.bin`
//! is treated as fully untrusted input and is bounds-checked before use.

use alloy_primitives::U256;
use quantum_ecc::circuit::{
    analyze_ops, BitId, Op, OperationType, QubitId, QubitOrBit, RegisterId,
};
use quantum_ecc::sim::Simulator;
use quantum_ecc::weierstrass_elliptic_curve::WeierstrassEllipticCurve;
use sha3::{
    digest::{ExtendableOutput, Update, XofReader},
    Shake256,
};
use std::collections::HashSet;
use std::fmt::Write as FmtWrite;
use std::fs::{File, OpenOptions};
use std::io::{BufReader, Read, Write};
use std::path::{Path, PathBuf};
use std::process::Command;
use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::Mutex;
use std::time::{SystemTime, UNIX_EPOCH};

const OPS_PATH: &str = "ops.bin";
// "Z" framing: 16-byte plaintext header (MAGIC + u64 count) then a zstd
// frame of the fixed-width records. The count is read before decompressing
// so we can bound memory, and we read exactly count*OP_BYTES bytes out of
// the decoder so a crafted frame cannot expand without bound.
const MAGIC: &[u8; 8] = b"QECCOPSZ";
// Cap the zstd window the decoder will accept (2^27 = 128 MiB). A forged
// ops.bin cannot force a huge decompression-window allocation.
const ZSTD_WINDOW_LOG_MAX: u32 = 27;
const FIELD_BYTES: usize = 8;
const OP_FIELDS: usize = 7;
const OP_BYTES: usize = OP_FIELDS * FIELD_BYTES;
// Resource caps. These are sanity limits to prevent a malicious ops.bin
// from OOM'ing the simulator (each qubit/bit costs 8 bytes in `Simulator::new`).
// Real circuits sit ~3k qubits and a few hundred million ops; caps are
// generous compared to that.
const MAX_OPS: u64 = 4_000_000_000;
const NUM_TESTS: usize = 9024;

// ─── Bounded ops.bin loader ────────────────────────────────────────────────
//
// Hand-rolled fixed-width LE framing. Per-op layout:
//   u32 kind (must be 0..=17 — rejects the rkyv jump-table-confusion attack
//             that bypassed the Toffoli counter in the Google challenge)
//   u32 _pad
//   u64 q_control2  (NO_QUBIT = u64::MAX = unused)
//   u64 q_control1
//   u64 q_target
//   u64 c_target    (NO_BIT = u64::MAX)
//   u64 c_condition
//   u64 r_target    (NO_REG = u64::MAX)
//
// After reassembly, each Op is fed to Op::validate() (upstream zkp_ecc
// post-incident hardening). validate() panics on:
//   - operand aliasing (CCX q q q etc. — would yield free non-reversible
//     resets, the ToB "strictly better exploit primitive")
//   - per-kind field-shape violations (e.g. R/Hmr with c_condition,
//     which would suppress phase randomization on dirty frees)
// We catch_unwind so a forged ops.bin produces an error, not a crash.

fn op_kind_from_u32(v: u32) -> Option<OperationType> {
    Some(match v {
        0 => OperationType::Neg,
        1 => OperationType::Register,
        2 => OperationType::AppendToRegister,
        3 => OperationType::BitInvert,
        4 => OperationType::BitStore0,
        5 => OperationType::BitStore1,
        6 => OperationType::X,
        7 => OperationType::Z,
        8 => OperationType::CX,
        9 => OperationType::CZ,
        10 => OperationType::Swap,
        11 => OperationType::R,
        12 => OperationType::Hmr,
        13 => OperationType::CCX,
        14 => OperationType::CCZ,
        15 => OperationType::PushCondition,
        16 => OperationType::PopCondition,
        17 => OperationType::DebugPrint,
        _ => return None,
    })
}

fn read_u64(bytes: &[u8], off: usize) -> u64 {
    u64::from_le_bytes(bytes[off..off + 8].try_into().unwrap())
}

fn load_ops(path: &str) -> Result<Vec<Op>, String> {
    let mut file = File::open(path).map_err(|e| format!("open {path}: {e}"))?;

    // Plaintext header: MAGIC + u64 op count. Read and validate before
    // decompressing so the op count bounds every allocation below.
    let mut header = [0u8; MAGIC.len() + 8];
    file.read_exact(&mut header)
        .map_err(|e| format!("{path}: too short to read header: {e}"))?;
    if &header[..MAGIC.len()] != MAGIC {
        return Err(format!("{path}: bad magic"));
    }
    let n = u64::from_le_bytes(header[MAGIC.len()..].try_into().unwrap());
    if n > MAX_OPS {
        return Err(format!("{path}: op count {n} exceeds cap {MAX_OPS}"));
    }
    let n = n as usize;

    // Stream-decompress the record body. We read exactly n * OP_BYTES bytes
    // out of the decoder, so a forged frame cannot expand without bound; the
    // window cap limits the decoder's own buffer allocation.
    let mut dec = zstd::stream::read::Decoder::new(BufReader::new(file))
        .map_err(|e| format!("{path}: zstd init: {e}"))?;
    dec.window_log_max(ZSTD_WINDOW_LOG_MAX)
        .map_err(|e| format!("{path}: zstd window cap: {e}"))?;

    let mut ops = Vec::with_capacity(n);
    let mut rec = [0u8; OP_BYTES];
    for i in 0..n {
        dec.read_exact(&mut rec)
            .map_err(|e| format!("op {i}: short read from compressed body: {e}"))?;
        let kind_raw = u32::from_le_bytes(rec[0..4].try_into().unwrap());
        let kind =
            op_kind_from_u32(kind_raw).ok_or_else(|| format!("op {i}: unknown kind {kind_raw}"))?;
        // rec[4..8] are reserved padding for 8-byte alignment.
        let q_control2 = QubitId(read_u64(&rec, 8));
        let q_control1 = QubitId(read_u64(&rec, 16));
        let q_target = QubitId(read_u64(&rec, 24));
        let c_target = BitId(read_u64(&rec, 32));
        let c_condition = BitId(read_u64(&rec, 40));
        let r_target = RegisterId(read_u64(&rec, 48));

        let op = Op {
            kind,
            q_control2,
            q_control1,
            q_target,
            c_target,
            c_condition,
            r_target,
        };
        // Op::validate() panics on aliasing or per-kind field-shape errors.
        // Catch the unwind to convert into a clean rejection.
        let validated = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| op.validate()));
        if let Err(e) = validated {
            let msg = e
                .downcast_ref::<String>()
                .cloned()
                .or_else(|| e.downcast_ref::<&'static str>().map(|s| s.to_string()))
                .unwrap_or_else(|| "validation panic".to_string());
            return Err(format!("op {i}: {msg}"));
        }
        ops.push(op);
    }

    // Reject trailing data: exactly n records must decompress, no more.
    let mut extra = [0u8; 1];
    match dec.read(&mut extra) {
        Ok(0) => {}
        Ok(_) => return Err(format!("{path}: trailing data after {n} ops")),
        Err(e) => return Err(format!("{path}: error checking for trailing data: {e}")),
    }
    Ok(ops)
}

// ─── secp256k1 parameters ──────────────────────────────────────────────────

fn secp256k1() -> WeierstrassEllipticCurve {
    WeierstrassEllipticCurve {
        modulus: U256::from_str_radix(
            "FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F",
            16,
        )
        .unwrap(),
        a: U256::from(0),
        b: U256::from(7),
        gx: U256::from_str_radix(
            "79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798",
            16,
        )
        .unwrap(),
        gy: U256::from_str_radix(
            "483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8",
            16,
        )
        .unwrap(),
        order: U256::from_str_radix(
            "FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141",
            16,
        )
        .unwrap(),
    }
}

// ─── Fiat-Shamir seed ──────────────────────────────────────────────────────
//
// SHAKE256 over the op stream. Determines test inputs, simulator RNG for
// R/Hmr phase randomization, etc.

fn fiat_shamir_seed(ops: &[Op]) -> sha3::Shake256Reader {
    let mut hasher = Shake256::default();
    hasher.update(b"quantum_ecc-fiat-shamir-v2");
    hasher.update(&(ops.len() as u64).to_le_bytes());
    for op in ops {
        hasher.update(&[op.kind as u8]);
        hasher.update(&op.q_control2.0.to_le_bytes());
        hasher.update(&op.q_control1.0.to_le_bytes());
        hasher.update(&op.q_target.0.to_le_bytes());
        hasher.update(&op.c_target.0.to_le_bytes());
        hasher.update(&op.c_condition.0.to_le_bytes());
        hasher.update(&op.r_target.0.to_le_bytes());
    }
    hasher.finalize_xof()
}

fn evaluation_seed(ops: &[Op]) -> sha3::Shake256Reader {
    let Ok(seed) = std::env::var("EVAL_SHARED_SEED") else {
        return fiat_shamir_seed(ops);
    };
    let mut hasher = Shake256::default();
    hasher.update(b"quantum_ecc-shared-comparison-v1");
    hasher.update(seed.as_bytes());
    hasher.finalize_xof()
}

fn parallel_batch_seed(batch: usize) -> sha3::Shake256Reader {
    let mut hasher = Shake256::default();
    hasher.update(b"quantum_ecc-shared-comparison-batch-v1");
    if let Ok(seed) = std::env::var("EVAL_SHARED_SEED") {
        hasher.update(seed.as_bytes());
    }
    hasher.update(&(batch as u64).to_le_bytes());
    hasher.finalize_xof()
}

// ─── Test runner ──────────────────────────────────────────────────────────

struct SeedReport {
    ok: bool,
    avg_cliff: f64,
    avg_tof: f64,
    tot_tof: u64,
    tot_cliff: u64,
    n_shots: usize,
    classical_failures: usize,
    phase_failure_shots: usize,
    ancilla_failure_shots: usize,
    any_failure_shots: usize,
    identity_rows: usize,
    window_selections: usize,
    phase_garbage_batches: usize,
    ancilla_garbage_batches: usize,
    fail_reason: Option<String>,
}

struct WindowCases {
    table: quantum_ecc::windowed_table::WindowTable,
    targets: Vec<(U256, U256)>,
    addresses: Vec<usize>,
    addends: Vec<(U256, U256)>,
    expected: Vec<(U256, U256)>,
    address_sequences: Vec<Vec<usize>>,
    expected_sequences: Vec<Vec<(U256, U256)>>,
    identity_rows: usize,
}

#[derive(Clone, Copy, Debug)]
enum PairedWindowInterface {
    RuntimeTable,
    ClassicalAddend,
}

impl PairedWindowInterface {
    fn label(self) -> &'static str {
        match self {
            Self::RuntimeTable => "runtime-table-windowed",
            Self::ClassicalAddend => "baseline-classical-addend",
        }
    }

    fn quantum_interface_registers(self) -> usize {
        match self {
            Self::RuntimeTable => 3,
            Self::ClassicalAddend => 2,
        }
    }
}

#[derive(Clone, Default)]
struct ParallelReport {
    toffoli_gates: u64,
    clifford_gates: u64,
    classical_failures: usize,
    phase_failure_shots: usize,
    ancilla_failure_shots: usize,
    any_failure_shots: usize,
    phase_garbage_batches: usize,
    ancilla_garbage_batches: usize,
    fail_reason: Option<String>,
}

struct CheckpointStore {
    inputs: File,
    batches: File,
    completed_batches: HashSet<usize>,
    aggregate: ParallelReport,
    completed_shots: usize,
}

impl CheckpointStore {
    const INPUT_HEADER: &'static str = "batch\tindex\taddress\ttarget_x\ttarget_y\taddend_x\taddend_y\texpected_x\texpected_y\tgot_x\tgot_y\tgot_address\tclassical_failure\tphase_failure\tancilla_failure\tany_failure\n";
    const BATCH_HEADER: &'static str = "batch\tshots\ttoffoli\tclifford\tclassical_failures\tphase_failure_shots\tancilla_failure_shots\tany_failure_shots\tphase_garbage_batches\tancilla_garbage_batches\tinputs_end_offset\n";

    fn open(root: &Path) -> std::io::Result<Self> {
        std::fs::create_dir_all(root)?;
        let inputs_path = root.join("inputs.tsv");
        let batches_path = root.join("batches.tsv");

        let batch_text = std::fs::read_to_string(&batches_path).unwrap_or_default();
        let mut valid_batch_lines = Vec::new();
        let mut completed_batches = HashSet::new();
        let mut aggregate = ParallelReport::default();
        let mut completed_shots = 0usize;
        let mut committed_input_end = Self::INPUT_HEADER.len() as u64;

        for line in batch_text.lines() {
            if line.is_empty() || line.starts_with("batch\t") {
                continue;
            }
            let fields = line.split('\t').collect::<Vec<_>>();
            if fields.len() != 11 {
                continue;
            }
            let parsed = (
                fields[0].parse::<usize>(),
                fields[1].parse::<usize>(),
                fields[2].parse::<u64>(),
                fields[3].parse::<u64>(),
                fields[4].parse::<usize>(),
                fields[5].parse::<usize>(),
                fields[6].parse::<usize>(),
                fields[7].parse::<usize>(),
                fields[8].parse::<usize>(),
                fields[9].parse::<usize>(),
                fields[10].parse::<u64>(),
            );
            let (
                Ok(batch),
                Ok(shots),
                Ok(toffoli),
                Ok(clifford),
                Ok(classical),
                Ok(phase),
                Ok(ancilla),
                Ok(any),
                Ok(phase_batches),
                Ok(ancilla_batches),
                Ok(input_end),
            ) = parsed
            else {
                continue;
            };
            if !completed_batches.insert(batch) {
                continue;
            }
            valid_batch_lines.push(line.to_string());
            completed_shots += shots;
            aggregate.toffoli_gates += toffoli;
            aggregate.clifford_gates += clifford;
            aggregate.classical_failures += classical;
            aggregate.phase_failure_shots += phase;
            aggregate.ancilla_failure_shots += ancilla;
            aggregate.any_failure_shots += any;
            aggregate.phase_garbage_batches += phase_batches;
            aggregate.ancilla_garbage_batches += ancilla_batches;
            committed_input_end = input_end;
        }

        let mut inputs = OpenOptions::new()
            .create(true)
            .read(true)
            .append(true)
            .open(&inputs_path)?;
        if inputs.metadata()?.len() == 0 {
            inputs.write_all(Self::INPUT_HEADER.as_bytes())?;
            inputs.flush()?;
        } else {
            let minimum = Self::INPUT_HEADER.len() as u64;
            inputs.set_len(committed_input_end.max(minimum))?;
        }

        {
            let mut repaired = File::create(&batches_path)?;
            repaired.write_all(Self::BATCH_HEADER.as_bytes())?;
            for line in &valid_batch_lines {
                writeln!(repaired, "{line}")?;
            }
            repaired.flush()?;
        }
        let batches = OpenOptions::new()
            .create(true)
            .append(true)
            .open(&batches_path)?;

        Ok(Self {
            inputs,
            batches,
            completed_batches,
            aggregate,
            completed_shots,
        })
    }

    fn record_batch(
        &mut self,
        batch: usize,
        shots: usize,
        report: &ParallelReport,
        input_rows: &str,
    ) -> std::io::Result<()> {
        self.inputs.write_all(input_rows.as_bytes())?;
        self.inputs.flush()?;
        self.inputs.sync_data()?;
        let input_end = self.inputs.metadata()?.len();
        writeln!(
            self.batches,
            "{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}",
            batch,
            shots,
            report.toffoli_gates,
            report.clifford_gates,
            report.classical_failures,
            report.phase_failure_shots,
            report.ancilla_failure_shots,
            report.any_failure_shots,
            report.phase_garbage_batches,
            report.ancilla_garbage_batches,
            input_end,
        )?;
        self.batches.flush()?;
        self.batches.sync_data()?;
        self.completed_batches.insert(batch);
        self.completed_shots += shots;
        self.aggregate.toffoli_gates += report.toffoli_gates;
        self.aggregate.clifford_gates += report.clifford_gates;
        self.aggregate.classical_failures += report.classical_failures;
        self.aggregate.phase_failure_shots += report.phase_failure_shots;
        self.aggregate.ancilla_failure_shots += report.ancilla_failure_shots;
        self.aggregate.any_failure_shots += report.any_failure_shots;
        self.aggregate.phase_garbage_batches += report.phase_garbage_batches;
        self.aggregate.ancilla_garbage_batches += report.ancilla_garbage_batches;
        Ok(())
    }
}

fn ops_fingerprint(ops: &[Op]) -> String {
    let mut hasher = Shake256::default();
    hasher.update(b"quantum_ecc-checkpoint-ops-v1");
    hasher.update(&(ops.len() as u64).to_le_bytes());
    for op in ops {
        hasher.update(&[op.kind as u8]);
        hasher.update(&op.q_control2.0.to_le_bytes());
        hasher.update(&op.q_control1.0.to_le_bytes());
        hasher.update(&op.q_target.0.to_le_bytes());
        hasher.update(&op.c_target.0.to_le_bytes());
        hasher.update(&op.c_condition.0.to_le_bytes());
        hasher.update(&op.r_target.0.to_le_bytes());
    }
    let mut reader = hasher.finalize_xof();
    let mut digest = [0u8; 16];
    XofReader::read(&mut reader, &mut digest);
    let mut encoded = String::with_capacity(2 * digest.len());
    for byte in digest {
        write!(encoded, "{byte:02x}").expect("writing to a String cannot fail");
    }
    encoded
}

fn verify_checkpoint_manifest(
    root: &Path,
    interface: PairedWindowInterface,
    ops: &[Op],
    total_qubits: u64,
    target_shots: usize,
    window_bits: usize,
) -> std::io::Result<()> {
    std::fs::create_dir_all(root)?;
    let seed = std::env::var("EVAL_SHARED_SEED")
        .unwrap_or_else(|_| "<circuit-derived-fiat-shamir>".to_string());
    let body = format!(
        "format\tbounded-qip-checkpoint-v1\ninterface\t{}\nseed\t{}\nwindow_bits\t{}\ntarget_shots\t{}\nqubits\t{}\nops\t{}\nops_fingerprint\t{}\nqip_table_beta\t{:#x}\n",
        interface.label(),
        seed,
        window_bits,
        target_shots,
        total_qubits,
        ops.len(),
        ops_fingerprint(ops),
        qip_table_scalar(),
    );
    let path = root.join("manifest.tsv");
    match std::fs::read_to_string(&path) {
        Ok(existing) if existing == body => Ok(()),
        Ok(_) => Err(std::io::Error::new(
            std::io::ErrorKind::InvalidData,
            format!(
                "checkpoint manifest {} does not match this experiment",
                path.display()
            ),
        )),
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => {
            let mut file = File::create(path)?;
            file.write_all(body.as_bytes())?;
            file.flush()?;
            file.sync_data()
        }
        Err(error) => Err(error),
    }
}

// Experimental input construction only. The official evaluator is unchanged.
fn qip_table_scalar() -> U256 {
    let value = std::env::var("QIP_TABLE_BETA").unwrap_or_else(|_| "1".to_string());
    let value = value.strip_prefix("0x").unwrap_or(&value);
    let beta = U256::from_str_radix(value, 16).expect("QIP_TABLE_BETA must be hexadecimal");
    assert!(!beta.is_zero() && beta < secp256k1().order, "table base scalar out of range");
    beta
}

fn qip_table_from_scalar(window_bits: usize, beta: U256) -> quantum_ecc::windowed_table::WindowTable {
    assert!(window_bits <= 16);
    let curve = secp256k1();
    assert!(!beta.is_zero() && beta < curve.order);
    let base = curve.mul(curve.gx, curve.gy, beta);
    let rows = 1usize << window_bits;
    let mut x = Vec::with_capacity(rows);
    let mut y = Vec::with_capacity(rows);
    let mut point = (U256::ZERO, U256::ZERO);
    for _ in 0..rows {
        x.push(point.0);
        y.push(point.1);
        point = curve.add(point.0, point.1, base.0, base.1);
    }
    quantum_ecc::windowed_table::WindowTable { x, y }
}

fn generate_window_cases(
    xof: &mut sha3::Shake256Reader,
    target_shots: usize,
    window_bits: usize,
    sequence_calls: usize,
) -> WindowCases {
    assert!(sequence_calls > 0);
    let curve = secp256k1();
    let table = qip_table_from_scalar(window_bits, qip_table_scalar());
    let mut targets = Vec::with_capacity(target_shots);
    let mut addresses = Vec::with_capacity(target_shots);
    let mut addends = Vec::with_capacity(target_shots);
    let mut expected = Vec::with_capacity(target_shots);
    let mut address_sequences = Vec::with_capacity(target_shots);
    let mut expected_sequences = Vec::with_capacity(target_shots);
    let mut identity_rows = 0usize;
    while targets.len() < target_shots {
        let mut scalar_bytes = [0u8; 32];
        XofReader::read(xof, &mut scalar_bytes);
        let target = curve.mul(curve.gx, curve.gy, U256::from_le_bytes(scalar_bytes));
        if target.0.is_zero() && target.1.is_zero() {
            continue;
        }

        let mut current = target;
        let mut sequence = Vec::with_capacity(sequence_calls);
        let mut sequence_expected = Vec::with_capacity(sequence_calls);
        let mut sequence_identity_rows = 0usize;
        let mut valid = true;
        for _ in 0..sequence_calls {
            let mut address_bytes = [0u8; 8];
            XofReader::read(xof, &mut address_bytes);
            let address = (u64::from_le_bytes(address_bytes) as usize) & (table.len() - 1);
            let addend = table.point(address);
            // The arithmetic kernel, like the cited generic-affine constructions,
            // excludes R = +/-A.  Equal x-coordinates identify both cases.
            if address != 0 && current.0 == addend.0 {
                valid = false;
                break;
            }
            if address == 0 {
                sequence_identity_rows += 1;
            } else {
                current = curve.add(current.0, current.1, addend.0, addend.1);
            }
            sequence.push(address);
            sequence_expected.push(current);
        }
        if !valid {
            continue;
        }

        let address = sequence[0];
        let addend = table.point(address);
        targets.push(target);
        addresses.push(address);
        addends.push(addend);
        expected.push(sequence_expected[0]);
        address_sequences.push(sequence);
        expected_sequences.push(sequence_expected);
        identity_rows += sequence_identity_rows;
    }
    WindowCases {
        table,
        targets,
        addresses,
        addends,
        expected,
        address_sequences,
        expected_sequences,
        identity_rows,
    }
}

fn set_register_mask<R: XofReader>(
    sim: &mut Simulator<'_, R>,
    register: &[QubitOrBit],
    value: U256,
    mask: u64,
) {
    for (bit, item) in register.iter().enumerate() {
        let state = if value.bit(bit) { mask } else { 0 };
        match *item {
            QubitOrBit::Qubit(id) => *sim.qubit_mut(id) = state,
            QubitOrBit::Bit(id) => *sim.bit_mut(id) = state,
        }
    }
}

fn set_window_table_inputs<R: XofReader>(
    sim: &mut Simulator<'_, R>,
    layout_regs: &[Vec<QubitOrBit>],
    table: &quantum_ecc::windowed_table::WindowTable,
    mask: u64,
) {
    assert_eq!(layout_regs.len(), 3 + 2 * table.len());
    for row in 0..table.len() {
        set_register_mask(sim, &layout_regs[3 + 2 * row], table.x[row], mask);
        set_register_mask(sim, &layout_regs[4 + 2 * row], table.y[row], mask);
    }
}

fn run_tests(
    ops: &[Op],
    layout_regs: &[Vec<QubitOrBit>],
    total_qubits: u64,
    num_bits: u64,
    mut xof: sha3::Shake256Reader,
    target_shots: usize,
) -> SeedReport {
    let curve = secp256k1();

    let mut targets = Vec::with_capacity(target_shots);
    let mut offsets = Vec::with_capacity(target_shots);
    let mut expected = Vec::with_capacity(target_shots);
    for _ in 0..target_shots {
        let mut rb = [[0u8; 32]; 2];
        // Disambiguate from std::io::Read (in scope for the zstd loader).
        XofReader::read(&mut xof, &mut rb[0]);
        XofReader::read(&mut xof, &mut rb[1]);
        let k1 = U256::from_le_bytes(rb[0]);
        let k2 = U256::from_le_bytes(rb[1]);
        let t = curve.mul(curve.gx, curve.gy, k1);
        let o = curve.mul(curve.gx, curve.gy, k2);
        if t.0 == o.0 {
            continue;
        }
        if t.0.is_zero() && t.1.is_zero() {
            continue;
        }
        if o.0.is_zero() && o.1.is_zero() {
            continue;
        }
        let e = curve.add(t.0, t.1, o.0, o.1);
        targets.push(t);
        offsets.push(o);
        expected.push(e);
    }
    let n = targets.len();

    let mut sim = Simulator::new(total_qubits as usize, num_bits as usize, &mut xof);
    let mut ok = true;
    let mut fail_reason: Option<String> = None;
    let mut classical_failures = 0usize;
    let mut phase_garbage_batches = 0usize;
    let mut ancilla_garbage_batches = 0usize;

    const BATCH: usize = 64;
    let num_batches = (n + BATCH - 1) / BATCH;
    for batch in 0..num_batches {
        let bs = BATCH.min(n - batch * BATCH);
        let cond_mask: u64 = if bs == 64 { u64::MAX } else { (1u64 << bs) - 1 };

        sim.clear_for_shot();
        for shot in 0..bs {
            let i = batch * BATCH + shot;
            sim.set_register(&layout_regs[0], targets[i].0, shot);
            sim.set_register(&layout_regs[1], targets[i].1, shot);
            sim.set_register(&layout_regs[2], offsets[i].0, shot);
            sim.set_register(&layout_regs[3], offsets[i].1, shot);
        }

        sim.apply_iter_masked(ops.iter(), cond_mask);

        for shot in 0..bs {
            let i = batch * BATCH + shot;
            let gx = sim.get_register(&layout_regs[0], shot);
            let gy = sim.get_register(&layout_regs[1], shot);
            if gx != expected[i].0 || gy != expected[i].1 {
                classical_failures += 1;
                if fail_reason.is_none() {
                    fail_reason = Some(format!(
                        "CLASSICAL MISMATCH shot {i}: got ({:#x},{:#x}) exp ({:#x},{:#x})",
                        gx, gy, expected[i].0, expected[i].1
                    ));
                }
                ok = false;
            }
        }

        let phase = sim.phase & cond_mask;
        if phase != 0 {
            phase_garbage_batches += 1;
            let msg = format!(
                "PHASE GARBAGE: global_phase = {:#018x} across {} live shots (must be 0)",
                phase, bs
            );
            if fail_reason.is_none() {
                fail_reason = Some(msg);
            }
            ok = false;
        }

        for register in layout_regs {
            for qb in register {
                if let QubitOrBit::Qubit(q) = *qb {
                    *sim.qubit_mut(q) = 0;
                }
            }
        }
        let mut garbage_q: Option<u64> = None;
        for q in 0..total_qubits {
            let v = sim.qubit(QubitId(q)) & cond_mask;
            if v != 0 {
                garbage_q = Some(q);
                break;
            }
        }
        if let Some(q) = garbage_q {
            ancilla_garbage_batches += 1;
            let v = sim.qubit(QubitId(q)) & cond_mask;
            let msg = format!(
                "ANCILLA GARBAGE: qubit {} = {:#018x} (live shots) at end of forward; \
                 every non-register qubit must be |0⟩ on every live shot",
                q, v
            );
            if fail_reason.is_none() {
                fail_reason = Some(msg);
            }
            ok = false;
        }
    }

    let _ = num_bits;
    let denom = n.max(1) as f64;
    SeedReport {
        ok,
        avg_cliff: sim.stats.clifford_gates as f64 / denom,
        avg_tof: sim.stats.toffoli_gates as f64 / denom,
        tot_tof: sim.stats.toffoli_gates,
        tot_cliff: sim.stats.clifford_gates,
        n_shots: n,
        classical_failures,
        phase_failure_shots: 0,
        ancilla_failure_shots: 0,
        any_failure_shots: classical_failures,
        identity_rows: 0,
        window_selections: 0,
        phase_garbage_batches,
        ancilla_garbage_batches,
        fail_reason,
    }
}

fn run_windowed_tests(
    ops: &[Op],
    layout_regs: &[Vec<QubitOrBit>],
    total_qubits: u64,
    num_bits: u64,
    mut xof: sha3::Shake256Reader,
    target_shots: usize,
    window_bits: usize,
    sequence_calls: usize,
) -> SeedReport {
    let cases = generate_window_cases(&mut xof, target_shots, window_bits, sequence_calls);
    let n = cases.targets.len();
    let mut sim = Simulator::new(total_qubits as usize, num_bits as usize, &mut xof);
    let mut fail_reason = None;
    let mut classical_failures = 0usize;
    let mut phase_failure_shots = 0usize;
    let mut ancilla_failure_shots = 0usize;
    let mut any_failure_shots = 0usize;
    let mut phase_garbage_batches = 0usize;
    let mut ancilla_garbage_batches = 0usize;

    let mut interface_qubits = vec![false; total_qubits as usize];
    for register in &layout_regs[..3] {
        for item in register {
            if let QubitOrBit::Qubit(qubit) = *item {
                interface_qubits[qubit.0 as usize] = true;
            }
        }
    }

    const BATCH: usize = 64;
    let num_batches = (n + BATCH - 1) / BATCH;
    for batch in 0..num_batches {
        let bs = BATCH.min(n - batch * BATCH);
        let cond_mask = if bs == 64 { u64::MAX } else { (1u64 << bs) - 1 };
        sim.clear_for_shot();
        set_window_table_inputs(&mut sim, layout_regs, &cases.table, cond_mask);
        let mut classical_failure_mask = 0u64;
        let mut phase_failure_mask = 0u64;
        let mut ancilla_failure_mask = 0u64;
        for shot in 0..bs {
            let index = batch * BATCH + shot;
            sim.set_register(&layout_regs[0], cases.targets[index].0, shot);
            sim.set_register(&layout_regs[1], cases.targets[index].1, shot);
        }

        for call in 0..sequence_calls {
            for shot in 0..bs {
                let index = batch * BATCH + shot;
                sim.set_register(
                    &layout_regs[2],
                    U256::from(cases.address_sequences[index][call]),
                    shot,
                );
            }

            let phase_before = sim.phase;
            sim.apply_iter_masked(ops.iter(), cond_mask);
            let call_phase = (sim.phase ^ phase_before) & cond_mask;
            if call_phase != 0 {
                phase_garbage_batches += 1;
                phase_failure_mask |= call_phase;
                if fail_reason.is_none() {
                    fail_reason = Some(format!(
                        "PHASE GARBAGE after sequence call {call}: delta = {call_phase:#018x}"
                    ));
                }
            }

            for shot in 0..bs {
                let index = batch * BATCH + shot;
                let got_x = sim.get_register(&layout_regs[0], shot);
                let got_y = sim.get_register(&layout_regs[1], shot);
                let got_address = sim.get_register(&layout_regs[2], shot);
                let expected = cases.expected_sequences[index][call];
                let address = cases.address_sequences[index][call];
                if got_x != expected.0 || got_y != expected.1 || got_address != U256::from(address)
                {
                    classical_failure_mask |= 1u64 << shot;
                    if fail_reason.is_none() {
                        fail_reason = Some(format!(
                            "CLASSICAL MISMATCH shot {index}, call {call}, address {address}: got ({got_x:#x},{got_y:#x}) exp ({:#x},{:#x})",
                            expected.0, expected.1,
                        ));
                    }
                }
            }

            let mut call_garbage = 0u64;
            for q in 0..total_qubits as usize {
                if !interface_qubits[q] {
                    call_garbage |= sim.qubit(QubitId(q as u64)) & cond_mask;
                }
            }
            if call_garbage != 0 {
                ancilla_garbage_batches += 1;
                ancilla_failure_mask |= call_garbage;
                if fail_reason.is_none() {
                    fail_reason = Some(format!(
                        "ANCILLA GARBAGE after sequence call {call}: mask = {call_garbage:#018x}"
                    ));
                }
            }
        }

        classical_failures += classical_failure_mask.count_ones() as usize;
        phase_failure_shots += phase_failure_mask.count_ones() as usize;
        ancilla_failure_shots += ancilla_failure_mask.count_ones() as usize;
        any_failure_shots += (classical_failure_mask | phase_failure_mask | ancilla_failure_mask)
            .count_ones() as usize;
    }

    let operation_denom = (n * sequence_calls).max(1) as f64;
    SeedReport {
        ok: classical_failures == 0 && phase_failure_shots == 0 && ancilla_failure_shots == 0,
        avg_cliff: sim.stats.clifford_gates as f64 / operation_denom,
        avg_tof: sim.stats.toffoli_gates as f64 / operation_denom,
        tot_tof: sim.stats.toffoli_gates,
        tot_cliff: sim.stats.clifford_gates,
        n_shots: n,
        classical_failures,
        phase_failure_shots,
        ancilla_failure_shots,
        any_failure_shots,
        identity_rows: cases.identity_rows,
        window_selections: n * sequence_calls,
        phase_garbage_batches,
        ancilla_garbage_batches,
        fail_reason,
    }
}

fn run_paired_window_tests_parallel(
    ops: &[Op],
    layout_regs: &[Vec<QubitOrBit>],
    total_qubits: u64,
    num_bits: u64,
    mut xof: sha3::Shake256Reader,
    target_shots: usize,
    window_bits: usize,
    interface: PairedWindowInterface,
    requested_threads: usize,
) -> SeedReport {
    let cases = generate_window_cases(&mut xof, target_shots, window_bits, 1);
    let n = cases.targets.len();
    const BATCH: usize = 64;
    let num_batches = (n + BATCH - 1) / BATCH;
    let threads = requested_threads.max(1).min(num_batches.max(1));
    let only_batch = std::env::var("EVAL_ONLY_BATCH")
        .ok()
        .and_then(|value| value.parse::<usize>().ok());

    let checkpoint = std::env::var("EVAL_CHECKPOINT_DIR")
        .ok()
        .map(PathBuf::from)
        .map(|path| {
            println!("  checkpoint directory     : {}", path.display());
            verify_checkpoint_manifest(
                &path,
                interface,
                ops,
                total_qubits,
                target_shots,
                window_bits,
            )
            .expect("checkpoint manifest does not match this evaluation");
            CheckpointStore::open(&path).expect("failed to open evaluation checkpoint")
        });
    let (previously_completed, prior_report, prior_shots) = checkpoint
        .as_ref()
        .map(|store| {
            (
                store.completed_batches.clone(),
                store.aggregate.clone(),
                store.completed_shots,
            )
        })
        .unwrap_or_default();
    let checkpoint = checkpoint.map(Mutex::new);
    let completed_shots = AtomicUsize::new(prior_shots);
    let observed_failures = AtomicUsize::new(prior_report.any_failure_shots);
    let first_threshold = (((prior_shots / 10_000) + 1) * 10_000).min(n.max(1));
    let next_progress = AtomicUsize::new(first_threshold);

    println!("  evaluator threads        : {threads}");
    println!("  paired interface         : {}", interface.label());
    if prior_shots > 0 {
        println!(
            "  resumed progress         : {prior_shots}/{n} shots; {} failures observed",
            prior_report.any_failure_shots,
        );
    }

    let worker_reports = std::thread::scope(|scope| {
        let mut handles = Vec::with_capacity(threads);
        for worker in 0..threads {
            let completed_shots = &completed_shots;
            let observed_failures = &observed_failures;
            let next_progress = &next_progress;
            let cases = &cases;
            let previously_completed = &previously_completed;
            let checkpoint = &checkpoint;
            handles.push(scope.spawn(move || {
                let mut report = ParallelReport::default();

                for batch in (worker..num_batches).step_by(threads) {
                    if only_batch.is_some_and(|selected| batch != selected) {
                        continue;
                    }
                    if previously_completed.contains(&batch) {
                        continue;
                    }
                    let bs = BATCH.min(n - batch * BATCH);
                    let cond_mask = if bs == 64 {
                        u64::MAX
                    } else {
                        (1u64 << bs) - 1
                    };
                    let mut batch_xof = parallel_batch_seed(batch);
                    let mut sim = Simulator::new(
                        total_qubits as usize,
                        num_bits as usize,
                        &mut batch_xof,
                    );
                    if matches!(interface, PairedWindowInterface::RuntimeTable) {
                        set_window_table_inputs(&mut sim, layout_regs, &cases.table, cond_mask);
                    }
                    let mut classical_failure_mask = 0u64;
                    let mut got_values = Vec::with_capacity(bs);
                    for shot in 0..bs {
                        let index = batch * BATCH + shot;
                        sim.set_register(&layout_regs[0], cases.targets[index].0, shot);
                        sim.set_register(&layout_regs[1], cases.targets[index].1, shot);
                        match interface {
                            PairedWindowInterface::RuntimeTable => sim.set_register(
                                &layout_regs[2],
                                U256::from(cases.addresses[index]),
                                shot,
                            ),
                            PairedWindowInterface::ClassicalAddend => {
                                sim.set_register(&layout_regs[2], cases.addends[index].0, shot);
                                sim.set_register(&layout_regs[3], cases.addends[index].1, shot);
                            }
                        }
                    }
                    sim.apply_iter_masked(ops.iter(), cond_mask);

                    for shot in 0..bs {
                        let index = batch * BATCH + shot;
                        let got_x = sim.get_register(&layout_regs[0], shot);
                        let got_y = sim.get_register(&layout_regs[1], shot);
                        let got_address = match interface {
                            PairedWindowInterface::RuntimeTable => {
                                sim.get_register(&layout_regs[2], shot)
                            }
                            PairedWindowInterface::ClassicalAddend => {
                                U256::from(cases.addresses[index])
                            }
                        };
                        got_values.push((got_x, got_y, got_address));
                        if got_x != cases.expected[index].0
                            || got_y != cases.expected[index].1
                            || (matches!(interface, PairedWindowInterface::RuntimeTable)
                                && got_address != U256::from(cases.addresses[index]))
                        {
                            classical_failure_mask |= 1u64 << shot;
                            if report.fail_reason.is_none() {
                                report.fail_reason = Some(format!(
                                    "CLASSICAL MISMATCH shot {index} address {}: got ({got_x:#x},{got_y:#x}) exp ({:#x},{:#x})",
                                    cases.addresses[index],
                                    cases.expected[index].0,
                                    cases.expected[index].1,
                                ));
                            }
                        }
                    }

                    let phase = sim.phase & cond_mask;
                    if phase != 0 && report.fail_reason.is_none() {
                        report.fail_reason =
                            Some(format!("PHASE GARBAGE: global_phase = {phase:#018x}"));
                    }

                    for register in &layout_regs[..interface.quantum_interface_registers()] {
                        for item in register {
                            if let QubitOrBit::Qubit(qubit) = *item {
                                *sim.qubit_mut(qubit) = 0;
                            }
                        }
                    }
                    let mut garbage_mask = 0u64;
                    for q in 0..total_qubits {
                        garbage_mask |= sim.qubit(QubitId(q)) & cond_mask;
                    }
                    if garbage_mask != 0 && report.fail_reason.is_none() {
                        report.fail_reason =
                            Some(format!("ANCILLA GARBAGE mask = {garbage_mask:#018x}"));
                    }

                    let any_failure_mask = classical_failure_mask | phase | garbage_mask;
                    let mut batch_report = ParallelReport {
                        toffoli_gates: sim.stats.toffoli_gates,
                        clifford_gates: sim.stats.clifford_gates,
                        classical_failures: classical_failure_mask.count_ones() as usize,
                        phase_failure_shots: phase.count_ones() as usize,
                        ancilla_failure_shots: garbage_mask.count_ones() as usize,
                        any_failure_shots: any_failure_mask.count_ones() as usize,
                        phase_garbage_batches: usize::from(phase != 0),
                        ancilla_garbage_batches: usize::from(garbage_mask != 0),
                        fail_reason: report.fail_reason.clone(),
                    };
                    let mut input_rows = String::with_capacity(bs * 700);
                    for shot in 0..bs {
                        let index = batch * BATCH + shot;
                        let bit = 1u64 << shot;
                        let (got_x, got_y, got_address) = got_values[shot];
                        writeln!(
                            input_rows,
                            "{}\t{}\t{}\t{:#x}\t{:#x}\t{:#x}\t{:#x}\t{:#x}\t{:#x}\t{:#x}\t{:#x}\t{:#x}\t{}\t{}\t{}\t{}",
                            batch,
                            index,
                            cases.addresses[index],
                            cases.targets[index].0,
                            cases.targets[index].1,
                            cases.addends[index].0,
                            cases.addends[index].1,
                            cases.expected[index].0,
                            cases.expected[index].1,
                            got_x,
                            got_y,
                            got_address,
                            usize::from(classical_failure_mask & bit != 0),
                            usize::from(phase & bit != 0),
                            usize::from(garbage_mask & bit != 0),
                            usize::from(any_failure_mask & bit != 0),
                        )
                        .expect("failed to format per-input checkpoint row");
                    }
                    if let Some(checkpoint) = checkpoint {
                        checkpoint
                            .lock()
                            .expect("evaluation checkpoint lock poisoned")
                            .record_batch(batch, bs, &batch_report, &input_rows)
                            .expect("failed to persist evaluation checkpoint");
                    }

                    report.toffoli_gates += batch_report.toffoli_gates;
                    report.clifford_gates += batch_report.clifford_gates;
                    report.classical_failures += batch_report.classical_failures;
                    report.phase_failure_shots += batch_report.phase_failure_shots;
                    report.ancilla_failure_shots += batch_report.ancilla_failure_shots;
                    report.any_failure_shots += batch_report.any_failure_shots;
                    report.phase_garbage_batches += batch_report.phase_garbage_batches;
                    report.ancilla_garbage_batches += batch_report.ancilla_garbage_batches;
                    if report.fail_reason.is_none() {
                        report.fail_reason = batch_report.fail_reason.take();
                    }

                    let batch_failures = batch_report.any_failure_shots;
                    observed_failures.fetch_add(batch_failures, Ordering::Relaxed);
                    let done = completed_shots.fetch_add(bs, Ordering::Relaxed) + bs;

                    loop {
                        let threshold = next_progress.load(Ordering::Relaxed);
                        if done < threshold || threshold > n {
                            break;
                        }
                        let next = (threshold + 10_000).min(n + 1);
                        if next_progress
                            .compare_exchange(
                                threshold,
                                next,
                                Ordering::Relaxed,
                                Ordering::Relaxed,
                            )
                            .is_ok()
                        {
                            let failures = observed_failures.load(Ordering::Relaxed);
                            println!(
                                "  progress                : {done}/{n} shots; {failures} failures observed"
                            );
                            let _ = std::io::stdout().flush();
                            break;
                        }
                    }
                }

                report
            }));
        }

        handles
            .into_iter()
            .map(|handle| handle.join().expect("parallel evaluator worker panicked"))
            .collect::<Vec<_>>()
    });

    let mut merged = prior_report;
    for worker in worker_reports {
        merged.toffoli_gates += worker.toffoli_gates;
        merged.clifford_gates += worker.clifford_gates;
        merged.classical_failures += worker.classical_failures;
        merged.phase_failure_shots += worker.phase_failure_shots;
        merged.ancilla_failure_shots += worker.ancilla_failure_shots;
        merged.any_failure_shots += worker.any_failure_shots;
        merged.phase_garbage_batches += worker.phase_garbage_batches;
        merged.ancilla_garbage_batches += worker.ancilla_garbage_batches;
        if merged.fail_reason.is_none() {
            merged.fail_reason = worker.fail_reason;
        }
    }
    if merged.fail_reason.is_none() && merged.any_failure_shots > 0 {
        merged.fail_reason = Some("failure details are recorded in the resumed checkpoint".into());
    }

    let denom = n.max(1) as f64;
    SeedReport {
        ok: merged.classical_failures == 0
            && merged.phase_failure_shots == 0
            && merged.ancilla_failure_shots == 0,
        avg_cliff: merged.clifford_gates as f64 / denom,
        avg_tof: merged.toffoli_gates as f64 / denom,
        tot_tof: merged.toffoli_gates,
        tot_cliff: merged.clifford_gates,
        n_shots: n,
        classical_failures: merged.classical_failures,
        phase_failure_shots: merged.phase_failure_shots,
        ancilla_failure_shots: merged.ancilla_failure_shots,
        any_failure_shots: merged.any_failure_shots,
        identity_rows: cases.identity_rows,
        window_selections: n,
        phase_garbage_batches: merged.phase_garbage_batches,
        ancilla_garbage_batches: merged.ancilla_garbage_batches,
        fail_reason: merged.fail_reason,
    }
}

fn run_mixed_window_tests(
    ops: &[Op],
    layout_regs: &[Vec<QubitOrBit>],
    total_qubits: u64,
    num_bits: u64,
    mut xof: sha3::Shake256Reader,
    target_shots: usize,
    window_bits: usize,
) -> SeedReport {
    let cases = generate_window_cases(&mut xof, target_shots, window_bits, 1);
    let n = cases.targets.len();
    let mut sim = Simulator::new(total_qubits as usize, num_bits as usize, &mut xof);
    let mut fail_reason = None;
    let mut classical_failures = 0usize;
    let mut phase_failure_shots = 0usize;
    let mut ancilla_failure_shots = 0usize;
    let mut any_failure_shots = 0usize;
    let mut phase_garbage_batches = 0usize;
    let mut ancilla_garbage_batches = 0usize;

    const BATCH: usize = 64;
    let num_batches = (n + BATCH - 1) / BATCH;
    for batch in 0..num_batches {
        let bs = BATCH.min(n - batch * BATCH);
        let cond_mask = if bs == 64 { u64::MAX } else { (1u64 << bs) - 1 };
        sim.clear_for_shot();
        let mut classical_failure_mask = 0u64;
        for shot in 0..bs {
            let index = batch * BATCH + shot;
            sim.set_register(&layout_regs[0], cases.targets[index].0, shot);
            sim.set_register(&layout_regs[1], cases.targets[index].1, shot);
            sim.set_register(&layout_regs[2], cases.addends[index].0, shot);
            sim.set_register(&layout_regs[3], cases.addends[index].1, shot);
        }
        sim.apply_iter_masked(ops.iter(), cond_mask);

        for shot in 0..bs {
            let index = batch * BATCH + shot;
            let got_x = sim.get_register(&layout_regs[0], shot);
            let got_y = sim.get_register(&layout_regs[1], shot);
            if got_x != cases.expected[index].0 || got_y != cases.expected[index].1 {
                classical_failures += 1;
                classical_failure_mask |= 1u64 << shot;
                if fail_reason.is_none() {
                    fail_reason = Some(format!(
                        "CLASSICAL MISMATCH shot {index} address {}: got ({got_x:#x},{got_y:#x}) exp ({:#x},{:#x})",
                        cases.addresses[index], cases.expected[index].0, cases.expected[index].1,
                    ));
                }
            }
        }

        let phase = sim.phase & cond_mask;
        if phase != 0 {
            phase_garbage_batches += 1;
            phase_failure_shots += phase.count_ones() as usize;
            if fail_reason.is_none() {
                fail_reason = Some(format!("PHASE GARBAGE: global_phase = {phase:#018x}"));
            }
        }

        for register in layout_regs {
            for item in register {
                if let QubitOrBit::Qubit(qubit) = *item {
                    *sim.qubit_mut(qubit) = 0;
                }
            }
        }
        let mut garbage_mask = 0u64;
        for q in 0..total_qubits {
            garbage_mask |= sim.qubit(QubitId(q)) & cond_mask;
        }
        if garbage_mask != 0 {
            ancilla_garbage_batches += 1;
            ancilla_failure_shots += garbage_mask.count_ones() as usize;
            if fail_reason.is_none() {
                fail_reason = Some(format!("ANCILLA GARBAGE mask = {garbage_mask:#018x}"));
            }
        }
        any_failure_shots += (classical_failure_mask | phase | garbage_mask).count_ones() as usize;
    }

    let denom = n.max(1) as f64;
    SeedReport {
        ok: classical_failures == 0 && phase_failure_shots == 0 && ancilla_failure_shots == 0,
        avg_cliff: sim.stats.clifford_gates as f64 / denom,
        avg_tof: sim.stats.toffoli_gates as f64 / denom,
        tot_tof: sim.stats.toffoli_gates,
        tot_cliff: sim.stats.clifford_gates,
        n_shots: n,
        classical_failures,
        phase_failure_shots,
        ancilla_failure_shots,
        any_failure_shots,
        identity_rows: cases.identity_rows,
        window_selections: n,
        phase_garbage_batches,
        ancilla_garbage_batches,
        fail_reason,
    }
}

// ─── Output bookkeeping ────────────────────────────────────────────────────

fn parse_note() -> String {
    let mut args = std::env::args().skip(1);
    let mut note = String::new();
    while let Some(a) = args.next() {
        if a == "--note" {
            if let Some(v) = args.next() {
                note = v;
            }
        } else if let Some(rest) = a.strip_prefix("--note=") {
            note = rest.to_string();
        }
    }
    note.replace('\t', " ").replace('\n', " ")
}

fn git_commit_short() -> String {
    Command::new("git")
        .args(["rev-parse", "--short", "HEAD"])
        .output()
        .ok()
        .and_then(|o| {
            if o.status.success() {
                Some(String::from_utf8_lossy(&o.stdout).trim().to_string())
            } else {
                None
            }
        })
        .unwrap_or_else(|| "nogit".to_string())
}

fn append_results_row(
    correct: &str,
    avg_tof: f64,
    avg_cliff: f64,
    qubits: u64,
    ops_len: usize,
    note: &str,
) {
    let ts = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_secs())
        .unwrap_or(0);
    let commit = git_commit_short();
    let safe_note = note.replace('\t', " ").replace('\n', " ");
    let row = format!(
        "{ts}\t{commit}\t{avg_tof:.3}\t{avg_cliff:.3}\t{qubits}\t{ops_len}\t{correct}\t{safe_note}\n"
    );
    let path = std::env::current_dir().unwrap().join("research-results.tsv");
    match OpenOptions::new().create(true).append(true).open(path) {
        Ok(mut f) => {
            if let Err(e) = f.write_all(row.as_bytes()) {
                eprintln!("warning: failed to write results.tsv: {e}");
            }
        }
        Err(e) => eprintln!("warning: failed to open results.tsv: {e}"),
    }
}

fn write_score(avg_tof: f64, qubits: u64) {
    let path = std::env::current_dir().unwrap().join("research-score.json");
    let toffoli = avg_tof.round() as u64;
    let score = toffoli.saturating_mul(qubits);
    let body = format!(
        "{{\n  \"score\": {score},\n  \"metrics\": {{\n    \"toffoli\": {toffoli},\n    \"qubits\": {qubits}\n  }}\n}}\n"
    );
    if let Err(e) = std::fs::write(path, body) {
        eprintln!("warning: failed to write score.json: {e}");
    }
}

fn fail_and_exit(reason: &str, note: &str, ops_len: usize, total_qubits: u64) -> ! {
    eprintln!("\n!! eval FAILED: {reason}");
    let fail_note = if note.is_empty() {
        reason.to_string()
    } else {
        format!("{note} | {reason}")
    };
    append_results_row("FAIL", 0.0, 0.0, total_qubits, ops_len, &fail_note);
    std::process::exit(1);
}

#[cfg(test)]
mod bounded_qip_table_tests {
    use super::*;

    #[test]
    fn beta_one_preserves_the_original_table() {
        let old = quantum_ecc::windowed_table::WindowTable::new(6);
        let new = qip_table_from_scalar(6, U256::from(1));
        assert_eq!(old.x, new.x);
        assert_eq!(old.y, new.y);
    }

    #[test]
    fn table_rows_match_scalar_multiples() {
        let curve = secp256k1();
        for beta in [U256::from(17), U256::from(1) << 240, curve.order - U256::from(1)] {
            let table = qip_table_from_scalar(5, beta);
            for row in [0, 1, 2, 7, 15, 31] {
                let scalar = beta.mul_mod(U256::from(row), curve.order);
                assert_eq!(table.point(row), curve.mul(curve.gx, curve.gy, scalar));
                assert!(curve.is_on_curve(table.x[row], table.y[row]));
            }
        }
    }

    #[test]
    #[should_panic]
    fn zero_table_base_is_rejected() {
        qip_table_from_scalar(4, U256::ZERO);
    }
}

fn main() {
    let note = parse_note();
    println!("=== quantum_ecc: eval_bounded (research input driver) ===\n");

    let ops = match load_ops(OPS_PATH) {
        Ok(v) => v,
        Err(e) => {
            eprintln!("!! could not load {OPS_PATH}: {e}");
            append_results_row("FAIL", 0.0, 0.0, 0, 0, &format!("{note} | load: {e}"));
            std::process::exit(1);
        }
    };
    println!("  loaded ops  : {}", ops.len());

    let (total_qubits, num_bits, _num_regs, regs) = analyze_ops(ops.iter());

    if std::env::var_os("WINDOWED_MODE").is_some() {
        let window_bits = quantum_ecc::windowed_table::window_bits_from_env();
        let rows = 1usize << window_bits;
        let expected_registers = 3 + 2 * rows;
        if regs.len() != expected_registers {
            fail_and_exit(
                &format!(
                    "windowed mode expected {expected_registers} registers (X, Y, J, and {rows} classical point-table rows), got {}",
                    regs.len()
                ),
                &note,
                ops.len(),
                total_qubits,
            );
        }
        for (index, expected_width) in [256usize, 256usize, window_bits].into_iter().enumerate() {
            if regs[index].len() != expected_width {
                fail_and_exit(
                    &format!(
                        "windowed register {index} should be {expected_width} wide, got {}",
                        regs[index].len()
                    ),
                    &note,
                    ops.len(),
                    total_qubits,
                );
            }
            if regs[index]
                .iter()
                .any(|item| !matches!(item, QubitOrBit::Qubit(_)))
            {
                fail_and_exit(
                    &format!("windowed register {index} must contain only qubits"),
                    &note,
                    ops.len(),
                    total_qubits,
                );
            }
        }
        for index in 3..expected_registers {
            if regs[index].len() != 256 {
                fail_and_exit(
                    &format!(
                        "windowed table register {index} should be 256 bits wide, got {}",
                        regs[index].len()
                    ),
                    &note,
                    ops.len(),
                    total_qubits,
                );
            }
            if regs[index]
                .iter()
                .any(|item| !matches!(item, QubitOrBit::Bit(_)))
            {
                fail_and_exit(
                    &format!("windowed table register {index} must contain only classical bits"),
                    &note,
                    ops.len(),
                    total_qubits,
                );
            }
        }

        let tests = std::env::var("WINDOWED_TESTS")
            .ok()
            .and_then(|value| value.parse::<usize>().ok())
            .unwrap_or(NUM_TESTS);
        let max_error_rate = std::env::var("WINDOWED_MAX_ERROR_RATE")
            .ok()
            .and_then(|value| value.parse::<f64>().ok())
            .unwrap_or(0.0025);
        let evaluator_threads = std::env::var("EVAL_THREADS")
            .ok()
            .and_then(|value| value.parse::<usize>().ok())
            .unwrap_or(1);
        let sequence_calls = std::env::var("WINDOWED_SEQUENCE_CALLS")
            .ok()
            .and_then(|value| value.parse::<usize>().ok())
            .unwrap_or(1)
            .max(1);
        println!("  qubits      : {total_qubits}");
        println!("  bits        : {num_bits}");
        println!(
            "\n-- coherent {window_bits}-bit window tests ({tests} shots x {sequence_calls} correlated calls; allowed error {:.4}%) --",
            100.0 * max_error_rate,
        );
        let xof = evaluation_seed(&ops);
        let report = if evaluator_threads > 1 && sequence_calls == 1 {
            run_paired_window_tests_parallel(
                &ops,
                &regs,
                total_qubits,
                num_bits,
                xof,
                tests,
                window_bits,
                PairedWindowInterface::RuntimeTable,
                evaluator_threads,
            )
        } else {
            run_windowed_tests(
                &ops,
                &regs,
                total_qubits,
                num_bits,
                xof,
                tests,
                window_bits,
                sequence_calls,
            )
        };
        let denom = report.n_shots.max(1) as f64;
        let classical_rate = report.classical_failures as f64 / denom;
        let phase_rate = report.phase_failure_shots as f64 / denom;
        let ancilla_rate = report.ancilla_failure_shots as f64 / denom;
        let overlap_counting_rate = (report.classical_failures
            + report.phase_failure_shots
            + report.ancilla_failure_shots) as f64
            / denom;
        let any_failure_rate = report.any_failure_shots as f64 / denom;
        println!("  tested shots            : {}", report.n_shots);
        println!("  calls per shot          : {sequence_calls}");
        println!(
            "  identity-table rows     : {} ({:.4}%)",
            report.identity_rows,
            100.0 * report.identity_rows as f64 / report.window_selections.max(1) as f64,
        );
        println!(
            "  classical mismatches    : {} ({:.4}%)",
            report.classical_failures,
            100.0 * classical_rate,
        );
        println!(
            "  phase-failure shots     : {} ({:.4}%; {} batches)",
            report.phase_failure_shots,
            100.0 * phase_rate,
            report.phase_garbage_batches,
        );
        println!(
            "  ancilla-failure shots   : {} ({:.4}%; {} batches)",
            report.ancilla_failure_shots,
            100.0 * ancilla_rate,
            report.ancilla_garbage_batches,
        );
        println!(
            "  shots failing any channel: {} ({:.4}%)",
            report.any_failure_shots,
            100.0 * any_failure_rate,
        );
        println!(
            "  overlap-counting channel sum: {:.4}%",
            100.0 * overlap_counting_rate,
        );
        println!("\n=== coherent-window circuit metrics ===");
        println!("  avg executed Toffoli  : {:.3}", report.avg_tof);
        println!("  avg executed Clifford : {:.3}", report.avg_cliff);
        println!("  emitted ops           : {}", ops.len());
        println!("  qubits                : {total_qubits}");

        if any_failure_rate > max_error_rate {
            let reason = report.fail_reason.unwrap_or_else(|| {
                format!(
                    "observed error {:.6} exceeds allowed {:.6}",
                    any_failure_rate, max_error_rate
                )
            });
            fail_and_exit(&reason, &note, ops.len(), total_qubits);
        }
        append_results_row(
            if report.ok { "OK" } else { "OK_APPROX" },
            report.avg_tof,
            report.avg_cliff,
            total_qubits,
            ops.len(),
            &note,
        );
        write_score(report.avg_tof, total_qubits);
        println!("\n=== coherent-window experiment OK ===");
        return;
    }

    if regs.len() != 4 {
        fail_and_exit(
            &format!("expected 4 registers, got {}", regs.len()),
            &note,
            ops.len(),
            total_qubits,
        );
    }
    for (i, r) in regs.iter().enumerate() {
        if r.len() != 256 {
            fail_and_exit(
                &format!("register {i} should be 256 wide, got {}", r.len()),
                &note,
                ops.len(),
                total_qubits,
            );
        }
    }
    for q in &regs[0] {
        if !matches!(q, QubitOrBit::Qubit(_)) {
            fail_and_exit("register 0 must be qubits", &note, ops.len(), total_qubits);
        }
    }
    for q in &regs[1] {
        if !matches!(q, QubitOrBit::Qubit(_)) {
            fail_and_exit("register 1 must be qubits", &note, ops.len(), total_qubits);
        }
    }
    for q in &regs[2] {
        if !matches!(q, QubitOrBit::Bit(_)) {
            fail_and_exit("register 2 must be bits", &note, ops.len(), total_qubits);
        }
    }
    for q in &regs[3] {
        if !matches!(q, QubitOrBit::Bit(_)) {
            fail_and_exit("register 3 must be bits", &note, ops.len(), total_qubits);
        }
    }

    if let Some(window_bits) = std::env::var("MIXED_WINDOW_BITS")
        .ok()
        .and_then(|value| value.parse::<usize>().ok())
    {
        assert!((1..=16).contains(&window_bits));
        let tests = std::env::var("EVAL_TESTS")
            .ok()
            .and_then(|value| value.parse::<usize>().ok())
            .unwrap_or(NUM_TESTS);
        let max_error_rate = std::env::var("EVAL_MAX_ERROR_RATE")
            .ok()
            .and_then(|value| value.parse::<f64>().ok())
            .unwrap_or(1.0);
        let evaluator_threads = std::env::var("EVAL_THREADS")
            .ok()
            .and_then(|value| value.parse::<usize>().ok())
            .unwrap_or(1);
        println!("  qubits      : {total_qubits}");
        println!("  bits        : {num_bits}");
        println!("\n-- mixed-add comparison on {window_bits}-bit table cases ({tests} shots) --");
        let report = if evaluator_threads > 1 || std::env::var_os("EVAL_CHECKPOINT_DIR").is_some() {
            run_paired_window_tests_parallel(
                &ops,
                &regs,
                total_qubits,
                num_bits,
                evaluation_seed(&ops),
                tests,
                window_bits,
                PairedWindowInterface::ClassicalAddend,
                evaluator_threads,
            )
        } else {
            run_mixed_window_tests(
                &ops,
                &regs,
                total_qubits,
                num_bits,
                evaluation_seed(&ops),
                tests,
                window_bits,
            )
        };
        let denom = report.n_shots.max(1) as f64;
        let classical_rate = report.classical_failures as f64 / denom;
        let phase_rate = report.phase_failure_shots as f64 / denom;
        let ancilla_rate = report.ancilla_failure_shots as f64 / denom;
        let any_failure_rate = report.any_failure_shots as f64 / denom;
        println!("  tested shots            : {}", report.n_shots);
        println!(
            "  identity-table rows     : {} ({:.4}%)",
            report.identity_rows,
            100.0 * report.identity_rows as f64 / denom,
        );
        println!(
            "  classical mismatches    : {} ({:.4}%)",
            report.classical_failures,
            100.0 * classical_rate,
        );
        println!(
            "  phase-failure shots     : {} ({:.4}%; {} batches)",
            report.phase_failure_shots,
            100.0 * phase_rate,
            report.phase_garbage_batches,
        );
        println!(
            "  ancilla-failure shots   : {} ({:.4}%; {} batches)",
            report.ancilla_failure_shots,
            100.0 * ancilla_rate,
            report.ancilla_garbage_batches,
        );
        println!(
            "  shots failing any channel: {} ({:.4}%)",
            report.any_failure_shots,
            100.0 * any_failure_rate,
        );
        println!("\n=== mixed-add comparison metrics ===");
        println!("  avg executed Toffoli  : {:.3}", report.avg_tof);
        println!("  avg executed Clifford : {:.3}", report.avg_cliff);
        println!("  emitted ops           : {}", ops.len());
        println!("  qubits                : {total_qubits}");
        if any_failure_rate > max_error_rate {
            fail_and_exit(
                &format!(
                    "observed error {:.6} exceeds allowed {:.6}",
                    any_failure_rate, max_error_rate
                ),
                &note,
                ops.len(),
                total_qubits,
            );
        }
        append_results_row(
            if report.ok { "OK" } else { "OK_APPROX" },
            report.avg_tof,
            report.avg_cliff,
            total_qubits,
            ops.len(),
            &note,
        );
        write_score(report.avg_tof, total_qubits);
        println!("\n=== mixed-add comparison OK ===");
        return;
    }

    println!("  qubits      : {}", total_qubits);
    println!("  bits        : {}", num_bits);

    println!("\n-- correctness tests ({} shots) --", NUM_TESTS);
    let xof = fiat_shamir_seed(&ops);
    let r = run_tests(&ops, &regs, total_qubits, num_bits, xof, NUM_TESTS);
    println!("  tested shots            : {}", r.n_shots);
    println!("  classical mismatches    : {}", r.classical_failures);
    println!("  phase-garbage batches   : {}", r.phase_garbage_batches);
    println!("  ancilla-garbage batches : {}", r.ancilla_garbage_batches);
    if !r.ok {
        let reason = r
            .fail_reason
            .clone()
            .unwrap_or_else(|| "(no detail)".into());
        println!("\n!! correctness FAILED: {reason}");
        let fail_note = format!("{note} | {reason}");
        append_results_row(
            "FAIL",
            r.avg_tof,
            r.avg_cliff,
            total_qubits,
            ops.len(),
            &fail_note,
        );
        std::process::exit(1);
    }
    println!("  all {} shots OK", r.n_shots);

    println!("\n=== circuit metrics (secp256k1, n=256) ===");
    println!("  avg executed Toffoli  : {:.3}", r.avg_tof);
    println!("  avg executed Clifford : {:.3}", r.avg_cliff);
    println!(
        "  total Toffoli (sum)   : {} over {} shots",
        r.tot_tof, r.n_shots
    );
    println!("  total Clifford (sum)  : {}", r.tot_cliff);
    println!("  emitted ops           : {}", ops.len());
    println!("  qubits                : {}", total_qubits);

    append_results_row("OK", r.avg_tof, r.avg_cliff, total_qubits, ops.len(), &note);
    write_score(r.avg_tof, total_qubits);

    println!("\n=== experiment OK ===");
}
