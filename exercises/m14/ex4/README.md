# Ex 14.4: port the probe tool to Kotlin with MediaExtractor (Android; untested)

Port the M9/M14 `probe` tool (duration, streams, sample rate) to Android using the platform
`MediaExtractor` (tracks and their `MediaFormat`: `KEY_MIME`, `KEY_DURATION`, `KEY_SAMPLE_RATE`,
`KEY_WIDTH`/`KEY_HEIGHT`) and `MediaMetadataRetriever` (`METADATA_KEY_DURATION`). Put the parsing in
KMP commonMain behind the existing `FfprobeRunner`-style seam (`kmp/shared/.../m9/MediaProbeServer.kt`)
so the shared contract tests still run on the JVM, and the Android implementation in androidMain.

**Untested here:** it needs the Android SDK (not installed on the course box) and a device or emulator.
Check the key names against the Android reference
(https://developer.android.com/reference/android/media/MediaExtractor,
https://developer.android.com/reference/android/media/MediaMetadataRetriever) and compare your
output with `ffprobe` on the same files.
