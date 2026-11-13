package course.m5

/**
 * M5 on-device HITL, in KMP commonMain. A destructive tool (think: an AppFunction such as
 * `delete_recording`) is wrapped in a decorator that asks the user before it runs.
 *
 * ML Kit's preview `genai-agent` docs describe a decorator for this on `AgentTool`. This file
 * mirrors the idea with our own small types so it compiles and runs on the JVM in CI; it is
 * NOT the ML Kit API and has not been run against it or on a device.
 */
interface AgentTool {
    val name: String
    val destructive: Boolean get() = false
    suspend fun invoke(args: Map<String, String>): String
}

/** The UI side: on Android this would show a dialog; tests answer from a script. */
fun interface Confirmer {
    suspend fun confirm(prompt: String): Boolean
}

class RequiresConfirmation(private val inner: AgentTool, private val confirmer: Confirmer) : AgentTool by inner {
    val asked = mutableListOf<String>()

    override suspend fun invoke(args: Map<String, String>): String {
        val prompt = "Allow ${inner.name}(${args.entries.joinToString { "${it.key}=${it.value}" }})?"
        asked += prompt
        return if (confirmer.confirm(prompt)) inner.invoke(args) else "denied by user: ${inner.name} was not run"
    }
}

/** Wrap every destructive tool; leave read-only tools alone. */
fun guardDestructive(tools: List<AgentTool>, confirmer: Confirmer): List<AgentTool> =
    tools.map { if (it.destructive) RequiresConfirmation(it, confirmer) else it }

class Recordings(initial: List<String>) {
    val names = initial.toMutableList()

    val list = object : AgentTool {
        override val name = "list_recordings"
        override suspend fun invoke(args: Map<String, String>) = names.joinToString()
    }

    val delete = object : AgentTool {
        override val name = "delete_recording"
        override val destructive = true
        override suspend fun invoke(args: Map<String, String>): String {
            val n = args.getValue("name")
            return if (names.remove(n)) "deleted $n" else "error: no recording named $n"
        }
    }
}
