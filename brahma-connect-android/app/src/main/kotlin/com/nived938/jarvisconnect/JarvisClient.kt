package com.nived938.jarvisconnect

import android.content.Context
import android.os.Build
import android.provider.Settings
import okhttp3.*
import org.json.JSONObject
import java.util.concurrent.TimeUnit

class JarvisClient(
    private val context: Context,
    private val onStatus: (String) -> Unit,
    private val onCommand: (String, JSONObject) -> JSONObject
) {
    private val prefs = context.getSharedPreferences("jarvis_connect", Context.MODE_PRIVATE)
    private val client = OkHttpClient.Builder()
        .readTimeout(0, TimeUnit.MILLISECONDS)
        .build()
    private var socket: WebSocket? = null

    private fun deviceId(): String =
        Settings.Secure.getString(context.contentResolver, Settings.Secure.ANDROID_ID)
            ?: "android-${Build.MODEL}"

    private fun hello(code: String = ""): JSONObject {
        val device = JSONObject()
            .put("id", deviceId())
            .put("name", "${Build.MANUFACTURER} phone")
            .put("model", Build.MODEL)
            .put("android", Build.VERSION.RELEASE)

        val message = JSONObject()
            .put("type", "hello")
            .put("device", device)

        val token = prefs.getString("token", "") ?: ""
        if (token.isNotBlank()) {
            message.put("token", token)
        } else {
            message.put("pairing_code", code)
        }
        return message
    }

    fun connect(host: String, port: Int, code: String = "") {
        val url = if (host.startsWith("ws://") || host.startsWith("wss://"))
            host
        else
            "ws://$host:$port/ws"

        onStatus("Connecting to $url")
        socket?.cancel()
        socket = client.newWebSocket(
            Request.Builder().url(url).build(),
            object : WebSocketListener() {
                override fun onOpen(webSocket: WebSocket, response: Response) {
                    onStatus("Connected — authenticating")
                    webSocket.send(hello(code).toString())
                }

                override fun onMessage(webSocket: WebSocket, text: String) {
                    try {
                        val msg = JSONObject(text)
                        when (msg.optString("type")) {
                            "pair_approved" -> {
                                prefs.edit()
                                    .putString("token", msg.optString("token"))
                                    .putString("device_id", msg.optString("device_id"))
                                    .apply()
                                onStatus("Paired. Authenticating…")
                                webSocket.send(hello().toString())
                            }
                            "authenticated" -> onStatus(
                                "Authenticated as ${msg.optString("device_id")}"
                            )
                            "execute" -> {
                                val id = msg.optString("id")
                                val result = onCommand(
                                    msg.optString("action"),
                                    msg.optJSONObject("payload") ?: JSONObject()
                                )
                                webSocket.send(
                                    JSONObject()
                                        .put("type", "result")
                                        .put("id", id)
                                        .put("ok", result.optBoolean("ok", true))
                                        .put("result", result.optString("result"))
                                        .toString()
                                )
                            }
                            "ping" -> webSocket.send(
                                JSONObject().put("type", "pong").toString()
                            )
                            "error" -> onStatus("JARVIS error: ${msg.optString("error")}")
                        }
                    } catch (e: Exception) {
                        onStatus("Message error: ${e.message}")
                    }
                }

                override fun onFailure(webSocket: WebSocket, t: Throwable, response: Response?) {
                    onStatus("Disconnected: ${t.message}")
                }

                override fun onClosed(webSocket: WebSocket, code: Int, reason: String) {
                    onStatus("Disconnected: $reason")
                }
            }
        )
    }

    fun forgetPairing() {
        prefs.edit().clear().apply()
        socket?.close(1000, "forget")
    }

    fun close() {
        socket?.close(1000, "app closed")
        client.dispatcher.executorService.shutdown()
    }
}
