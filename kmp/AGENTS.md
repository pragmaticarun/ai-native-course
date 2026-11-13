# kmp/ — Kotlin Multiplatform

Verify: `./gradlew :shared:jvmTest`

- JDK 21. Only the JVM target is built; there is no Android SDK on CI or on the owner's box, so don't
  add `androidMain` code that has to compile, and don't install the SDK.
- Agent logic goes in `shared/src/commonMain`; platform backends sit behind interfaces with fakes in tests.
- Versions live in `gradle/libs.versions.toml`; change them there, never inline.
