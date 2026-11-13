package course.m13

import course.m5.Confirmer
import io.modelcontextprotocol.kotlin.sdk.ExperimentalMcpApi
import io.modelcontextprotocol.kotlin.sdk.client.Client
import io.modelcontextprotocol.kotlin.sdk.testing.ChannelTransport
import io.modelcontextprotocol.kotlin.sdk.types.Implementation
import io.modelcontextprotocol.kotlin.sdk.types.TextContent
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.withContext
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertIs
import kotlin.test.assertNull
import kotlin.test.assertTrue

class VoiceNotesTest {
    private fun store() = NoteStore(listOf("buy milk", "call the plumber about the leak", "milk the cow (joke)"))

    @Test
    fun searchThenAnswer() = runTest {
        val model = ScriptedLocalModel(listOf("""{"tool":"search_notes","args":{"query":"plumber"}}""", "Your note says: call the plumber."))
        val agent = VoiceNotesAgent(model, noteTools(store()), Confirmer { false })
        val r = agent.run("what did I say about the plumber?")
        assertEquals(listOf("search_notes"), r.calls)
        assertEquals("Your note says: call the plumber.", r.answer)
        assertTrue(model.seen.last().any { it.contains("#2: call the plumber") })
        agent.close()
        assertTrue(model.closed)
    }

    @Test
    fun deleteIsHitlGated() = runTest {
        val s = store()
        val script = listOf("""{"tool":"delete_note","args":{"id":"1"}}""", "OK.")
        val denied = VoiceNotesAgent(ScriptedLocalModel(script), noteTools(s), Confirmer { false }).run("delete note 1")
        assertEquals(3, s.notes.size)
        assertEquals(listOf("delete_note"), denied.calls)
        val approved = VoiceNotesAgent(ScriptedLocalModel(script), noteTools(s), Confirmer { true }).run("delete note 1")
        assertEquals(2, s.notes.size)
        assertEquals("OK.", approved.answer)
    }

    @Test
    fun unknownToolsAndTurnBudget() = runTest {
        val loop = List(10) { """{"tool":"search_notes","args":{"query":"x"}}""" }
        val r = VoiceNotesAgent(ScriptedLocalModel(loop), noteTools(store()), Confirmer { false }, maxTurns = 3).run("?")
        assertEquals(3, r.turns)
        assertTrue(r.answer.startsWith("stopped"))
        val bad = ScriptedLocalModel(listOf("""{"tool":"rm_rf","args":{}}""", "sorry"))
        val r2 = VoiceNotesAgent(bad, noteTools(store()), Confirmer { false }).run("?")
        assertTrue(bad.seen.last().last().contains("unknown tool rm_rf"))
        assertEquals("sorry", r2.answer)
    }

    @Test
    fun missingArgsAreReportedNotThrown() = runTest {
        val tools = noteTools(store()).associateBy { it.name }
        assertEquals("error: missing [text]", tools.getValue("create_note").invoke(emptyMap()))
        assertEquals("error: id must be a number", tools.getValue("delete_note").invoke(mapOf("id" to "one")))
    }

    @Test
    fun parseToolCallFormat() {
        assertIs<Turn.Call>(parseToolCall("""{"tool":"create_note","args":{"text":"hi"}}"""))
        assertNull(parseToolCall("just text"))
    }

    @Test
    fun goldenEvalsRunInCommonMain() = runTest {
        val cases = listOf(
            Golden("note: buy eggs", listOf("create_note"), "saved"),
            Golden("find milk", listOf("search_notes"), "2 notes"),
        )
        val scripts = mapOf(
            "note: buy eggs" to listOf("""{"tool":"create_note","args":{"text":"buy eggs"}}""", "Saved it."),
            "find milk" to listOf("""{"tool":"search_notes","args":{"query":"milk"}}""", "Found 2 notes."),
        )
        val fails = evaluate(cases) { ask ->
            VoiceNotesAgent(ScriptedLocalModel(scripts.getValue(ask)), noteTools(store()), Confirmer { false }).run(ask)
        }
        assertEquals(emptyList(), fails)
    }

    @Test
    fun availabilityAndRouter() {
        assertIs<UiState.Unsupported>(AvailabilityMachine().onStatus(A73_EXPECTED.getValue("genai-prompt")))
        assertEquals(UiState.Ready, AvailabilityMachine().onStatus(A73_EXPECTED.getValue("speech-recognition-basic")))
        val d = AvailabilityMachine()
        d.onStatus(FeatureStatus.DOWNLOADING)
        d.onProgress(0.6f)
        assertEquals(UiState.Downloading(0.6f), d.onProgress(0.2f))
        assertEquals(UiState.Ready, d.onProgress(1f))
        assertEquals(Route.REFUSE, routeSummary("email me at a@b.com", online = true, localFits = false, userAllowsCloud = true))
        assertEquals(Route.CLOUD, routeSummary("long meeting notes", online = true, localFits = false, userAllowsCloud = true))
        assertEquals(Route.REFUSE, routeSummary("long meeting notes", online = true, localFits = false, userAllowsCloud = false))
    }

    @OptIn(ExperimentalMcpApi::class)
    @Test
    fun sameToolsOverMcp() = runTest {
        withContext(Dispatchers.Default) {
            val s = store()
            val server = voiceNotesMcpServer(noteTools(s), Confirmer { false })
            val (ct, st) = ChannelTransport.createLinkedPair()
            server.createSession(st)
            val client = Client(clientInfo = Implementation("test", "1.0.0"))
            client.connect(ct)
            val tools = client.listTools().tools
            assertEquals(listOf("search_notes", "create_note", "delete_note"), tools.map { it.name })
            assertEquals(true, tools.last().annotations?.destructiveHint)
            val found = client.callTool("search_notes", mapOf("query" to "milk"))
            assertTrue((found.content.first() as TextContent).text.contains("#1: buy milk"))
            val del = client.callTool("delete_note", mapOf("id" to "1"))
            assertEquals(true, del.isError) // denied by the confirmer
            assertEquals(3, s.notes.size)
            client.close()
        }
    }
}
