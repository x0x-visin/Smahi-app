package com.example.samahi

import android.net.Uri
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import okhttp3.*
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.RequestBody.Companion.toRequestBody
import java.io.IOException

class MainActivity : ComponentActivity() {
    private val client = OkHttpClient()
    private var uri by mutableStateOf<Uri?>(null)
    private var status by mutableStateOf("Pick an image")
    private val pick = registerForActivityResult(ActivityResultContracts.GetContent()) { uri = it; status = "Ready to send" }

    override fun onCreate(b: Bundle?) {
        super.onCreate(b)
        setContent {
            MaterialTheme {
                Column(Modifier.fillMaxSize().padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                    Text("Samahi App", style = MaterialTheme.typography.headlineSmall)
                    Button(onClick = { pick.launch("image/*") }) { Text("Choose image") }
                    Text(status)
                    Button(onClick = { uri?.let(::send) }, enabled = uri != null) { Text("Vectorize -> TTF") }
                }
            }
        }
    }

    private fun send(u: Uri) {
        status = "Uploading..."
        val bytes = contentResolver.openInputStream(u)!!.readBytes()
        val body = MultipartBody.Builder().setType(MultipartBody.FORM)
            .addFormDataPart("file", "in.png", bytes.toRequestBody("image/*".toMediaType())).build()
        val req = Request.Builder().url("http://10.0.2.2:8000/vectorize?scale=2&threshold=180&chars=A").post(body).build()
        client.newCall(req).enqueue(object : Callback {
            override fun onFailure(c: Call, e: IOException) { status = "Failed: ${e.message}" }
            override fun onResponse(c: Call, r: Response) {
                r.body?.bytes()?.let { openFileOutput("vectorfont.ttf", MODE_PRIVATE).write(it) }
                status = if (r.isSuccessful) "Saved vectorfont.ttf" else "Error ${r.code}"
            }
        })
    }
}
