package course.fieldnotes.app

import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import course.fieldnotes.ApprovalGate
import course.fieldnotes.FieldNotesAgent
import course.fieldnotes.GOLDEN
import course.fieldnotes.NoteStore
import course.fieldnotes.OnDevice
import course.fieldnotes.PrivacyRouter
import course.fieldnotes.SessionStore
import kotlinx.coroutines.runBlocking
import org.junit.Assume.assumeTrue
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File
import kotlin.time.measureTimedValue

/**
 * The golden-prompt and tool-trajectory suite against the real LiteRT-LM model on the Galaxy A73.
 * Push the model first: adb push mobile_actions_q8_ekv1024.litertlm /data/local/tmp/llm/
 * Device-only: compiled in CI, NOT yet run on a device. Results go to logcat, not a gate.
 */
@RunWith(AndroidJUnit4::class)
class GoldenOnDeviceTest {
    private val modelsDir = File("/data/local/tmp/llm")

    @Test
    fun goldenTrajectoriesOnLiteRt() = runBlocking {
        assumeTrue("model file missing", OnDevice.modelFile(modelsDir).exists())
        val executor = OnDevice.liteRtExecutor(modelsDir)
        var ok = 0
        for (g in GOLDEN) {
            val store = NoteStore.sample()
            val agent = FieldNotesAgent(executor, OnDevice.ROUTER_MODEL, store, ApprovalGate { g.approve }, SessionStore(), PrivacyRouter())
            val (reply, took) = measureTimedValue { agent.ask(g.id, g.prompt) }
            val pass = reply.trace == g.expected && g.check(store)
            if (pass) ok++
            android.util.Log.i("P6Golden", "${g.id} pass=$pass ms=${took.inWholeMilliseconds} trace=${reply.trace}")
        }
        android.util.Log.i("P6Golden", "trajectory+state pass rate ${ok}/${GOLDEN.size}")
    }

    @Test
    fun onDevicePathMakesNoNetworkCalls() = runBlocking {
        // Run with the device in airplane mode: the local path must still answer.
        assumeTrue("model file missing", OnDevice.modelFile(modelsDir).exists())
        val ctx = InstrumentationRegistry.getInstrumentation().targetContext
        val cm = ctx.getSystemService(android.net.ConnectivityManager::class.java)
        assumeTrue("turn networking off first", cm.activeNetwork == null)
        val agent = FieldNotesAgent(OnDevice.liteRtExecutor(modelsDir), OnDevice.ROUTER_MODEL, NoteStore.sample(), ApprovalGate { false }, SessionStore(), PrivacyRouter())
        val reply = agent.ask("offline", "Summarise everything")
        check(reply.routes.all { it.route == course.fieldnotes.Route.LOCAL })
    }
}
