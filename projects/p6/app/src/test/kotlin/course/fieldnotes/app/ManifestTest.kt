package course.fieldnotes.app

import java.io.File
import kotlin.test.Test
import kotlin.test.assertFalse

/** Local unit test: the app must not ask for network access (privacy checklist item 1). */
class ManifestTest {
    @Test
    fun noInternetPermission() {
        val manifest = File("src/main/AndroidManifest.xml").readText()
        assertFalse("android.permission.INTERNET" in manifest.replace(Regex("<!--.*?-->", RegexOption.DOT_MATCHES_ALL), ""))
    }
}
