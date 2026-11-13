package course.fieldnotes

import ai.koog.agents.core.agent.AIAgent
import ai.koog.agents.core.agent.config.AIAgentConfig
import ai.koog.agents.core.dsl.builder.strategy
import ai.koog.agents.core.dsl.extension.nodeExecuteTools
import ai.koog.agents.core.dsl.extension.nodeLLMRequest
import ai.koog.agents.core.dsl.extension.nodeLLMSendToolResults
import ai.koog.agents.core.dsl.extension.onTextMessage
import ai.koog.agents.core.dsl.extension.onToolCalls
import ai.koog.agents.core.tools.SimpleTool
import ai.koog.agents.core.tools.Tool
import ai.koog.agents.core.tools.ToolRegistry
import ai.koog.prompt.dsl.prompt
import ai.koog.prompt.executor.model.PromptExecutor
import ai.koog.prompt.llm.LLModel
import ai.koog.serialization.JSONSerializer
import kotlinx.coroutines.CancellationException
import kotlinx.serialization.KSerializer
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive

const val SYSTEM_PROMPT = "You are Field Notes, an offline assistant. Use the tools to search, create, tag, " +
    "summarise, delete or share the user's notes. Never claim an action you did not run."

/** The graph: LLM -> tools -> LLM ... until the model answers in text. */
fun fieldNotesStrategy() = strategy<String, String>("field_notes") {
    val callLLM by nodeLLMRequest()
    val runTools by nodeExecuteTools()
    val sendResults by nodeLLMSendToolResults()
    edge(nodeStart forwardTo callLLM)
    edge(callLLM forwardTo runTools onToolCalls { true })
    edge(callLLM forwardTo nodeFinish onTextMessage { true })
    edge(runTools forwardTo sendResults)
    edge(sendResults forwardTo runTools onToolCalls { true })
    edge(sendResults forwardTo nodeFinish onTextMessage { true })
}

/**
 * Field Notes agent. One Koog agent run per user turn; history, the tool trace and any pending
 * approval are saved in [sessions] after every step, so a new instance (after a configuration
 * change or process death) carries on where the old one stopped.
 */
class FieldNotesAgent(
    private val executor: PromptExecutor,
    private val model: LLModel,
    val store: NoteStore,
    private val gate: ApprovalGate,
    private val sessions: SessionStore,
    val router: PrivacyRouter = PrivacyRouter(),
    private val local: Summariser = FirstSentenceSummariser,
    private val cloud: Summariser? = null,
    private val maxIterations: Int = 12,
) {
    private var sessionId = ""
    private val resumers = mutableMapOf<String, suspend (String) -> String>()

    private fun update(f: (Session) -> Session) = sessions.save(f(sessions.load(sessionId)))

    /** Wraps a tool: records it in the trace and, for delete_ and share_, asks the user first. */
    private fun <A> wrap(tool: SimpleTool<A>, ser: KSerializer<A>): Tool<A, String> {
        val consequential = tool.name.startsWith("delete_") || tool.name.startsWith("share_")
        if (consequential) resumers[tool.name] = { json -> tool.execute(NoteStore.json.decodeFromString(ser, json)) }
        return object : Tool<A, String>(tool.argsType, tool.resultType, tool.descriptor) {
            override fun encodeResultToString(result: String, serializer: JSONSerializer) = result

            override suspend fun execute(args: A): String {
                val json = NoteStore.json.encodeToString(ser, args)
                update { it.copy(trace = it.trace + traceLine(tool.name, json)) }
                if (!consequential) return tool.execute(args)
                val pending = PendingAction(tool.name, json, "${tool.name} ${traceLine("", json).trim()}")
                update { it.copy(pending = pending) }
                val ok = gate.approve(pending)
                update { it.copy(pending = null) }
                return if (ok) tool.execute(args) else "the user declined ${pending.summary}"
            }
        }
    }

    private suspend fun pickSummariser(notes: List<Note>): Summariser {
        val d = router.decide(notes)
        return if (d.route == Route.CLOUD && cloud != null) cloud else local
    }

    private fun registry() = ToolRegistry.builder().tools(
        listOf(
            wrap(SearchNotesTool(store), SearchArgs.serializer()),
            wrap(CreateNoteTool(store), CreateArgs.serializer()),
            wrap(TagNoteTool(store), TagArgs.serializer()),
            wrap(SummariseNotesTool(store, ::pickSummariser), SummariseArgs.serializer()),
            wrap(DeleteNoteTool(store), IdArgs.serializer()),
            wrap(ShareNoteTool(store), ShareArgs.serializer()),
        ),
    ).build()

    suspend fun ask(sessionId: String, text: String): Reply {
        this.sessionId = sessionId
        val before = sessions.load(sessionId)
        val routesBefore = router.log.size
        val history = prompt("field-notes-$sessionId") {
            system(SYSTEM_PROMPT)
            before.turns.forEach { if (it.role == "user") user(it.text) else assistant(it.text) }
        }
        update { it.copy(turns = it.turns + Turn("user", text)) }
        val agent = AIAgent(
            promptExecutor = executor,
            agentConfig = AIAgentConfig(history, model, maxIterations),
            strategy = fieldNotesStrategy(),
            toolRegistry = registry(),
        )
        val answer = try {
            agent.run(text)
        } catch (e: CancellationException) {
            throw e
        } catch (e: Exception) {
            "stopped: ${e::class.simpleName}: ${e.message?.take(120)}"
        }
        update { it.copy(turns = it.turns + Turn("assistant", answer)) }
        val after = sessions.load(sessionId)
        return Reply(answer, after.trace.drop(before.trace.size), router.log.drop(routesBefore))
    }

    /** After a restart: re-ask the user about a persisted pending action, then run or drop it. */
    suspend fun resumePending(sessionId: String): String? {
        this.sessionId = sessionId
        if (resumers.isEmpty()) registry()
        val p = sessions.load(sessionId).pending ?: return null
        val result = if (gate.approve(p)) resumers.getValue(p.tool)(p.argsJson) else "the user declined ${p.summary}"
        update { it.copy(pending = null, turns = it.turns + Turn("assistant", result)) }
        return result
    }

    fun session(id: String): Session = sessions.load(id)

    companion object {
        fun traceLine(tool: String, json: String): String {
            val obj = NoteStore.json.parseToJsonElement(json) as JsonObject
            val args = obj.entries.sortedBy { it.key }.joinToString(" ") { (k, v) -> "$k=${(v as JsonPrimitive).content}" }
            return "$tool $args".trim()
        }
    }
}
