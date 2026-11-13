package course.fieldnotes

/**
 * Golden prompts with the expected tool trajectory and a state check, run against a fresh
 * [NoteStore.sample]. The same list is used by the JVM suite (fake model) and the on-device
 * instrumentation suite (LiteRT model).
 */
data class Golden(
    val id: String,
    val prompt: String,
    /** Expected calls as "tool k=v k=v", keys sorted. Empty = no tool should run. */
    val expected: List<String>,
    val approve: Boolean = true,
    val check: (NoteStore) -> Boolean = { true },
)

val GOLDEN: List<Golden> = listOf(
    Golden("g01", "Find my notes about kotlin", listOf("search_notes query=kotlin")),
    Golden("g02", "search for gradle", listOf("search_notes query=gradle")),
    Golden("g03", "What did I write about Hampi?", listOf("search_notes query=hampi")),
    Golden("g04", "Create a note: buy milk and eggs", listOf("create_note body=buy milk and eggs title=buy milk and eggs"),
        check = { s -> s.search("milk").size == 1 }),
    Golden("g05", "Jot down: call Ravi about the demo", listOf("create_note body=call Ravi about the demo title=call Ravi about the"),
        check = { s -> s.search("ravi demo").size == 1 }),
    Golden("g06", "Tag note 3 as holiday", listOf("tag_note id=3 tag=holiday"), check = { s -> "holiday" in s.get(3)?.tags.orEmpty() }),
    Golden("g07", "Label note 1 with study", listOf("tag_note id=1 tag=study"), check = { s -> "study" in s.get(1)?.tags.orEmpty() }),
    Golden("g08", "Summarise my kotlin notes", listOf("summarise_notes query=kotlin")),
    Golden("g09", "Give me a summary of notes about travel", listOf("summarise_notes query=travel")),
    Golden("g10", "Delete note 4", listOf("delete_note id=4"), approve = true, check = { s -> s.get(4) == null }),
    Golden("g11", "Delete note 3", listOf("delete_note id=3"), approve = false, check = { s -> s.get(3) != null }),
    Golden("g12", "Remove note 5", listOf("delete_note id=5"), approve = true, check = { s -> s.get(5) == null }),
    Golden("g13", "Share note 3 with asha@example.com", listOf("share_note id=3 to=asha@example.com"),
        check = { s -> s.outbox == listOf(Share(3, "asha@example.com")) }),
    Golden("g14", "Send note 1 to ravi", listOf("share_note id=1 to=ravi"), approve = false, check = { s -> s.outbox.isEmpty() }),
    Golden("g15", "Create a note: renew passport then tag it as todo",
        listOf("create_note body=renew passport title=renew passport", "tag_note id=6 tag=todo"),
        check = { s -> "todo" in s.get(6)?.tags.orEmpty() }),
    Golden("g16", "Find notes about gradle then share note 5 with team@example.com",
        listOf("search_notes query=gradle", "share_note id=5 to=team@example.com"),
        check = { s -> s.outbox.size == 1 }),
    Golden("g17", "Hello", emptyList()),
    Golden("g18", "What can you do?", emptyList()),
    Golden("g19", "Find notes about quantum", listOf("search_notes query=quantum")),
    Golden("g20", "Summarise everything", listOf("summarise_notes query=")),
)
