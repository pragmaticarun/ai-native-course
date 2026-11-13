package course.m13

/**
 * M13 L13.2: feature availability -> UI state, mirroring ML Kit GenAI's documented statuses
 * (UNAVAILABLE / DOWNLOADABLE / DOWNLOADING / AVAILABLE). Our own types, not the ML Kit API.
 * The A73 answers below are what the docs imply, not values read from a device (untested).
 */
enum class FeatureStatus { UNAVAILABLE, DOWNLOADABLE, DOWNLOADING, AVAILABLE }

sealed interface UiState {
    data object Checking : UiState
    data class Unsupported(val fallback: String) : UiState
    data object NeedsDownload : UiState
    data class Downloading(val progress: Float) : UiState
    data object Ready : UiState
}

class AvailabilityMachine {
    var state: UiState = UiState.Checking
        private set

    fun onStatus(s: FeatureStatus): UiState {
        state = when (s) {
            FeatureStatus.UNAVAILABLE -> UiState.Unsupported(fallback = "LiteRT-LM on CPU, or cloud with consent")
            FeatureStatus.DOWNLOADABLE -> UiState.NeedsDownload
            FeatureStatus.DOWNLOADING -> UiState.Downloading(0f)
            FeatureStatus.AVAILABLE -> UiState.Ready
        }
        return state
    }

    fun onProgress(p: Float): UiState {
        val prev = (state as? UiState.Downloading)?.progress ?: 0f
        val now = maxOf(prev, p.coerceIn(0f, 1f))
        state = if (now >= 1f) UiState.Ready else UiState.Downloading(now)
        return state
    }
}

val A73_EXPECTED: Map<String, FeatureStatus> = mapOf(
    "genai-prompt" to FeatureStatus.UNAVAILABLE,
    "speech-recognition-basic" to FeatureStatus.AVAILABLE,
)
