package course.m9

import io.modelcontextprotocol.kotlin.sdk.server.Server
import io.modelcontextprotocol.kotlin.sdk.server.ServerOptions
import io.modelcontextprotocol.kotlin.sdk.types.CallToolResult
import io.modelcontextprotocol.kotlin.sdk.types.Implementation
import io.modelcontextprotocol.kotlin.sdk.types.ServerCapabilities
import io.modelcontextprotocol.kotlin.sdk.types.TextContent
import io.modelcontextprotocol.kotlin.sdk.types.ToolAnnotations
import io.modelcontextprotocol.kotlin.sdk.types.ToolSchema
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.buildJsonArray
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.contentOrNull
import kotlinx.serialization.json.doubleOrNull
import kotlinx.serialization.json.intOrNull
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import kotlinx.serialization.json.put
import kotlinx.serialization.json.putJsonObject

/**
 * M9: the media-probe `probe` tool on the MCP Kotlin SDK (0.16.0), in commonMain.
 *
 * Running ffprobe is platform work, so it sits behind [FfprobeRunner]: a jvmMain/androidMain
 * implementation would start a process (or, on Android, use Media3/MediaExtractor). Tests use
 * a fake runner. Same contract as the Python and Rust servers: structured output with
 * `path`, `duration_s` and `streams`, and an error result for paths outside the media root.
 */
fun interface FfprobeRunner {
    suspend fun probeJson(relativePath: String): String
}

private val json = Json { ignoreUnknownKeys = true }

/** Rejects absolute paths and `..` segments (least privilege), like the other servers. */
fun isSafeRelative(path: String): Boolean =
    path.isNotEmpty() && !path.startsWith("/") && path.split('/', '\\').none { it == ".." }

/** Turns `ffprobe -show_format -show_streams -of json` output into the shared contract. */
fun summarise(path: String, ffprobeJson: String): JsonObject {
    val root = json.parseToJsonElement(ffprobeJson).jsonObject
    val duration = root["format"]?.jsonObject?.get("duration")?.jsonPrimitive?.contentOrNull
        ?.toDoubleOrNull() ?: error("ffprobe output has no format.duration")
    val streams = root["streams"]?.jsonArray.orEmpty()
    return buildJsonObject {
        put("path", path)
        put("duration_s", duration)
        put(
            "streams",
            buildJsonArray {
                for (s in streams) {
                    val o = s.jsonObject
                    add(
                        buildJsonObject {
                            put("codec_type", o["codec_type"]?.jsonPrimitive?.contentOrNull ?: "unknown")
                            put("codec_name", o["codec_name"]?.jsonPrimitive?.contentOrNull ?: "unknown")
                            o["width"]?.jsonPrimitive?.intOrNull?.let { put("width", it) }
                            o["height"]?.jsonPrimitive?.intOrNull?.let { put("height", it) }
                            o["sample_rate"]?.jsonPrimitive?.let { p ->
                                (p.intOrNull ?: p.contentOrNull?.toIntOrNull())?.let { put("sample_rate", it) }
                            }
                        },
                    )
                }
            },
        )
    }
}

fun mediaProbeServer(runner: FfprobeRunner): Server {
    val server = Server(
        serverInfo = Implementation(name = "media-probe-kotlin", version = "0.1.0"),
        options = ServerOptions(capabilities = ServerCapabilities(tools = ServerCapabilities.Tools(listChanged = false))),
    )
    val pathSchema = ToolSchema(
        properties = buildJsonObject {
            putJsonObject("path") {
                put("type", "string")
                put("description", "Path relative to the media root")
            }
        },
        required = listOf("path"),
    )
    val outputSchema = ToolSchema(
        properties = buildJsonObject {
            putJsonObject("path") { put("type", "string") }
            putJsonObject("duration_s") { put("type", "number") }
            putJsonObject("streams") { put("type", "array") }
        },
        required = listOf("path", "duration_s", "streams"),
    )
    server.addTool(
        name = "probe",
        description = "Probe a media file with ffprobe: duration and streams. Read-only.",
        inputSchema = pathSchema,
        outputSchema = outputSchema,
        toolAnnotations = ToolAnnotations(readOnlyHint = true, destructiveHint = false),
    ) { request ->
        val path = request.arguments?.get("path")?.jsonPrimitive?.contentOrNull.orEmpty()
        if (!isSafeRelative(path)) {
            CallToolResult(content = listOf(TextContent("path escapes media root: $path")), isError = true)
        } else {
            val summary = summarise(path, runner.probeJson(path))
            val duration = summary["duration_s"]?.jsonPrimitive?.doubleOrNull
            CallToolResult(
                content = listOf(TextContent("$path: $duration s")),
                structuredContent = summary,
            )
        }
    }
    return server
}
