package course.fieldnotes.app

import androidx.compose.ui.test.hasText
import androidx.compose.ui.test.junit4.v2.createAndroidComposeRule
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performTextInput
import androidx.test.ext.junit.runners.AndroidJUnit4
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

/** Device-only. Compiled in CI (assembleDebugAndroidTest); not yet run on a device or emulator. */
@RunWith(AndroidJUnit4::class)
class FieldNotesUiTest {
    @get:Rule
    val rule = createAndroidComposeRule<MainActivity>()

    @Test
    fun searchShowsMatchingNote() {
        rule.onNodeWithTag("input").performTextInput("Find my notes about kotlin")
        rule.onNodeWithTag("send").performClick()
        rule.waitUntil(10_000) { rule.onAllNodes(hasText("Kotlin coroutines", substring = true)).fetchSemanticsNodes().isNotEmpty() }
    }

    @Test
    fun deleteAsksAndDenyKeepsTheNote() {
        rule.onNodeWithTag("input").performTextInput("Delete note 3")
        rule.onNodeWithTag("send").performClick()
        rule.waitUntil(10_000) { rule.onAllNodes(hasText("delete_note id=3")).fetchSemanticsNodes().isNotEmpty() }
        rule.onNodeWithTag("deny").performClick()
        rule.waitUntil(10_000) { rule.onAllNodes(hasText("declined", substring = true)).fetchSemanticsNodes().isNotEmpty() }
    }
}
