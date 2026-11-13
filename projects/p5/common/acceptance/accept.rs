// Hidden acceptance tests (the ground truth), copied into the crate only while judging.
use clipcore::*;

#[test]
fn frames() {
    assert_eq!(to_frames(0, 0, 1, 5, 25), 30);
    assert_eq!(to_frames(1, 0, 0, 0, 25), 90_000);
}

#[test]
fn clamp() {
    assert_eq!(clamp_volume(6.0), 0.0);
    assert_eq!(clamp_volume(-80.0), -60.0);
}

#[test]
fn fps() {
    assert_eq!(fps_from_str(" 25"), Some(25));
    assert_eq!(fps_from_str("0"), None);
    assert_eq!(fps_from_str("x"), None);
}
