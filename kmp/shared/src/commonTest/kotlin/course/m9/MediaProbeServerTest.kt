package course.m9

import io.modelcontextprotocol.kotlin.sdk.ExperimentalMcpApi
import io.modelcontextprotocol.kotlin.sdk.client.Client
import io.modelcontextprotocol.kotlin.sdk.testing.ChannelTransport
import io.modelcontextprotocol.kotlin.sdk.types.Implementation
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlinx.coroutines.test.runTest
import kotlinx.serialization.json.double
import kotlinx.serialization.json.int
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertTrue

private const val FFPROBE = """{"streams":[
  {"codec_type":"video","codec_name":"h264","width":1080,"height":2400},
  {"codec_type":"audio","codec_name":"aac","sample_rate":"48000"}],
  "format":{"duration":"12.500000"}}"""

class MediaProbeServerTest {
    @Test
    fun summariseMatchesTheSharedContract() {
        val s = summarise("a.mp4", FFPROBE)
        assertEquals(12.5, s["duration_s"]!!.jsonPrimitive.double)
        assertEquals(48000, s["streams"]!!.jsonArray[1].jsonObject["sample_rate"]!!.jsonPrimitive.int)
    }

    @Test
    fun rejectsPathEscapes() {
        assertFalse(isSafeRelative("../etc/passwd"))
        assertFalse(isSafeRelative("/etc/passwd"))
        assertTrue(isSafeRelative("clips/a.mp4"))
    }

    @OptIn(ExperimentalMcpApi::class)
    @Test
    fun clientCallsProbeOverChannelTransport() = runTest {
        // Real dispatcher: the SDK's request timeouts must not run on runTest's virtual clock.
        withContext(Dispatchers.Default) { roundTrip() }
    }

    @OptIn(ExperimentalMcpApi::class)
    private suspend fun roundTrip() {
        val probed = mutableListOf<String>()
        val server = mediaProbeServer { path -> probed += path; FFPROBE }
        val (clientTransport, serverTransport) = ChannelTransport.createLinkedPair()
        server.createSession(serverTransport)
        val client = Client(clientInfo = Implementation("test-client", "1.0.0"))
        client.connect(clientTransport)

        val tools = client.listTools().tools
        assertEquals(listOf("probe"), tools.map { it.name })
        assertEquals(true, tools.single().annotations?.readOnlyHint)

        val ok = client.callTool("probe", mapOf("path" to "a.mp4"))
        assertEquals(12.5, ok.structuredContent!!["duration_s"]!!.jsonPrimitive.double)
        val bad = client.callTool("probe", mapOf("path" to "../secret.mp4"))
        assertEquals(true, bad.isError)
        assertEquals(listOf("a.mp4"), probed) // the escape never reached the runner
        client.close()
    }
}
