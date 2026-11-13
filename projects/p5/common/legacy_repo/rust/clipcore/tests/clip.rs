#![cfg(feature = "full")]
use clipcore::*;

#[test]
fn one_hour_at_25() {
    assert_eq!(to_frames(1, 0, 0, 0, 25), 90_000);
}
