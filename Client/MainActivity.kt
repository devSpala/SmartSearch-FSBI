package com.example.smartsearch

import android.os.Bundle
import android.util.Log
import android.widget.Button
import android.widget.EditText
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import kotlinx.coroutines.*
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody
import org.json.JSONObject
import java.io.File

class MainActivity : AppCompatActivity() {
    private val TAG = "SmartSearchClient"
    private val serverUrl = "http://10.0.2.2:5000" // emulator -> host
    private val client = OkHttpClient()
    private val ioScope = CoroutineScope(Dispatchers.IO + Job())

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        val qEdit = findViewById<EditText>(R.id.queryEdit)
        val runBtn = findViewById<Button>(R.id.runBtn)
        val outTv = findViewById<TextView>(R.id.outTv)

        runBtn.setOnClickListener {
            val q = qEdit.text.toString()
            if (q.isNotBlank()) {
                outTv.text = "Searching..."
                ioScope.launch {
                    val local = checkLocalCache(q)
                    if (local != null) {
                        withContext(Dispatchers.Main) {
                            outTv.text = "LOCAL RESULT:\n$local"
                        }
                    } else {
                        val res = remoteQuery(q)
                        if (res != null) {
                            // Save to local cache (simple)
                            saveToLocalCache(q, res)
                            withContext(Dispatchers.Main) {
                                outTv.text = "REMOTE RESULT:\n$res"
                            }
                        } else {
                            withContext(Dispatchers.Main) {
                                outTv.text = "No results"
                            }
                        }
                    }
                }
            }
        }
    }

    // Very small LRU style: keep files in app storage, simple eviction by count
    private fun cacheDirFile(): File {
        return File(filesDir, "fsbi_cache").apply { if (!exists()) mkdirs() }
    }

    private fun checkLocalCache(query: String): String? {
        val cache = cacheDirFile()
        val fname = "q_${query.hashCode()}.json"
        val f = File(cache, fname)
        if (f.exists()) {
            return f.readText()
        }
        return null
    }

    private fun saveToLocalCache(query: String, resp: String) {
        val cache = cacheDirFile()
        val files = cache.listFiles()
        val MAX_FILES = 50
        if (files != null && files.size > MAX_FILES) {
            // rudimentary eviction (oldest)
            files.sortedBy { it.lastModified() }.first().delete()
        }
        val fname = "q_${query.hashCode()}.json"
        val f = File(cache, fname)
        f.writeText(resp)
    }

    private fun remoteQuery(query: String): String? {
        try {
            val json = JSONObject().put("q", query)
            val body = RequestBody.create("application/json; charset=utf-8".toMediaTypeOrNull(), json.toString())
            val req = Request.Builder()
                .url("$serverUrl/query")
                .post(body)
                .build()
            client.newCall(req).execute().use { resp ->
                if (!resp.isSuccessful) {
                    Log.e(TAG, "Server error: ${resp.code}")
                    return null
                }
                val s = resp.body?.string()
                return s
            }
        } catch (e: Exception) {
            Log.e(TAG, "Exception remote query", e)
            return null
        }
    }
}
