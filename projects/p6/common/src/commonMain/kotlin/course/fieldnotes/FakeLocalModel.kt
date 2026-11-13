package course.fieldnotes

import ai.koog.agents.core.tools.ToolDescriptor
import ai.koog.prompt.Prompt
import ai.koog.prompt.dsl.ModerationResult
import ai.koog.prompt.executor.model.PromptExecutor
import ai.koog.prompt.llm.LLMCapability
import ai.koog.prompt.llm.LLMProvider
import ai.koog.prompt.llm.LLModel
import ai.koog.prompt.message.Message
import ai.koog.prompt.message.MessagePart
import ai.koog.prompt.message.ResponseMetaInfo
import ai.koog.prompt.streaming.StreamFrame
import ai.koog.prompt.streaming.toStreamFrames
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flow
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.buildJsonObject
import kotlin.time.Clock

/**
 * A deterministic stand-in for the on-device tool-routing model (FunctionGemma 270M on the A73).
 * It reads the latest user message and emits Koog tool calls, so the real agent graph, tools,
 * HITL and persistence run in CI without a model file. It is not a language model: it measures
 * the plumbing, not model quality.
 *
 * - [Mode.ROUTER] understands paraphrases ("jot down", "remove", "send ... to") and chains
 *   steps joined by " then ".
 * - [Mode.KEYWORD] is a weaker baseline: literal verbs only, one step. The eval reports both, so
 *   you can see the trajectory metric tell a better router from a worse one.
 */
class FakeLocalModel(private val mode: Mode = Mode.ROUTER) : PromptExecutor() {
    enum class Mode { ROUTER, KEYWORD }

    var requests = 0
        private set

    data class Call(val tool: String, val args: Map<String, Any>)

    override suspend fun execute(prompt: Prompt, model: LLModel, tools: List<ToolDescriptor>): Message.Assistant {
        requests++
        val msgs = prompt.messages
        val userIdx = msgs.indexOfLast { m -> m is Message.User && m.parts.any { it is MessagePart.Text } }
        val userText = (msgs.getOrNull(userIdx) as? Message.User)
            ?.parts?.filterIsInstance<MessagePart.Text>()?.joinToString(" ") { it.text }.orEmpty()
        val results = msgs.drop(userIdx + 1).flatMap { it.parts }.filterIsInstance<MessagePart.Tool.Result>()
        val steps = if (mode == Mode.ROUTER) userText.split(Regex("\\s+then\\s+", RegexOption.IGNORE_CASE)) else listOf(userText)
        val meta = ResponseMetaInfo(Clock.System.now())
        if (results.size < steps.size) {
            val lastCreated = results.lastOrNull { it.output.startsWith("created note #") }?.output?.substringAfter('#')?.toIntOrNull()
            val call = parse(steps[results.size], lastCreated)
            val known = tools.any { it.name == call?.tool }
            if (call != null && known) {
                val args = buildJsonObject {
                    call.args.forEach { (k, v) -> put(k, if (v is Int) JsonPrimitive(v) else JsonPrimitive(v.toString())) }
                }
                return Message.Assistant(MessagePart.Tool.Call(id = "call_${requests}", tool = call.tool, args = args), meta)
            }
        }
        val text = when {
            results.isNotEmpty() -> results.joinToString("; ") { it.output }
            else -> "I can search, create, tag, summarise, delete or share your notes."
        }
        return Message.Assistant(text, meta)
    }

    fun parse(raw: String, lastCreated: Int? = null): Call? {
        val t = raw.trim().lowercase().trimEnd('?', '.', '!')
        val id = Regex("note\\s*#?(\\d+)").find(t)?.groupValues?.get(1)?.toInt()
            ?: if (Regex("\\bit\\b").containsMatchIn(t)) lastCreated else null
        val router = mode == Mode.ROUTER
        fun has(vararg ws: String) = ws.any { Regex("\\b$it\\b").containsMatchIn(t) }
        return when {
            has("delete") || (router && has("remove", "bin")) -> id?.let { Call("delete_note", mapOf("id" to it)) }
            has("share") || (router && has("send")) -> {
                val to = Regex("\\b(?:with|to)\\s+(\\S+)$").find(t)?.groupValues?.get(1) ?: return null
                id?.let { Call("share_note", mapOf("id" to it, "to" to to)) }
            }
            has("tag") || (router && has("label")) -> {
                val tag = Regex("\\b(?:as|with)\\s+(\\w+)$").find(t)?.groupValues?.get(1) ?: return null
                id?.let { Call("tag_note", mapOf("id" to it, "tag" to tag)) }
            }
            has("summarise", "summarize") || (router && has("summary")) -> Call("summarise_notes", mapOf("query" to keywords(t)))
            (has("create") && ':' in t) || (router && (t.startsWith("jot down") || t.startsWith("remember"))) -> {
                val body = raw.substringAfter(':', raw.substringAfter(' ')).trim()
                Call("create_note", mapOf("title" to body.split(" ").take(4).joinToString(" "), "body" to body))
            }
            has("find", "search") || (router && (t.startsWith("what did i") || has("show", "look"))) ->
                Call("search_notes", mapOf("query" to keywords(t)))
            else -> null
        }
    }

    private fun keywords(t: String): String =
        t.split(Regex("[^a-z0-9@.]+")).filter { it.isNotBlank() && it !in STOP }.joinToString(" ")

    override fun executeStreaming(prompt: Prompt, model: LLModel, tools: List<ToolDescriptor>): Flow<StreamFrame> =
        flow { execute(prompt, model, tools).toStreamFrames().forEach { emit(it) } }

    override suspend fun moderate(prompt: Prompt, model: LLModel) = ModerationResult(false, emptyMap())

    override fun close() {}

    companion object {
        /** The model id the fake answers to; on the device this is the LiteRT FunctionGemma model. */
        val MODEL = LLModel(LLMProvider("fake-local", "Fake local"), "fake-functiongemma", listOf(LLMCapability.Tools, LLMCapability.Completion))

        private val STOP = setOf(
            "find", "search", "for", "my", "notes", "note", "about", "what", "did", "i", "write", "show", "me", "the",
            "of", "a", "an", "summarise", "summarize", "give", "summary", "everything", "all", "look", "up", "on", "please",
        )
    }
}
