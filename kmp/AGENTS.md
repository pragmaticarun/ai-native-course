# kmp/ — Kotlin Multiplatform

Verify: `./gradlew :shared:jvmTest :p6-agent:jvmTest` (JVM, no SDK needed) and, with the Android SDK,
`./gradlew :shared:testAndroidHostTest :p6-agent:testAndroidHostTest :p6-app:assembleDebug :p6-app:testDebugUnitTest :p6-app:assembleDebugAndroidTest`.

- JDK 21. Targets: `jvm()` and Android (`com.android.kotlin.multiplatform.library`, compileSdk 37, minSdk 29).
- The owner (Arunkumar) approved accepting the Android SDK license and installing the SDK on the box
  and in CI on 14 Nov 2026. Box SDK: `/home/box/opt/android-sdk` (`export ANDROID_HOME=...`).
  CI installs `platforms;android-37.0` and `build-tools;36.0.0` with `sdkmanager`.
- Instrumentation tests (`androidTest`) are compiled in CI but have not run on a device or emulator;
  say so wherever results are reported.
- Agent logic goes in `commonMain`; platform backends sit behind interfaces with fakes in tests.
- P6 sources live in `projects/p6` and are wired in `settings.gradle.kts`; pick the exercise variant
  with `-Pp6.variant=starter|solution` (default solution; the starter must fail its tests).
- Versions live in `gradle/libs.versions.toml`; change them there, never inline.
