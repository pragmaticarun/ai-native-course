# Field Notes (Android) — agent instructions

Setup: `./gradlew help`
Verify: `./gradlew :app:testDebugUnitTest :app:lintDebug`

- Unit tests and lint are the fast oracle. Run them after every change; they need no device.
- Screenshot tests (if the module has them) are the next oracle for UI changes; review the diff images,
  never re-record the baselines to make a failure go away.
- Device steps (install, launch, Logcat) need an emulator or a phone: ask before starting one.
- Never commit `local.properties`, keystores or `google-services.json`.
- Kotlin style: ktlint via `./gradlew :app:ktlintCheck` if configured; otherwise follow the existing code.
