package course.p3

import io.modelcontextprotocol.kotlin.sdk.ExperimentalMcpApi
import io.modelcontextprotocol.kotlin.sdk.client.Client
import io.modelcontextprotocol.kotlin.sdk.testing.ChannelTransport
import io.modelcontextprotocol.kotlin.sdk.types.Implementation
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.withContext
import kotlinx.serialization.json.double
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonPrimitive
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertTrue

class AdbMediaServerTest {
    @Test
    fun intentsBecomeFixedSteps() {
        assertEquals(
            listOf(Step.Trim(0.0, 5.0), Step.RemoveAudio, Step.Resize(720)),
            planTransform("Trim to 5 s, mute it and make it 720p").getOrThrow(),
        )
        assertEquals(listOf(Step.Trim(2.0, 4.5)), planTransform("keep from 2 to 4.5 s").getOrThrow())
        assertTrue(planTransform("make it look cinematic").isFailure)
        assertTrue(planTransform("trim 5 to 2 s").isFailure)
        assertTrue(planTransform("make it 333p").isFailure)
    }

    @Test
    fun devicePathsStayUnderSdcard() {
        assertTrue(isSafeDevicePath("/sdcard/p3_rec_1.mp4"))
        assertFalse(isSafeDevicePath("/data/data/app/db"))
        assertFalse(isSafeDevicePath("/sdcard/../data/x"))
        assertFalse(isSafeDevicePath("/sdcard/a.mp4; rm -rf /"))
    }

    @OptIn(ExperimentalMcpApi::class)
    @Test
    fun agentDrivesTheFakeDeviceOverMcp() = runTest {
        withContext(Dispatchers.Default) { roundTrip() }
    }

    @OptIn(ExperimentalMcpApi::class)
    private suspend fun roundTrip() {
        val adbCalls = mutableListOf<List<String>>()
        val transforms = mutableListOf<Pair<String, List<Step>>>()
        val answers = ArrayDeque(listOf(false, true, false))
        val asked = mutableListOf<String>()
        val server = adbMediaServer(
            adb = { args -> adbCalls += args; AdbResult(0) },
            transformer = { input, steps, _ -> transforms += input to steps; 5.0 },
            confirmer = { prompt -> asked += prompt; answers.removeFirst() },
        )
        val (clientTransport, serverTransport) = ChannelTransport.createLinkedPair()
        server.createSession(serverTransport)
        val client = Client(clientInfo = Implementation("p3-agent", "1.0.0"))
        client.connect(clientTransport)

        assertEquals(setOf("screenrecord", "pull", "transform"), client.listTools().tools.map { it.name }.toSet())

        // Denied: adb never runs. Then allowed.
        assertEquals(true, client.callTool("screenrecord", mapOf("seconds" to 5)).isError)
        assertTrue(adbCalls.isEmpty())
        val rec = client.callTool("screenrecord", mapOf("seconds" to 5))
        val devicePath = rec.structuredContent!!["device_path"]!!.jsonPrimitive.content
        assertEquals(listOf("shell", "screenrecord", "--time-limit", "5", devicePath), adbCalls.single())
        assertEquals(true, client.callTool("screenrecord", mapOf("seconds" to 999)).isError)

        assertEquals(true, client.callTool("pull", mapOf("device_path" to "/sdcard/x.mp4", "name" to "../x.mp4")).isError)
        assertTrue(client.callTool("pull", mapOf("device_path" to devicePath, "name" to "rec.mp4")).isError != true)
        assertEquals(listOf("pull", devicePath, "media/rec.mp4"), adbCalls.last())

        val t = client.callTool("transform", mapOf("path" to "rec.mp4", "intent" to "first 5 s, no audio", "out" to "clip.mp4"))
        assertEquals(5.0, t.structuredContent!!["duration_s"]!!.jsonPrimitive.double)
        assertEquals(2, t.structuredContent!!["steps"]!!.jsonArray.size)
        // Overwriting the source asks; the user says no and nothing runs.
        val same = client.callTool("transform", mapOf("path" to "rec.mp4", "intent" to "mute", "out" to "rec.mp4"))
        assertEquals(true, same.isError)
        assertEquals(1, transforms.size)
        assertEquals(3, asked.size)
        client.close()
    }
}
