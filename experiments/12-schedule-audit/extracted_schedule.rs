const N: usize = 256;
const VALUE_WIDTH: usize = N + 3;
#[derive(Clone, Copy, Debug)]
struct BoundedProfile {
    rounds: usize,
    margin: usize,
    chunk_compare: usize,
    replay_fold: usize,
    endpoint_fold: usize,
    flag_compare: usize,
}

// Host-side experimental settings. The default emits the frozen baseline.
fn bounded_profile() -> BoundedProfile {
    let mut p = BoundedProfile {
        rounds: 704, margin: 4, chunk_compare: 26,
        replay_fold: 56, endpoint_fold: 55, flag_compare: 28,
    };
    match std::env::var("QIP_PINGPONG_PROFILE").as_deref().unwrap_or("base") {
        "base" => {}
        "rounds" => { p.rounds = 736; }
        "widths" => { p.rounds = 736; p.margin = 20; }
        "guarded" => {
            p.rounds = 736; p.margin = 20; p.chunk_compare = 40;
            p.replay_fold = 72; p.endpoint_fold = 71; p.flag_compare = 48;
        }
        other => panic!("unknown bounded QIP profile: {other}"),
    }
    p
}

fn value_width(round: usize) -> usize {
    const BREAK_1: usize = 40;
    const BREAK_2: usize = 304;
    const SLOPE_1: usize = 17;
    const SLOPE_2: usize = 33;
    const SLOPE_3: usize = 40;
    let start = N + bounded_profile().margin;
    let width = if round < BREAK_1 {
        start.saturating_sub(SLOPE_1 * round / 100)
    } else {
        let at_first = start.saturating_sub(SLOPE_1 * BREAK_1 / 100);
        if round < BREAK_2 {
            at_first.saturating_sub(SLOPE_2 * (round - BREAK_1) / 100)
        } else {
            let at_second = at_first.saturating_sub(SLOPE_2 * (BREAK_2 - BREAK_1) / 100);
            at_second.saturating_sub(SLOPE_3 * (round - BREAK_2) / 100)
        }
    };
    width.clamp(8, VALUE_WIDTH)
}


fn main() {
    let p = bounded_profile();
    println!("{},{},{},{},{},{}", p.rounds, p.margin, p.chunk_compare,
             p.replay_fold, p.endpoint_fold, p.flag_compare);
    for k in 0..800 { println!("{},{}", k, value_width(k)); }
}
