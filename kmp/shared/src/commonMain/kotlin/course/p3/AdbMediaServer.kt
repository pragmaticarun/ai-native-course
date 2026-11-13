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
fun isSafeDevicePath(path: String): Boolean =
    path.startsWith("/sdcard/") && path.split('/').none { it == ".." } &&
        path.none { it in ";&|`$<>\\\"' \n" }

/**
 * Parses an intent into steps. Recognised: "trim to N s" / "first N s" / "N to M s",
 * "mute" / "no audio" / "remove audio", "NNNp". Anything else is an error, not a guess.
 */
fun planTransform(intent: String): Result<List<Step>> {
    val text = intent.lowercase()
    val steps = mutableListOf<Step>()
    Regex("""(?:from\s+)?(\d+(?:\.\d+)?)\s*(?:s|sec\w*)?\s*(?:to|-)\s*(\d+(?:\.\d+)?)\s*(?:s|sec)""")
        .find(text)?.let { steps += Step.Trim(it.groupValues[1].toDouble(), it.groupValues[2].toDouble()) }
        ?: Regex("""(?:trim to|first|keep)\s+(\d+(?:\.\d+)?)\s*(?:s|sec)""").find(text)
            ?.let { steps += Step.Trim(0.0, it.groupValues[1].toDouble()) }
    if (Regex("""\b(mute|no audio|remove audio|silent)\b""").containsMatchIn(text)) steps += Step.RemoveAudio
    Regex("""\b(\d{3,4})p\b""").find(text)?.let {
        val h = it.groupValues[1].toInt()
        if (h !in HEIGHTS) return Result.failure(IllegalArgumentException("unsupported height ${h}p; use $HEIGHTS"))
        steps += Step.Resize(h)
    }
    steps.filterIsInstance<Step.Trim>().firstOrNull()?.let {
        if (it.endS <= it.startS) return Result.failure(IllegalArgumentException("trim end must be after start"))
    }
    return if (steps.isEmpty()) {
        Result.failure(IllegalArgumentException("no edit recognised in \"$intent\"; say e.g. \"trim to 5 s, mute, 720p\""))
    } else {
        Result.success(steps)
    }
}

private fun err(text: String) = CallToolResult(content = listOf(TextContent(text)), isError = true)

private fun ok(text: String, structured: JsonObject) =
    CallToolResult(content = listOf(TextContent(text)), structuredContent = structured)

private fun JsonObject?.str(key: String) = this?.get(key)?.jsonPrimitive?.contentOrNull.orEmpty()

private fun schema(vararg props: Pair<String, String>) = ToolSchema(
    properties = buildJsonObject { for ((k, type) in props) putJsonObject(k) { put("type", type) } },
    required = props.map { it.first },
)

fun adbMediaServer(adb: Adb, transformer: MediaTransformer, confirmer: Confirmer): Server {
    val server = Server(
        serverInfo = Implementation(name = "adb-media-kotlin", version = "0.6.0"),
        options = ServerOptions(capabilities = ServerCapabilities(tools = ServerCapabilities.Tools(listChanged = false))),
    )
    var recordings = 0

    server.addTool(
        name = "screenrecord",
        description = "Record the device screen for 1-$MAX_RECORD_S seconds to /sdcard/. Asks the user first.",
        inputSchema = schema("seconds" to "integer"),
        toolAnnotations = ToolAnnotations(readOnlyHint = false, destructiveHint = false, openWorldHint = false),
    ) { request ->
        val seconds = request.arguments?.get("seconds")?.jsonPrimitive?.intOrNull
        if (seconds == null || seconds !in 1..MAX_RECORD_S) return@addTool err("seconds must be 1-$MAX_RECORD_S")
        if (!confirmer.confirm("Record your screen for $seconds s?")) return@addTool err("denied by user: nothing recorded")
        val path = "/sdcard/p3_rec_${++recordings}.mp4"
        val r = adb.run(listOf("shell", "screenrecord", "--time-limit", "$seconds", path))
        if (r.exitCode != 0) err("screenrecord failed: ${r.output}") else ok(path, buildJsonObject { put("device_path", path) })
    }

    server.addTool(
        name = "pull",
        description = "Copy a file from /sdcard/ on the device into the media root as `name` (relative).",
        inputSchema = schema("device_path" to "string", "name" to "string"),
        toolAnnotations = ToolAnnotations(readOnlyHint = false, destructiveHint = false, openWorldHint = false),
    ) { request ->
        val src = request.arguments.str("device_path")
        val name = request.arguments.str("name")
        if (!isSafeDevicePath(src)) return@addTool err("device_path must be under /sdcard/ with no .. or shell characters")
        if (!isSafeRelative(name)) return@addTool err("name escapes media root: $name")
        val r = adb.run(listOf("pull", src, "media/$name"))
        if (r.exitCode != 0) err("pull failed: ${r.output}") else ok(name, buildJsonObject { put("path", name) })
    }

    server.addTool(
        name = "transform",
        description = "Edit a media file from a plain-language intent (trim to N s, mute, 360p/480p/720p/1080p). " +
            "Writes `out`; asks before overwriting an existing file.",
        inputSchema = schema("path" to "string", "intent" to "string", "out" to "string"),
        toolAnnotations = ToolAnnotations(readOnlyHint = false, destructiveHint = true, openWorldHint = false),
    ) { request ->
        val path = request.arguments.str("path")
        val out = request.arguments.str("out")
        if (!isSafeRelative(path) || !isSafeRelative(out)) return@addTool err("path escapes media root")
        val steps = planTransform(request.arguments.str("intent")).getOrElse { return@addTool err(it.message.orEmpty()) }
        if (out == path && !confirmer.confirm("Overwrite $path?")) return@addTool err("denied by user: $path unchanged")
        val duration = transformer.transform(path, steps, out)
        ok(
            "$out: ${steps.size} steps, $duration s",
            buildJsonObject {
                put("path", out)
                put("duration_s", duration)
                put("steps", buildJsonArray { steps.forEach { add(kotlinx.serialization.json.JsonPrimitive(it.toString())) } })
            },
        )
    }
    return server
}
