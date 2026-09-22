use alloy_primitives::U256;

use crate::weierstrass_elliptic_curve::WeierstrassEllipticCurve;

pub const DEFAULT_WINDOW_BITS: usize = 16;

#[derive(Clone, Debug)]
pub struct WindowTable {
    pub x: Vec<U256>,
    pub y: Vec<U256>,
}

pub fn window_bits_from_env() -> usize {
    let width = std::env::var("WINDOW_BITS")
        .ok()
        .and_then(|value| value.parse::<usize>().ok())
        .unwrap_or(DEFAULT_WINDOW_BITS);
    assert!(width <= 16, "WINDOW_BITS must lie in 0..=16");
    width
}

pub fn secp256k1() -> WeierstrassEllipticCurve {
    WeierstrassEllipticCurve {
        modulus: U256::from_str_radix(
            "FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F",
            16,
        )
        .unwrap(),
        a: U256::ZERO,
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

impl WindowTable {
    /// Builds T[j] = [j]G. Row zero is the elliptic-curve identity. The
    /// windowed adapter handles it coherently by disabling the coordinate
    /// updates that are defined only for nonidentity addends.
    pub fn new(window_bits: usize) -> Self {
        assert!(window_bits <= 16);
        let rows = 1usize << window_bits;
        let curve = secp256k1();
        let mut x = Vec::with_capacity(rows);
        let mut y = Vec::with_capacity(rows);
        let mut point = (U256::ZERO, U256::ZERO);
        for _ in 0..rows {
            x.push(point.0);
            y.push(point.1);
            point = curve.add(point.0, point.1, curve.gx, curve.gy);
        }
        Self { x, y }
    }

    pub fn len(&self) -> usize {
        self.x.len()
    }

    pub fn point(&self, row: usize) -> (U256, U256) {
        (self.x[row], self.y[row])
    }
}
