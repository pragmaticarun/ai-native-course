# kmp/ — Kotlin Multiplatform examples

`shared/src/commonMain` holds platform-neutral agent logic that depends only on the small
`OnDeviceLlm` / `AgentTool` interfaces. Tests in `commonTest` run against fakes.

| Package | Module | What |
|---|---|---|
| `course.m2` | M2 | notification → `{title, date, location}` with JSON validation, one repair retry, `BUSY` backoff; fakes for the LiteRT-LM (A73) and Gemini Nano paths |
| `course.m4` | M4 | fit prompt + history into a 2,048 / ~4,000-token window with a running summary |
| `course.m5` | M5 | confirmation decorator for destructive tools (on-device HITL) |
| `course.m9` | M9 | media-probe MCP server on the MCP Kotlin SDK 0.16.0 (`probe` tool, path safety); tested with the SDK's in-memory `ChannelTransport` and client. The SDK speaks protocol 2025-11-25 (not 2026-07-28) |

```bash
./gradlew :shared:jvmTest    # JDK 21; the wrapper downloads Gradle 9.9.1
```

**Status:** only the **JVM target** is built and tested (locally and in CI). The `androidMain`
target, real LiteRT-LM / ML Kit backends, and any run on the Galaxy A73 are **not done yet**
(planned for M13 / P6). Types such as `ErrorCode` and `AgentTool` are our own and mirror
documented ML Kit concepts; they are not the ML Kit API.
