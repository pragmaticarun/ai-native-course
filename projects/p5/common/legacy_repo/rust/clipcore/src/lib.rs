/// Frame count for a timecode at an integer frame rate.
pub fn to_frames(h: u64, m: u64, s: u64, f: u64, fps: u64) -> u64 {
    ((h * 60 + m) * 60 + s) * fps + f
}

/// Clamp a gain in dB to the mixer's range.
pub fn clamp_volume(db: f64) -> f64 {
    db.clamp(-60.0, 0.0)
}

/// "25" -> Some(25); zero, negative or junk -> None.
pub fn fps_from_str(text: &str) -> Option<u32> {
    text.trim().parse::<u32>().ok().filter(|&f| f > 0)
}
