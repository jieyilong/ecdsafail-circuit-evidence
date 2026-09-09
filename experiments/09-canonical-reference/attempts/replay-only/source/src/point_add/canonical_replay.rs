//! Canonical-residue reference replay. All payload inputs and outputs are in [0,p).
use super::*;

pub(super) fn enabled() -> bool { std::env::var_os("QIP_CANONICAL_REPLAY").is_some() }

fn zero_into(b: &mut B, value: &[QubitId], output: QubitId) {
    for &q in value { b.x(q); }
    let mut products = vec![and_clean(b, value[0], value[1])];
    for &q in &value[2..] { products.push(and_clean(b, *products.last().unwrap(), q)); }
    b.cx(*products.last().unwrap(), output);
    for i in (1..products.len()).rev() { and_uncompute(b, products[i], products[i-1], value[i+1]); }
    and_uncompute(b, products[0], value[0], value[1]);
    for &q in value { b.x(q); }
}

pub(super) fn negate(b: &mut B, control: QubitId, value: &[QubitId]) {
    let zero=b.alloc_qubit(); zero_into(b,value,zero); b.x(zero);
    let active=and_clean(b,control,zero);
    for &q in value { b.cx(active,q); }
    csub_nbit_const_direct_fast(b,value,U256::MAX-SECP256K1_P,active);
    and_uncompute(b,active,control,zero); b.x(zero);
    zero_into(b,value,zero); b.free(zero);
}

fn add(b: &mut B, source: &[QubitId], target: &[QubitId]) {
    let (t,th)=ext_reg(b,target);
    let (s,sh)=ext_reg(b,source);
    add_nbit_qq_fast(b,&s,&t);
    let f=U256::MAX-SECP256K1_P+U256::from(1);
    add_nbit_const_direct_uncontrolled_fast(b,&t,f);
    let reduced=b.alloc_qubit(); b.cx(th,reduced); b.x(reduced);
    csub_nbit_const_direct_fast(b,&t,f,reduced); b.x(reduced);
    b.cx(reduced,th);
    // Canonical modular addition reduced exactly when its result is below source.
    cmp_lt_into_fast(b,target,source,reduced);
    b.free(reduced); unext_reg(b,sh); unext_reg(b,th);
}

pub(super) fn signed_add(b: &mut B, sign: QubitId, source: &[QubitId], target: &[QubitId]) {
    negate(b,sign,target); add(b,source,target); negate(b,sign,target);
}

pub(super) fn halve(b: &mut B, target: &[QubitId]) {
    let (wide,high)=ext_reg(b,target);
    let odd=b.alloc_qubit(); b.cx(target[0],odd);
    cadd_nbit_const_direct_fast(b,&wide,SECP256K1_P,odd);
    for i in 0..N { b.swap(wide[i],wide[i+1]); }
    let threshold=load_const(b,N,(SECP256K1_P>>1)+U256::from(1));
    cmp_lt_into_fast(b,target,&threshold,odd); b.x(odd);
    unload_const(b,&threshold,(SECP256K1_P>>1)+U256::from(1));
    b.free(odd); unext_reg(b,high);
}

pub(super) fn double(b: &mut B, target: &[QubitId]) {
    let (wide,high)=ext_reg(b,target);
    for i in (0..N).rev() { b.swap(wide[i],wide[i+1]); }
    let modulus=load_const(b,N+1,SECP256K1_P);
    let reduced=b.alloc_qubit();
    cmp_lt_into_fast(b,&wide,&modulus,reduced); b.x(reduced);
    unload_const(b,&modulus,SECP256K1_P);
    csub_nbit_const_direct_fast(b,&wide,SECP256K1_P,reduced);
    b.cx(target[0],reduced); b.free(reduced); unext_reg(b,high);
}

pub(super) fn seed(b: &mut B, sign: QubitId, source: &[QubitId], target: &[QubitId], inverse: bool) {
    if inverse { negate(b,sign,target); }
    for (&s,&t) in source.iter().zip(target) { b.cx(s,t); }
    if !inverse { negate(b,sign,target); }
}
