// No feature gate: plain `cargo test` runs these (the old file only ran with --features full).
use clipcore::*;

#[test]
fn frames_include_the_frame_field() {
    assert_eq!(to_frames(1, 0, 0, 0, 25), 90_000);
    assert_eq!(to_frames(0, 0, 1, 5, 25), 30);
}

#[test]
fn volume_is_clamped_both_ways() {
    assert_eq!(clamp_volume(6.0), 0.0);
    assert_eq!(clamp_volume(-80.0), -60.0);
}

#[test]
fn fps_trims_and_rejects_zero() {
    assert_eq!(fps_from_str(" 25"), Some(25));
    assert_eq!(fps_from_str("0"), None);
}
