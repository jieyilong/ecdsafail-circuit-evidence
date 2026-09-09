//! Count the serialized emitted stream without materializing the circuit.
use std::io::Read;
fn main() {
    let path=std::env::args().nth(1).expect("ops.bin");
    let mut f=std::fs::File::open(path).unwrap();let mut header=[0u8;16];f.read_exact(&mut header).unwrap();assert_eq!(&header[..8],b"QECCOPSZ");
    let count=u64::from_le_bytes(header[8..].try_into().unwrap());let mut decoder=zstd::stream::read::Decoder::new(f).unwrap();
    let mut buffer=vec![0u8;56*32768];let mut kinds=[0u64;18];let mut remaining=count;
    while remaining>0 {
        let n=remaining.min(32768) as usize;decoder.read_exact(&mut buffer[..56*n]).unwrap();
        for row in buffer[..56*n].chunks_exact(56) {let kind=u32::from_le_bytes(row[..4].try_into().unwrap()) as usize;assert!(kind<18);kinds[kind]+=1;}
        remaining-=n as u64;
    }
    assert_eq!(decoder.read(&mut [0u8;1]).unwrap(),0);
    println!("{{\"operations\":{count},\"static_toffoli\":{},\"kinds\":{:?}}}",kinds[13]+kinds[14],kinds);
}
