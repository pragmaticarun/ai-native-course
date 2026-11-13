package course.fieldnotes

import ai.koog.prompt.executor.clients.litert.LiteRTClientConfig
import ai.koog.prompt.executor.clients.litert.LiteRTLLMClient
import ai.koog.prompt.executor.clients.litert.LiteRTLLModels
import ai.koog.prompt.executor.llms.MultiLLMPromptExecutor
import ai.koog.prompt.executor.model.PromptExecutor
import ai.koog.prompt.llm.LLModel
import com.google.ai.edge.litertlm.Backend
import java.io.File

/**
 * Android backends. The tool-routing model runs on-device through Koog's LiteRT client (preview,
 * 1.3.0-beta) on the CPU. GPU is an option that stays off until it passes the on-device test on the
 * Galaxy A73; nothing here has been run on a device yet.
 */
object OnDevice {
    /** FunctionGemma 270M (mobile actions) for routing, per the A73 model ladder. */
    val ROUTER_MODEL: LLModel = LiteRTLLModels.FunctionGemma

    /** Gemma 4 E2B for longer answers (not wired into the agent yet). */
    val ANSWER_MODEL: LLModel = LiteRTLLModels.Gemma4E2B

    fun modelFile(modelsDir: File, model: LLModel = ROUTER_MODEL) = File(modelsDir, model.id)

    fun liteRtExecutor(modelsDir: File, model: LLModel = ROUTER_MODEL, gpu: Boolean = false): PromptExecutor =
        MultiLLMPromptExecutor(
            LiteRTLLMClient(
                LiteRTClientConfig(
                    defaultModel = model,
                    modelsPath = modelsDir.absolutePath,
                    backend = if (gpu) Backend.GPU() else Backend.CPU(),
                ),
            ),
        )
}

/** Stores JSON in a file (the app passes files in filesDir), written atomically via a temp file. */
class FilePersist(private val file: File) : Persist {
    override fun read(): String? = if (file.exists()) file.readText() else null
    override fun write(text: String) {
        val tmp = File(file.parentFile, file.name + ".tmp")
        tmp.writeText(text)
        if (!tmp.renameTo(file)) { file.writeText(text); tmp.delete() }
    }
}
