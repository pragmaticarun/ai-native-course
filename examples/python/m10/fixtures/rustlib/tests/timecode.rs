#![cfg(feature = "full")]

use timecode::*;

const ONE_HOUR: Timecode = Timecode { h: 1, m: 0, s: 0, f: 0 };

#[test]
fn to_frames_counts_every_unit() {
    assert_eq!(to_frames(ONE_HOUR, 25), 90_000);
    assert_eq!(to_frames(Timecode { h: 0, m: 1, s: 2, f: 3 }, 25), 1_553);
}

#[test]
fn from_frames_inverts_to_frames() {
    for n in [0u64, 24, 25, 1_553, 90_000, 90_001] {
        assert_eq!(to_frames(from_frames(n, 25), 25), n);
    }
}

#[test]
fn parse_reads_and_validates() {
    assert_eq!(parse("01:00:00:00"), Ok(ONE_HOUR));
    assert!(parse("00:61:00:00").is_err());
    assert!(parse("00:00:00").is_err());
}

#[test]
fn format_zero_pads() {
    assert_eq!(format(Timecode { h: 1, m: 2, s: 3, f: 4 }), "01:02:03:04");
}

#[test]
fn between_is_none_when_reversed() {
    let a = Timecode { h: 0, m: 0, s: 1, f: 0 };
    assert_eq!(between(a, ONE_HOUR, 25), Some(89_975));
    assert_eq!(between(ONE_HOUR, a, 25), None);
}
