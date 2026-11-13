package course.fieldnotes

import kotlinx.serialization.Serializable
import kotlinx.serialization.builtins.MapSerializer
import kotlinx.serialization.builtins.serializer

@Serializable
data class Turn(val role: String, val text: String)

/** A consequential tool call waiting for the user. Persisted so it survives process death. */
@Serializable
data class PendingAction(val tool: String, val argsJson: String, val summary: String)

@Serializable
data class Session(
    val id: String,
    val turns: List<Turn> = emptyList(),
    val trace: List<String> = emptyList(),
    val pending: PendingAction? = null,
)

/** Sessions keyed by id, stored as one JSON document through [Persist]. */
class SessionStore(private val persist: Persist = MemoryPersist()) {
    private val ser = MapSerializer(String.serializer(), Session.serializer())

    private fun readAll(): Map<String, Session> =
        persist.read()?.let { NoteStore.json.decodeFromString(ser, it) } ?: emptyMap()

    fun load(id: String): Session = readAll()[id] ?: Session(id)

    fun save(session: Session) {
        persist.write(NoteStore.json.encodeToString(ser, readAll() + (session.id to session)))
    }
}

/** Human-in-the-loop hook. The app shows a dialog; tests script the answer. */
fun interface ApprovalGate {
    suspend fun approve(action: PendingAction): Boolean
}

enum class Route { LOCAL, CLOUD }

data class RouteDecision(val route: Route, val reason: String)

/** Router inputs the user controls in settings, plus connectivity. */
data class RouterSettings(
    val cloudAllowed: Boolean = false,
    val online: Boolean = false,
    /** Characters of note text above which a summary counts as "long". */
    val longChars: Int = 600,
)

data class Reply(val text: String, val trace: List<String>, val routes: List<RouteDecision>)

/** Counts calls so tests can prove the cloud was (or was not) used. */
class CountingSummariser(private val inner: Summariser) : Summariser {
    var calls = 0
        private set

    override suspend fun summarise(text: String): String {
        calls++
        return inner.summarise(text)
    }
}
