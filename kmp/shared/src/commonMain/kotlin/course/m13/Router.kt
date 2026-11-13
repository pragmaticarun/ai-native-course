package course.m13

/**
 * M13 L13.4: the voice-notes privacy check before anything goes to a cloud model.
 * Same rules as examples/python/m13/privacy_router.py (kept small here).
 */
enum class Route { LOCAL, CLOUD, REFUSE }

private val PII = listOf(
    Regex("""\b[\w.+-]+@[\w-]+\.[\w.]+\b"""),
    Regex("""(?<!\d)\+?\d[\d -]{8,}\d(?!\d)"""),
)

fun containsPii(text: String) = PII.any { it.containsMatchIn(text) }

fun routeSummary(text: String, online: Boolean, localFits: Boolean, userAllowsCloud: Boolean): Route = when {
    containsPii(text) -> if (localFits) Route.LOCAL else Route.REFUSE
    localFits -> Route.LOCAL
    online && userAllowsCloud -> Route.CLOUD
    else -> Route.REFUSE
}
