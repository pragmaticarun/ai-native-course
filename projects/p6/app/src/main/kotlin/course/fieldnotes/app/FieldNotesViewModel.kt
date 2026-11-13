package course.fieldnotes.app

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import course.fieldnotes.ApprovalGate
import course.fieldnotes.FakeLocalModel
import course.fieldnotes.FieldNotesAgent
import course.fieldnotes.FilePersist
import course.fieldnotes.NoteStore
import course.fieldnotes.OnDevice
import course.fieldnotes.PendingAction
import course.fieldnotes.PrivacyRouter
import course.fieldnotes.SessionStore
import course.fieldnotes.Turn
import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch
import java.io.File

/**
 * Holds the agent across configuration changes (ViewModel) and process death (notes and sessions
 * are files in filesDir). With no model file on the device it falls back to the fake router and
 * says so in [backend].
 */
class FieldNotesViewModel(app: Application) : AndroidViewModel(app) {
    private val dir = app.filesDir
    private val modelsDir = File(dir, "models")
    private val sessionId = "main"

    val backend: String
    private var answer: CompletableDeferred<Boolean>? = null
    private val _pending = MutableStateFlow<PendingAction?>(null)
    val pending: StateFlow<PendingAction?> = _pending
    private val _turns = MutableStateFlow<List<Turn>>(emptyList())
    val turns: StateFlow<List<Turn>> = _turns
    private val _busy = MutableStateFlow(false)
    val busy: StateFlow<Boolean> = _busy

    private val gate = ApprovalGate { action ->
        val d = CompletableDeferred<Boolean>()
        answer = d
        _pending.value = action
        try { d.await() } finally { _pending.value = null }
    }

    private val agent: FieldNotesAgent

    init {
        val hasModel = OnDevice.modelFile(modelsDir).exists()
        backend = if (hasModel) "LiteRT-LM CPU · ${OnDevice.ROUTER_MODEL.id}" else "demo: fake router (no model file in ${modelsDir.path})"
        val executor = if (hasModel) OnDevice.liteRtExecutor(modelsDir) else FakeLocalModel()
        val model = if (hasModel) OnDevice.ROUTER_MODEL else FakeLocalModel.MODEL
        agent = FieldNotesAgent(
            executor, model,
            NoteStore.sample(FilePersist(File(dir, "notes.json"))),
            gate,
            SessionStore(FilePersist(File(dir, "sessions.json"))),
            PrivacyRouter(), // cloud not configured: every summary stays on the device
        )
        _turns.value = agent.session(sessionId).turns
        viewModelScope.launch { // a dialog that was open when the process died is shown again
            if (agent.resumePending(sessionId) != null) _turns.value = agent.session(sessionId).turns
        }
    }

    fun send(text: String) {
        if (text.isBlank() || _busy.value) return
        _busy.value = true
        _turns.value = _turns.value + Turn("user", text)
        viewModelScope.launch {
            try { agent.ask(sessionId, text) } finally {
                _turns.value = agent.session(sessionId).turns
                _busy.value = false
            }
        }
    }

    fun decide(ok: Boolean) { answer?.complete(ok) }
}
