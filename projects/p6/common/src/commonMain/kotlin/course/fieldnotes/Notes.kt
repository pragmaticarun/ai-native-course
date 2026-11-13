package course.fieldnotes

import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json

/** A note or a transcribed voice memo. `private` notes never leave the device (see PrivacyRouter). */
@Serializable
data class Note(
    val id: Int,
    val title: String,
    val body: String,
    val tags: Set<String> = emptySet(),
    val voiceMemo: Boolean = false,
)

@Serializable
data class Share(val noteId: Int, val to: String)

/**
 * The app's data. Kept deliberately plain: a list in memory plus a [Persist] hook, so the same code
 * runs on the JVM (tests) and on Android (the app writes it to filesDir).
 */
class NoteStore(seed: List<Note> = emptyList(), private val persist: Persist? = null) {
    @Serializable
    private data class Snapshot(val notes: List<Note>, val shares: List<Share>)

    private val notes = linkedMapOf<Int, Note>()
    val outbox = mutableListOf<Share>()

    init {
        val saved = persist?.read()?.let { json.decodeFromString(Snapshot.serializer(), it) }
        (saved?.notes ?: seed).forEach { notes[it.id] = it }
        saved?.shares?.let(outbox::addAll)
    }

    fun all(): List<Note> = notes.values.toList()
    fun get(id: Int): Note? = notes[id]

    fun search(query: String): List<Note> {
        val words = query.lowercase().split(Regex("\\W+")).filter { it.length > 1 }
        if (words.isEmpty()) return all()
        return all().filter { n ->
            val hay = (n.title + " " + n.body + " " + n.tags.joinToString(" ")).lowercase()
            words.all { it in hay }
        }
    }

    fun create(title: String, body: String, tags: Set<String> = emptySet()): Note {
        val note = Note((notes.keys.maxOrNull() ?: 0) + 1, title, body, tags)
        notes[note.id] = note
        save()
        return note
    }

    fun tag(id: Int, tag: String): Note? {
        val n = notes[id] ?: return null
        return n.copy(tags = n.tags + tag.lowercase()).also { notes[id] = it; save() }
    }

    fun delete(id: Int): Boolean = (notes.remove(id) != null).also { if (it) save() }

    fun share(id: Int, to: String): Boolean {
        if (id !in notes) return false
        outbox += Share(id, to)
        save()
        return true
    }

    private fun save() {
        persist?.write(json.encodeToString(Snapshot.serializer(), Snapshot(all(), outbox.toList())))
    }

    companion object {
        val json = Json { ignoreUnknownKeys = true }

        /** Fixture data used by the evals and by the app's first launch. */
        fun sample(persist: Persist? = null) = NoteStore(
            listOf(
                Note(1, "Kotlin coroutines", "Structured concurrency: a scope owns its children.", setOf("kotlin")),
                Note(2, "Dentist", "Appointment on Tuesday at 10. Call 555-0100 to move it.", setOf("private")),
                Note(3, "Trip ideas", "Hampi in December, Coorg in the monsoon.", setOf("travel")),
                Note(4, "Standup memo", "Shipped the export screen; blocked on the API review.", setOf("work"), voiceMemo = true),
                Note(5, "Gradle tips", "Use a version catalog; keep plugin versions in one place.", setOf("kotlin", "build")),
            ),
            persist,
        )
    }
}

/** Where a store keeps its JSON. Android passes a file in filesDir; tests pass memory. */
interface Persist {
    fun read(): String?
    fun write(text: String)
}

class MemoryPersist(var text: String? = null) : Persist {
    override fun read() = text
    override fun write(text: String) { this.text = text }
}
