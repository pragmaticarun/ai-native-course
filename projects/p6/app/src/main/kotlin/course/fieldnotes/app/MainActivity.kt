package course.fieldnotes.app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent { MaterialTheme { FieldNotesScreen() } }
    }
}

@Composable
fun FieldNotesScreen(vm: FieldNotesViewModel = viewModel()) {
    val turns by vm.turns.collectAsState()
    val pending by vm.pending.collectAsState()
    val busy by vm.busy.collectAsState()
    var input by rememberSaveable { mutableStateOf("") }

    Column(Modifier.fillMaxSize().padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Text("Field Notes", style = MaterialTheme.typography.headlineSmall)
        Text(vm.backend, style = MaterialTheme.typography.labelSmall, modifier = Modifier.testTag("backend"))
        LazyColumn(Modifier.weight(1f).fillMaxWidth().testTag("turns")) {
            items(turns) { t -> Text((if (t.role == "user") "You: " else "Notes: ") + t.text, Modifier.padding(vertical = 4.dp)) }
        }
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            OutlinedTextField(input, { input = it }, Modifier.weight(1f).testTag("input"), placeholder = { Text("Ask about your notes") })
            Button(onClick = { vm.send(input); input = "" }, enabled = !busy, modifier = Modifier.testTag("send")) { Text("Send") }
        }
    }
    pending?.let { p ->
        AlertDialog(
            onDismissRequest = {},
            title = { Text("Allow this action?") },
            text = { Text(p.summary, Modifier.testTag("pending")) },
            confirmButton = { TextButton({ vm.decide(true) }, Modifier.testTag("allow")) { Text("Allow") } },
            dismissButton = { TextButton({ vm.decide(false) }, Modifier.testTag("deny")) { Text("Deny") } },
        )
    }
}
