package course.m13

import course.m5.AgentTool
import course.m5.Confirmer
import course.m5.guardDestructive
import io.modelcontextprotocol.kotlin.sdk.server.Server
import io.modelcontextprotocol.kotlin.sdk.server.ServerOptions
import io.modelcontextprotocol.kotlin.sdk.types.CallToolResult
import io.modelcontextprotocol.kotlin.sdk.types.Implementation
import io.modelcontextprotocol.kotlin.sdk.types.ServerCapabilities
import io.modelcontextprotocol.kotlin.sdk.types.TextContent
import io.modelcontextprotocol.kotlin.sdk.types.ToolAnnotations
import io.modelcontextprotocol.kotlin.sdk.types.ToolSchema
import kotlinx.coroutines.CoroutineDispatcher
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flow
import kotlinx.coroutines.withContext
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.contentOrNull
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import kotlinx.serialization.json.put
import kotlinx.serialization.json.putJsonObject

/**
 * M13 worked example: the offline "voice notes" agent, commonMain half.
 *
 * Tools (`search_notes`, `create_note`, `delete_note`) are defined ONCE as [NoteTool]s and
 * exposed two ways: to the local model's tool-calling loop ([VoiceNotesAgent]) and as MCP tools
 * ([voiceNotesMcpServer]). `delete_note` is destructive, so the loop wraps it with M5's
 * confirmation decorator. The model is the [LocalModel] interface: androidMain would implement
 * it with LiteRT-LM (CPU) / llama.cpp JNI / ExecuTorch; tests use [ScriptedLocalModel].
 *
 * UNTESTED: no androidMain backend exists yet (needs the Android SDK, not installed), and
 * nothing here has run on the Galaxy A73. Koog is not used: the loop is hand-written so it runs
 * with no extra dependency; the lesson maps it onto Koog's graph strategy conceptually.
 */
data class Note(val id: Int, val text: String)

class NoteStore(initial: List<String> = emptyList()) {
    private var next = 1
    val notes = initial.map { Note(next++, it) }.toMutableList()

    fun search(q: String) = notes.filter { it.text.contains(q, ignoreCase = true) }
    fun create(text: String) = Note(next++, text).also { notes += it }
    fun delete(id: Int) = notes.removeAll { it.id == id }
}

/** One tool definition, used by both the local loop and MCP. */
class NoteTool(
    override val name: String,
    val description: String,
    val params: Map<String, String>, // name -> description (all strings, all required)
    override val destructive: Boolean = false,
    private val body: suspend (Map<String, String>) -> String,
) : AgentTool {
    override suspend fun invoke(args: Map<String, String>): String {
        val missing = params.keys - args.keys
        return if (missing.isNotEmpty()) "error: missing $missing" else body(args)
    }

    val schema: ToolSchema
        get() = ToolSchema(
            properties = buildJsonObject {
                params.forEach { (p, d) -> putJsonObject(p) { put("type", "string"); put("description", d) } }
            },
            required = params.keys.toList(),
        )
}

fun noteTools(store: NoteStore): List<NoteTool> = listOf(
    NoteTool("search_notes", "Find notes containing a phrase. Read-only.", mapOf("query" to "phrase to look for")) { a ->
        store.search(a.getValue("query")).joinToString("\n") { "#${it.id}: ${it.text}" }.ifEmpty { "no matches" }
    },
    NoteTool("create_note", "Save a new note.", mapOf("text" to "the note text")) { a ->
        "created #${store.create(a.getValue("text")).id}"
    },
    NoteTool("delete_note", "Delete a note by id. Destructive.", mapOf("id" to "note id"), destructive = true) { a ->
        val id = a.getValue("id").toIntOrNull()
        when {
            id == null -> "error: id must be a number"
            store.delete(id) -> "deleted #$id"
            else -> "error: no note #$id"
        }
    },
)

/** What a local model returns per turn: a tool call or a final answer (streamed). */
sealed interface Turn {
    data class Call(val tool: String, val args: Map<String, String>) : Turn
    data class Final(val tokens: Flow<String>) : Turn
}

/** The backend seam. Implementations own a native engine, so they are [AutoCloseable]. */
interface LocalModel : AutoCloseable {
    suspend fun next(transcript: List<String>, tools: List<NoteTool>): Turn
    override fun close() {}
}

/**
 * Our own JSON tool-call format, `{"tool": "...", "args": {...}}`, for backends that return text.
 * (FunctionGemma and LiteRT-LM have their own formats; adapters translate into [Turn].)
 */
fun parseToolCall(text: String): Turn.Call? = runCatching {
    val o: JsonObject = Json.parseToJsonElement(text.trim()).jsonObject
    val args = o["args"]?.jsonObject.orEmpty().mapValues { it.value.jsonPrimitive.contentOrNull.orEmpty() }
    Turn.Call(o.getValue("tool").jsonPrimitive.content, args)
}.getOrNull()

/** Test/CI model: replays a script of turns and records what it was shown. */
class ScriptedLocalModel(private val script: List<String>) : LocalModel {
    var closed = false
    val seen = mutableListOf<List<String>>()
    private var i = 0

    override suspend fun next(transcript: List<String>, tools: List<NoteTool>): Turn {
        seen += transcript.toList()
        val line = script.getOrElse(i++) { "Done." }
        return parseToolCall(line) ?: Turn.Final(flow { line.split(" ").forEach { emit("$it ") } })
    }

    override fun close() { closed = true }
}

data class AgentRun(val answer: String, val calls: List<String>, val turns: Int)

/**
 * The loop: observe -> ask the model -> run a tool (guarded) -> append the result, until a
 * final answer or [maxTurns]. Every model call runs on [engine], ONE thread that owns the native
 * runtime (LiteRT-LM and llama.cpp contexts are not thread-safe), via `limitedParallelism(1)`.
 */
@OptIn(ExperimentalCoroutinesApi::class)
class VoiceNotesAgent(
    private val model: LocalModel,
    tools: List<NoteTool>,
    confirmer: Confirmer,
    private val maxTurns: Int = 6,
    private val engine: CoroutineDispatcher = Dispatchers.Default.limitedParallelism(1),
) : AutoCloseable {
    private val defs = tools
    private val guarded = guardDestructive(tools, confirmer).associateBy { it.name }

    suspend fun run(userText: String): AgentRun {
        val transcript = mutableListOf("user: $userText")
        val calls = mutableListOf<String>()
        repeat(maxTurns) { turn ->
            when (val t = withContext(engine) { model.next(transcript, defs) }) {
                is Turn.Final -> {
                    val sb = StringBuilder()
                    t.tokens.collect { sb.append(it) }
                    return AgentRun(sb.toString().trim(), calls, turn + 1)
                }
                is Turn.Call -> {
                    val tool = guarded[t.tool]
                    val result = tool?.invoke(t.args) ?: "error: unknown tool ${t.tool}"
                    calls += t.tool
                    transcript += "tool ${t.tool}: $result"
                }
            }
        }
        return AgentRun("stopped: turn budget ($maxTurns) used up", calls, maxTurns)
    }

    override fun close() = model.close()
}

/** The same tools as an MCP server (e.g. for a desktop agent talking to the phone). */
fun voiceNotesMcpServer(tools: List<NoteTool>, confirmer: Confirmer): Server {
    val server = Server(
        serverInfo = Implementation(name = "voice-notes", version = "0.1.0"),
        options = ServerOptions(capabilities = ServerCapabilities(tools = ServerCapabilities.Tools(listChanged = false))),
    )
    val guarded = guardDestructive(tools, confirmer).associateBy { it.name }
    for (t in tools) {
        server.addTool(
            name = t.name,
            description = t.description,
            inputSchema = t.schema,
            toolAnnotations = ToolAnnotations(readOnlyHint = t.name.startsWith("search"), destructiveHint = t.destructive),
        ) { req ->
            val args = req.arguments.orEmpty().mapValues { it.value.jsonPrimitive.contentOrNull.orEmpty() }
            val out = guarded.getValue(t.name).invoke(args)
            CallToolResult(content = listOf(TextContent(out)), isError = out.startsWith("error") || out.startsWith("denied"))
        }
    }
    return server
}

/** Evals live in commonMain too, so the same golden cases run on the JVM and (later) on device. */
data class Golden(val ask: String, val expectCalls: List<String>, val expectInAnswer: String)

suspend fun evaluate(cases: List<Golden>, run: suspend (String) -> AgentRun): List<String> =
    cases.mapNotNull { c ->
        val r = run(c.ask)
        when {
            r.calls != c.expectCalls -> "${c.ask}: calls ${r.calls} != ${c.expectCalls}"
            !r.answer.contains(c.expectInAnswer, ignoreCase = true) -> "${c.ask}: answer '${r.answer}'"
            else -> null
        }
    }
