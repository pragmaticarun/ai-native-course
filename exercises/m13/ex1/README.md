# Ex 13.1: an availability state machine with honest UX

Write `Machine` in `impl.py`: it turns a feature's status and runtime errors into what the user sees.

| input | `ui` becomes | notes |
|---|---|---|
| `on_status("UNAVAILABLE")` | `"unsupported"` | set `fallback = "litert_lm_cpu"` |
| `on_status("DOWNLOADABLE")` | `"needs_download"` | ask before downloading |
| `on_status("DOWNLOADING")` | `"downloading"` | |
| `on_status("AVAILABLE")` | `"ready"` | |
| `on_progress(f)` | `"downloading"`, or `"ready"` at 1.0 | `progress` never goes backwards |
| `on_error("BACKGROUND_USE_BLOCKED")` | `"foreground_needed"` | don't retry in the background |
| `on_error("BUSY")` | `"retrying"` up to `max_retries` times, then `"fallback"` | |
| `on_error("PER_APP_BATTERY_USE_QUOTA_EXCEEDED")` | `"fallback"` | set `fallback` too |

Unknown statuses or error codes raise `ValueError`. The tests feed it the answers the docs say a
Galaxy A73 should give (Gemini Nano features unavailable; speech recognition Basic mode available).
Those answers come from documentation, **not from the device (untested)**: when you have the phone,
log the real `checkFeatureStatus` results and turn them into a fixture.

Reference: `examples/python/m13/availability.py` and the KMP `Availability.kt`.
