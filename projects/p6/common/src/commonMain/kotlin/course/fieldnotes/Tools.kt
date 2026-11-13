package course.fieldnotes

import ai.koog.agents.core.tools.SimpleTool
import ai.koog.agents.core.tools.annotations.LLMDescription
import ai.koog.serialization.typeToken
import kotlinx.serialization.Serializable

/** Produces a short summary. Local = on-device model; cloud = behind the PrivacyRouter. */
fun interface Summariser {
    suspend fun summarise(text: String): String
}

/** Deterministic stand-in for an on-device summariser: first sentence of each note. */
object FirstSentenceSummariser : Summariser {
    override suspend fun summarise(text: String): String =
        text.split("\n").filter { it.isNotBlank() }.joinToString(" ") { it.substringBefore(". ").trimEnd('.') + "." }
}

@Serializable
data class SearchArgs(@property:LLMDescription("Words to look for") val query: String)

@Serializable
data class CreateArgs(
    @property:LLMDescription("Short title") val title: String,
    @property:LLMDescription("Note text") val body: String,
)

@Serializable
data class TagArgs(@property:LLMDescription("Note id") val id: Int, @property:LLMDescription("Tag") val tag: String)

@Serializable
data class SummariseArgs(@property:LLMDescription("Words or a tag selecting the notes; empty = all") val query: String)

@Serializable
data class IdArgs(@property:LLMDescription("Note id") val id: Int)

@Serializable
data class ShareArgs(@property:LLMDescription("Note id") val id: Int, @property:LLMDescription("Recipient") val to: String)

class SearchNotesTool(private val store: NoteStore) :
    SimpleTool<SearchArgs>(typeToken<SearchArgs>(), "search_notes", "Find notes containing all the words") {
    override suspend fun execute(args: SearchArgs): String {
        val hits = store.search(args.query)
        return if (hits.isEmpty()) "no notes match '${args.query}'"
        else hits.joinToString("\n") { "#${it.id} ${it.title}" }
    }
}

class CreateNoteTool(private val store: NoteStore) :
    SimpleTool<CreateArgs>(typeToken<CreateArgs>(), "create_note", "Create a note") {
    override suspend fun execute(args: CreateArgs): String = "created note #${store.create(args.title, args.body).id}"
}

class TagNoteTool(private val store: NoteStore) :
    SimpleTool<TagArgs>(typeToken<TagArgs>(), "tag_note", "Add a tag to a note") {
    override suspend fun execute(args: TagArgs): String =
        store.tag(args.id, args.tag)?.let { "tagged #${it.id} with ${args.tag.lowercase()}" } ?: "no note #${args.id}"
}

/** Summarises the selected notes, picking the local or cloud summariser per call via [route]. */
class SummariseNotesTool(
    private val store: NoteStore,
    private val route: suspend (List<Note>) -> Summariser,
) : SimpleTool<SummariseArgs>(typeToken<SummariseArgs>(), "summarise_notes", "Summarise notes") {
    override suspend fun execute(args: SummariseArgs): String {
        val picked = store.search(args.query)
        if (picked.isEmpty()) return "no notes to summarise"
        return route(picked).summarise(picked.joinToString("\n") { it.body })
    }
}

class DeleteNoteTool(private val store: NoteStore) :
    SimpleTool<IdArgs>(typeToken<IdArgs>(), "delete_note", "Delete a note (asks the user first)") {
    override suspend fun execute(args: IdArgs): String =
        if (store.delete(args.id)) "deleted note #${args.id}" else "no note #${args.id}"
}

class ShareNoteTool(private val store: NoteStore) :
    SimpleTool<ShareArgs>(typeToken<ShareArgs>(), "share_note", "Share a note with someone (asks the user first)") {
    override suspend fun execute(args: ShareArgs): String =
        if (store.share(args.id, args.to)) "shared note #${args.id} with ${args.to}" else "no note #${args.id}"
}
