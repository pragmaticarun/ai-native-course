package course.fieldnotes

import ai.koog.agents.core.tools.ToolDescriptor
import ai.koog.agents.testing.tools.getMockExecutor
import ai.koog.prompt.Prompt
import ai.koog.prompt.dsl.ModerationResult
import ai.koog.prompt.executor.model.PromptExecutor
import ai.koog.prompt.llm.LLModel
import ai.koog.prompt.message.Message
import ai.koog.prompt.message.MessagePart
import ai.koog.prompt.message.ResponseMetaInfo
import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.cancelAndJoin
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.emptyFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.withContext
import kotlinx.coroutines.withTimeout
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.put
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertNotNull
import kotlin.test.assertNull
import kotlin.test.assertTrue
import kotlin.time.Clock
import kotlin.time.Duration.Companion.seconds

/** Records every prompt the agent sends, then delegates. */
class SpyExecutor(private val inner: PromptExecutor) : PromptExecutor() {
    val prompts = mutableListOf<Prompt>()
    override suspend fun execute(prompt: Prompt, model: LLModel, tools: List<ToolDescriptor>): Message.Assistant {
        prompts += prompt
        return inner.execute(prompt, model, tools)
    }
    override fun executeStreaming(prompt: Prompt, model: LLModel, tools: List<ToolDescriptor>) = inner.executeStreaming(prompt, model, tools)
    override suspend fun moderate(prompt: Prompt, model: LLModel) = inner.moderate(prompt, model)
    override fun close() {}
}

class RecordingGate(private val answer: Boolean) : ApprovalGate {
    val asked = mutableListOf<PendingAction>()
    override suspend fun approve(action: PendingAction): Boolean { asked += action; return answer }
}

data class GoldenRow(val id: String, val trajectoryOk: Boolean, val stateOk: Boolean, val got: List<String>)

fun agentFor(
    store: NoteStore = NoteStore.sample(),
    gate: ApprovalGate = RecordingGate(true),
    sessions: SessionStore = SessionStore(),
    executor: PromptExecutor = FakeLocalModel(),
    router: PrivacyRouter = PrivacyRouter(),
    cloud: Summariser? = null,
    maxIterations: Int = 12,
) = FieldNotesAgent(executor, FakeLocalModel.MODEL, store, gate, sessions, router, FirstSentenceSummariser, cloud, maxIterations)

suspend fun runGolden(mode: FakeLocalModel.Mode): List<GoldenRow> = GOLDEN.map { g ->
    val store = NoteStore.sample()
    val reply = agentFor(store, RecordingGate(g.approve), executor = FakeLocalModel(mode)).ask(g.id, g.prompt)
    GoldenRow(g.id, reply.trace == g.expected, g.check(store), reply.trace)
}

class P6Test {
    @Test
    fun goldenTrajectoriesAndState() = runTest(timeout = 120.seconds) {
        val router = runGolden(FakeLocalModel.Mode.ROUTER)
        val keyword = runGolden(FakeLocalModel.Mode.KEYWORD)
        fun acc(rows: List<GoldenRow>, f: (GoldenRow) -> Boolean) = rows.count(f).toDouble() / rows.size
        println("P6 golden: router trajectory=${acc(router) { it.trajectoryOk }} state=${acc(router) { it.stateOk }}; " +
            "keyword trajectory=${acc(keyword) { it.trajectoryOk }} state=${acc(keyword) { it.stateOk }}")
        router.filter { !it.trajectoryOk || !it.stateOk }.forEach { println("  FAIL ${it.id} got=${it.got}") }
        keyword.filter { !it.trajectoryOk }.forEach { println("  keyword miss ${it.id} got=${it.got}") }
        assertTrue(router.all { it.trajectoryOk && it.stateOk }, "every golden prompt passes with the router fake")
        assertTrue(acc(keyword) { it.trajectoryOk } < 1.0, "the metric separates the weaker baseline")
    }

    @Test
    fun deleteAndShareAskFirstAndRespectNo() = runTest {
        val store = NoteStore.sample()
        val gate = RecordingGate(false)
        val agent = agentFor(store, gate)
        val r1 = agent.ask("s", "Delete note 3")
        val r2 = agent.ask("s", "Share note 1 with ravi@example.com")
        assertEquals(listOf("delete_note", "share_note"), gate.asked.map { it.tool })
        assertNotNull(store.get(3))
        assertTrue(store.outbox.isEmpty())
        assertTrue("declined" in r1.text && "declined" in r2.text, "${r1.text} / ${r2.text}")
    }

    @Test
    fun safeToolsDoNotAsk() = runTest {
        val gate = RecordingGate(true)
        val agent = agentFor(gate = gate)
        listOf("Find my notes about kotlin", "Create a note: x", "Tag note 1 as y", "Summarise everything").forEach { agent.ask("s", it) }
        assertTrue(gate.asked.isEmpty())
    }

    @Test
    fun pendingApprovalSurvivesProcessDeath() = runTest(timeout = 60.seconds) {
        val notesDisk = MemoryPersist()
        val sessionsDisk = MemoryPersist()
        NoteStore.sample(notesDisk).all() // write nothing yet; first save happens on change
        val never = ApprovalGate { CompletableDeferred<Boolean>().await() }
        withContext(Dispatchers.Default) {
            val first = agentFor(NoteStore.sample(notesDisk), never, SessionStore(sessionsDisk))
            val job = launch { first.ask("s1", "Delete note 4") }
            withTimeout(10_000) { while (SessionStore(sessionsDisk).load("s1").pending == null) delay(5) }
            job.cancelAndJoin() // the process dies while the dialog is up
        }
        val reborn = NoteStore.sample(notesDisk)
        assertNotNull(reborn.get(4), "nothing ran before approval")
        val gate = RecordingGate(true)
        val second = agentFor(reborn, gate, SessionStore(sessionsDisk))
        assertEquals("delete_note id=4", second.session("s1").pending?.summary)
        assertEquals("deleted note #4", second.resumePending("s1"))
        assertNull(reborn.get(4))
        assertNull(second.resumePending("s1"), "runs exactly once")
        assertEquals(1, gate.asked.size)
    }

    @Test
    fun historySurvivesANewInstance() = runTest {
        val disk = MemoryPersist()
        agentFor(sessions = SessionStore(disk)).ask("s", "Find my notes about kotlin")
        val spy = SpyExecutor(FakeLocalModel())
        val again = agentFor(sessions = SessionStore(disk), executor = spy)
        again.ask("s", "Hello")
        val session = again.session("s")
        assertEquals(4, session.turns.size)
        assertEquals(listOf("search_notes query=kotlin"), session.trace)
        val texts = spy.prompts.first().messages.flatMap { it.parts }.filterIsInstance<MessagePart.Text>().map { it.text }
        assertTrue("Find my notes about kotlin" in texts, "earlier turns are replayed into the prompt")
    }

    @Test
    fun privacyRouterKeepsPrivateAndPersonalDataLocal() = runTest {
        val long = "Field trip log. " + "We walked the river trail and counted birds. ".repeat(20)
        fun storeWith(vararg notes: Note) = NoteStore(notes.toList())
        val open = RouterSettings(cloudAllowed = true, online = true)
        val cases = listOf(
            Triple(storeWith(Note(1, "trip", long, setOf("private"))), open, Route.LOCAL),
            Triple(storeWith(Note(1, "trip", long + " Mail asha@example.com.")), open, Route.LOCAL),
            Triple(storeWith(Note(1, "trip", long + " Call 555-0100.")), open, Route.LOCAL),
            Triple(storeWith(Note(1, "trip", long)), open.copy(online = false), Route.LOCAL),
            Triple(storeWith(Note(1, "trip", long)), RouterSettings(online = true), Route.LOCAL),
            Triple(storeWith(Note(1, "trip", "short")), open, Route.LOCAL),
            Triple(storeWith(Note(1, "trip", long)), open, Route.CLOUD),
        )
        for ((store, settings, want) in cases) {
            val cloud = CountingSummariser(FirstSentenceSummariser)
            val r = agentFor(store, router = PrivacyRouter(settings), cloud = cloud).ask("s", "Summarise everything")
            assertEquals(want, r.routes.single().route, r.routes.toString())
            assertEquals(if (want == Route.CLOUD) 1 else 0, cloud.calls)
        }
    }

    @Test
    fun defaultSettingsNeverTouchTheCloud() = runTest(timeout = 120.seconds) {
        val cloud = CountingSummariser(FirstSentenceSummariser)
        GOLDEN.forEach { g ->
            val r = agentFor(gate = RecordingGate(g.approve), cloud = cloud).ask(g.id, g.prompt)
            assertTrue(r.routes.all { it.route == Route.LOCAL })
        }
        assertEquals(0, cloud.calls)
    }

    @Test
    fun koogMockExecutorDrivesTheSameAgent() = runTest {
        val store = NoteStore.sample()
        val mock = getMockExecutor {
            mockLLMToolCall(SearchNotesTool(store), SearchArgs("gradle")) onRequestContains "build tips"
            mockLLMAnswer("Here is what I found.").asDefaultResponse
        }
        val r = agentFor(store, executor = mock).ask("s", "any build tips?")
        assertEquals(listOf("search_notes query=gradle"), r.trace)
        assertEquals("Here is what I found.", r.text)
    }

    @Test
    fun stepBudgetStopsALoopingModel() = runTest {
        val looping = object : PromptExecutor() {
            override suspend fun execute(prompt: Prompt, model: LLModel, tools: List<ToolDescriptor>) = Message.Assistant(
                MessagePart.Tool.Call(id = "c", tool = "search_notes", args = buildJsonObject { put("query", "kotlin") }),
                ResponseMetaInfo(Clock.System.now()),
            )
            override fun executeStreaming(prompt: Prompt, model: LLModel, tools: List<ToolDescriptor>) = emptyFlow<ai.koog.prompt.streaming.StreamFrame>()
            override suspend fun moderate(prompt: Prompt, model: LLModel) = ModerationResult(false, emptyMap())
            override fun close() {}
        }
        val r = agentFor(executor = looping, maxIterations = 6).ask("s", "loop")
        assertTrue(r.text.startsWith("stopped:"), r.text)
        assertTrue(r.trace.size in 1..6, "${r.trace.size} tool calls")
    }
}
