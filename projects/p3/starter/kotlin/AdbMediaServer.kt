package course.p3

import course.m5.Confirmer
import course.m9.isSafeRelative
import io.modelcontextprotocol.kotlin.sdk.server.Server
import io.modelcontextprotocol.kotlin.sdk.server.ServerOptions
import io.modelcontextprotocol.kotlin.sdk.types.CallToolResult
import io.modelcontextprotocol.kotlin.sdk.types.Implementation
import io.modelcontextprotocol.kotlin.sdk.types.ServerCapabilities
import io.modelcontextprotocol.kotlin.sdk.types.TextContent
import io.modelcontextprotocol.kotlin.sdk.types.ToolAnnotations
import io.modelcontextprotocol.kotlin.sdk.types.ToolSchema
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.buildJsonArray
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.contentOrNull
import kotlinx.serialization.json.intOrNull
import kotlinx.serialization.json.jsonPrimitive
import kotlinx.serialization.json.put
import kotlinx.serialization.json.putJsonObject

/**
 * STARTER (skeleton). Copy to kmp/shared/src/commonMain/kotlin/course/p3/ and fill in the
 * TODOs until kmp/shared/src/commonTest/kotlin/course/p3/AdbMediaServerTest.kt passes.
 *
 * P3 milestone 7 (Kotlin port): a device-side media server on the MCP Kotlin SDK 0.16.0,
 * in commonMain, tested on the JVM with fakes. No Android SDK, no device, no adb binary.
 *
 * Tools:
 * - `screenrecord(seconds)`: records the device screen (1-180 s). Recording a screen is
 *   private, so it always asks the user first through a [Confirmer] (M5's HITL gate).
 * - `pull(device_path, name)`: copies a file from `/sdcard/` into the media root under a
 *   safe relative name.
 * - `transform(path, intent)`: turns a plain-language intent ("trim to 5 s, mute, 720p")
 *   into a fixed list of edit steps, then runs them through a [MediaTransformer]. On Android
 *   that would be a Media3 Transformer; that path has not been built or run here.
 *
 * Every adb call goes through [Adb] as an argument list, never a shell string.
 */
data class AdbResult(val exitCode: Int, val output: String = "")

fun interface Adb {
    suspend fun run(args: List<String>): AdbResult
}

sealed interface Step {
    data class Trim(val startS: Double, val endS: Double) : Step
    data object RemoveAudio : Step
    data class Resize(val height: Int) : Step
}

fun interface MediaTransformer {
    /** Applies [steps] to [input] and writes [output]; returns the output duration (s). */
    suspend fun transform(input: String, steps: List<Step>, output: String): Double
}

const val MAX_RECORD_S = 180
val HEIGHTS = setOf(360, 480, 720, 1080)

/** Only files under /sdcard/, no `..`, no shell metacharacters. */
fun isSafeDevicePath(path: String): Boolean = TODO("under /sdcard/, no .., no shell characters: $path")

/**
 * Parses an intent into steps. Recognised: "trim to N s" / "first N s" / "N to M s",
 * "mute" / "no audio" / "remove audio", "NNNp". Anything else is an error, not a guess.
 */
fun planTransform(intent: String): Result<List<Step>> = TODO("parse $intent into Trim/RemoveAudio/Resize")

@Suppress("UNUSED_PARAMETER")
fun adbMediaServer(adb: Adb, transformer: MediaTransformer, confirmer: Confirmer): Server {
    val server = Server(
        serverInfo = Implementation(name = "adb-media-kotlin", version = "0.6.0"),
        options = ServerOptions(capabilities = ServerCapabilities(tools = ServerCapabilities.Tools(listChanged = false))),
    )
    // TODO: addTool("screenrecord") - 1..MAX_RECORD_S seconds, confirmer first, then
    //   adb.run(listOf("shell", "screenrecord", "--time-limit", "$seconds", path))
    // TODO: addTool("pull") - isSafeDevicePath(device_path), isSafeRelative(name),
    //   adb.run(listOf("pull", src, "media/$name"))
    // TODO: addTool("transform") - planTransform(intent), confirm before out == path,
    //   transformer.transform(path, steps, out); structured path/duration_s/steps
    return server
}
