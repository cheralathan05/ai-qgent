package com.apaos.agent.network

import android.util.Log
import com.google.gson.Gson
import kotlinx.coroutines.*
import okhttp3.*
import java.util.concurrent.TimeUnit

class WebSocketClient {

    companion object {
        private const val TAG = "WebSocketClient"
        private var instance: WebSocketClient? = null

        fun getInstance(): WebSocketClient {
            return instance ?: WebSocketClient().also { instance = it }
        }
    }

    private var webSocket: WebSocket? = null
    private var isConnected = false
    private val gson = Gson()
    private val scope = CoroutineScope(Dispatchers.IO + SupervisorJob())

    var onMessageReceived: ((String, Any?) -> Unit)? = null
    var onConnectionChanged: ((Boolean) -> Unit)? = null

    private val client = OkHttpClient.Builder()
        .readTimeout(0, TimeUnit.MILLISECONDS)
        .build()

    fun connect(clientId: String) {
        val baseUrl = ApiClient.getInstance().getBaseUrl().replace("http", "ws")
        val url = "$baseUrl/ws/agent/$clientId"

        val request = Request.Builder()
            .url(url)
            .build()

        webSocket = client.newWebSocket(request, object : WebSocketListener() {
            override fun onOpen(webSocket: WebSocket, response: Response) {
                Log.d(TAG, "WebSocket connected")
                isConnected = true
                onConnectionChanged?.invoke(true)
            }

            override fun onMessage(webSocket: WebSocket, text: String) {
                Log.d(TAG, "Message received: $text")
                try {
                    val json = gson.fromJson(text, Map::class.java)
                    val event = json["event"] as? String ?: "unknown"
                    onMessageReceived?.invoke(event, json["data"])
                } catch (e: Exception) {
                    onMessageReceived?.invoke("raw", text)
                }
            }

            override fun onClosing(webSocket: WebSocket, code: Int, reason: String) {
                webSocket.close(1000, null)
                isConnected = false
                onConnectionChanged?.invoke(false)
            }

            override fun onFailure(webSocket: WebSocket, t: Throwable, response: Response?) {
                Log.e(TAG, "WebSocket failure: ${t.message}")
                isConnected = false
                onConnectionChanged?.invoke(false)
                // Auto reconnect after 5 seconds
                scope.launch {
                    delay(5000)
                    connect(clientId)
                }
            }
        })
    }

    fun sendMessage(type: String, data: Any?) {
        val message = mapOf(
            "type" to type,
            "data" to data,
            "device_id" to ApiClient.getInstance().getDeviceId(),
            "timestamp" to System.currentTimeMillis()
        )
        webSocket?.send(gson.toJson(message))
    }

    fun sendCommandResult(commandId: String, success: Boolean, result: Any?) {
        sendMessage("command_result", mapOf(
            "command_id" to commandId,
            "success" to success,
            "result" to result
        ))
    }

    fun sendHeartbeat(battery: Int, foregroundApp: String) {
        sendMessage("heartbeat", mapOf(
            "battery" to battery,
            "foreground_app" to foregroundApp,
            "timestamp" to System.currentTimeMillis()
        ))
    }

    fun sendNotification(title: String, body: String, packageName: String) {
        sendMessage("notification", mapOf(
            "title" to title,
            "body" to body,
            "package" to packageName
        ))
    }

    fun disconnect() {
        webSocket?.close(1000, "Client disconnect")
        isConnected = false
        onConnectionChanged?.invoke(false)
    }

    fun isSocketConnected(): Boolean = isConnected
}
