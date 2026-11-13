package course.fieldnotes

/**
 * Decides where a summary runs. The on-device path is the default; the cloud is used only when the
 * user allowed it, the phone is online, the text is long, and nothing private or personal is in it.
 */
class PrivacyRouter(var settings: RouterSettings = RouterSettings()) {
    val log = mutableListOf<RouteDecision>()

    fun decide(notes: List<Note>): RouteDecision {
        val text = notes.joinToString("\n") { it.body }
        val d = when {
            !settings.cloudAllowed -> RouteDecision(Route.LOCAL, "cloud not allowed")
            !settings.online -> RouteDecision(Route.LOCAL, "offline")
            notes.any { "private" in it.tags } -> RouteDecision(Route.LOCAL, "private note")
            PII.any { it.containsMatchIn(text) } -> RouteDecision(Route.LOCAL, "personal data")
            text.length < settings.longChars -> RouteDecision(Route.LOCAL, "short")
            else -> RouteDecision(Route.CLOUD, "long, allowed, nothing private")
        }
        log += d
        return d
    }

    companion object {
        val PII = listOf(
            Regex("[\\w.+-]+@[\\w-]+\\.[\\w.]+"), // email
            Regex("\\b\\d{3}[- ]?\\d{4}\\b|\\+?\\d[\\d -]{8,}\\d"), // phone-like numbers
        )
    }
}
