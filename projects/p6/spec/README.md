# P6 · Field Notes: an on-device Android agent app (Kotlin Multiplatform + Koog)

**After:** M13 · **Language:** Kotlin · **Build:** `kmp/` Gradle (Kotlin 2.4.21, AGP 9.5.1, Koog 1.3.0)

An offline assistant that searches, creates, tags, summarises, deletes and shares notes and voice
memos. The agent lives in `commonMain`, so the same code runs on the JVM in CI (with a fake
tool-routing model) and on Android (Koog's LiteRT-LM client on the CPU).

## Layout

| Path | What |
|---|---|
| `common/` | provided: notes store, the six tools, sessions, `FakeLocalModel`, 20 golden prompts; `androidMain` LiteRT-LM backend |
| `starter/` | the agent and privacy router with TODOs (compiles, fails 5 of 9 evals) |
| `solution/` | reference agent and router (passes all 9) |
| `evals/` | `commonTest` suite, run as JVM tests and as Android host tests |
| `agent/` | Gradle module `:p6-agent` (jvm + Android library); picks the variant |
| `app/` | Gradle module `:p6-app`: the Compose app, a unit test, and instrumentation tests (device only) |

## Milestones

1. **Graph + tools.** A Koog graph strategy (LLM → tools → LLM … → text) over six tools. Golden
   prompts must produce the expected tool trajectory and final state.
2. **HITL.** `delete_*` and `share_*` ask the user first; "no" means the tool never runs.
3. **Privacy router.** Summaries stay on the device unless the user allowed the cloud, the phone is
   online, the text is long, and no note is private or contains an email or phone number.
4. **Persistence.** History, the tool trace and any pending approval are saved after every step, so
   the app survives configuration changes (ViewModel) and process death (files in `filesDir`); a
   dialog that was open when the process died is asked again and runs exactly once.
5. **On device.** Run the golden suite on the Galaxy A73 with FunctionGemma 270M on LiteRT-LM CPU,
   with networking off. (Device step: not run yet.)

## Run

```bash
cd kmp
./gradlew :p6-agent:jvmTest                        # solution: 9 pass
./gradlew :p6-agent:jvmTest -Pp6.variant=starter   # starter: 5 fail
# With the Android SDK (ANDROID_HOME set):
./gradlew :p6-agent:testAndroidHostTest :p6-app:assembleDebug :p6-app:testDebugUnitTest :p6-app:assembleDebugAndroidTest
# On a device with the model pushed to /data/local/tmp/llm (not run yet):
./gradlew :p6-app:connectedDebugAndroidTest
```
