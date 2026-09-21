package com.nived938.jarvisconnect

import android.content.Context
import android.content.Intent
import android.media.AudioManager
import android.net.Uri
import android.net.nsd.NsdManager
import android.net.nsd.NsdServiceInfo
import android.os.Bundle
import android.provider.Settings
import android.widget.*
import org.json.JSONObject

class MainActivity : android.app.Activity() {
    private lateinit var hostInput: EditText
    private lateinit var portInput: EditText
    private lateinit var codeInput: EditText
    private lateinit var status: TextView
    private lateinit var client: JarvisClient
    private var nsd: NsdManager? = null
    private var discoveryListener: NsdManager.DiscoveryListener? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(32, 32, 32, 32)
        }

        fun field(hint: String) = EditText(this).apply {
            this.hint = hint
            setSingleLine(true)
        }

        root.addView(TextView(this).apply {
            text = "JARVIS Connect"
            textSize = 28f
        })
        root.addView(TextView(this).apply {
            text = "Pair this phone with the JARVIS desktop companion."
            textSize = 15f
        })

        hostInput = field("JARVIS PC IP / hostname")
        portInput = field("Port (8765)")
        portInput.setText("8765")
        codeInput = field("6-digit pairing code")

        root.addView(hostInput)
        root.addView(portInput)
        root.addView(codeInput)

        val findButton = Button(this).apply { text = "Find JARVIS on LAN" }
        val connectButton = Button(this).apply { text = "Connect / Pair" }
        val accessibilityButton = Button(this).apply { text = "Enable Accessibility" }
        val forgetButton = Button(this).apply { text = "Forget pairing" }

        root.addView(findButton)
        root.addView(connectButton)

        status = TextView(this).apply {
            text = "Not connected"
            textSize = 14f
        }
        root.addView(status)

        root.addView(accessibilityButton)
        root.addView(forgetButton)

        setContentView(root)

        client = JarvisClient(
            this,
            onStatus = { message -> runOnUiThread { status.text = message } },
            onCommand = { action, payload -> handleCommand(action, payload) }
        )

        findButton.setOnClickListener { discoverJarvis() }

        connectButton.setOnClickListener {
            val host = hostInput.text.toString().trim()
            val port = portInput.text.toString().toIntOrNull() ?: 8765
            val code = codeInput.text.toString().trim()
            if (host.isBlank()) {
                status.text = "Enter the JARVIS PC address or use LAN discovery."
            } else {
                client.connect(host, port, code)
            }
        }

        accessibilityButton.setOnClickListener {
            startActivity(Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS))
        }

        forgetButton.setOnClickListener {
            client.forgetPairing()
            status.text = "Pairing forgotten."
        }
    }

    private fun discoverJarvis() {
        nsd = getSystemService(Context.NSD_SERVICE) as NsdManager
        discoveryListener = object : NsdManager.DiscoveryListener {
            override fun onDiscoveryStarted(serviceType: String) {
                status.text = "Searching for JARVIS…"
            }

            override fun onServiceFound(serviceInfo: NsdServiceInfo) {
                nsd?.resolveService(serviceInfo, object : NsdManager.ResolveListener {
                    override fun onResolveFailed(info: NsdServiceInfo, errorCode: Int) = Unit

                    override fun onServiceResolved(info: NsdServiceInfo) {
                        val address = info.host?.hostAddress ?: return
                        runOnUiThread {
                            hostInput.setText(address)
                            portInput.setText(info.port.toString())
                            status.text = "Found JARVIS at " + address + ":" + info.port
                        }
                    }
                })
            }

            override fun onServiceLost(serviceInfo: NsdServiceInfo) = Unit
            override fun onDiscoveryStopped(serviceType: String) = Unit

            override fun onStartDiscoveryFailed(serviceType: String, errorCode: Int) {
                runOnUiThread {
                    status.text = "JARVIS discovery failed: " + errorCode
                }
            }

            override fun onStopDiscoveryFailed(serviceType: String, errorCode: Int) = Unit
        }

        try {
            nsd?.discoverServices(
                "_jarvis._tcp",
                NsdManager.PROTOCOL_DNS_SD,
                discoveryListener
            )
        } catch (e: Exception) {
            status.text = "Discovery unavailable: " + (e.message ?: "unknown error")
        }
    }

    private fun handleCommand(action: String, payload: JSONObject): JSONObject {
        return try {
            when (action) {
                "device_info" -> JSONObject()
                    .put("ok", true)
                    .put(
                        "result",
                        android.os.Build.MANUFACTURER + " " +
                            android.os.Build.MODEL + " / Android " +
                            android.os.Build.VERSION.RELEASE
                    )

                "open_url" -> {
                    val url = payload.optString("url")
                    startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)))
                    JSONObject().put("ok", true).put("result", "Opened " + url)
                }

                "open_app" -> {
                    val pkg = payload.optString("package")
                    val intent = packageManager.getLaunchIntentForPackage(pkg)
                        ?: return JSONObject().put("ok", false)
                            .put("result", "App " + pkg + " is not installed.")
                    startActivity(intent)
                    JSONObject().put("ok", true).put("result", "Opened " + pkg)
                }

                "back" -> {
                    val service = BrahmaAccessibilityService.instance
                    val ok = service?.performGlobalAction(
                        android.accessibilityservice.AccessibilityService.GLOBAL_ACTION_BACK
                    ) ?: false
                    JSONObject().put("ok", ok).put("result", "Back action requested.")
                }

                "home" -> {
                    val service = BrahmaAccessibilityService.instance
                    val ok = service?.performGlobalAction(
                        android.accessibilityservice.AccessibilityService.GLOBAL_ACTION_HOME
                    ) ?: false
                    JSONObject().put("ok", ok).put("result", "Home action requested.")
                }

                "tap" -> {
                    val service = BrahmaAccessibilityService.instance
                        ?: return JSONObject().put("ok", false)
                            .put("result", "Enable JARVIS Connect accessibility service first.")
                    val ok = service.tap(
                        payload.optDouble("x").toFloat(),
                        payload.optDouble("y").toFloat()
                    )
                    JSONObject().put("ok", ok).put("result", "Tap requested.")
                }

                "tap_text" -> {
                    val service = BrahmaAccessibilityService.instance
                        ?: return JSONObject().put("ok", false)
                            .put("result", "Enable accessibility service first.")
                    val ok = service.tapText(payload.optString("text"))
                    JSONObject().put("ok", ok)
                        .put("result", if (ok) "Tapped text." else "Text not found.")
                }

                "swipe" -> {
                    val service = BrahmaAccessibilityService.instance
                        ?: return JSONObject().put("ok", false)
                            .put("result", "Enable accessibility service first.")
                    val ok = service.swipe(
                        payload.optDouble("x1").toFloat(),
                        payload.optDouble("y1").toFloat(),
                        payload.optDouble("x2").toFloat(),
                        payload.optDouble("y2").toFloat(),
                        payload.optLong("duration_ms", 350L)
                    )
                    JSONObject().put("ok", ok).put("result", "Swipe requested.")
                }

                "type" -> {
                    val service = BrahmaAccessibilityService.instance
                        ?: return JSONObject().put("ok", false)
                            .put("result", "Enable accessibility service first.")
                    val ok = service.type(payload.optString("text"))
                    JSONObject().put("ok", ok)
                        .put("result", if (ok) "Typed." else "Could not type.")
                }

                "volume_up", "volume_down" -> {
                    val audio = getSystemService(Context.AUDIO_SERVICE) as AudioManager
                    audio.adjustVolume(
                        if (action == "volume_up") AudioManager.ADJUST_RAISE else AudioManager.ADJUST_LOWER,
                        AudioManager.FLAG_SHOW_UI
                    )
                    JSONObject().put("ok", true).put("result", "Phone volume adjusted.")
                }

                else -> JSONObject().put("ok", false)
                    .put("result", "Unknown Android command: " + action)
            }
        } catch (e: Exception) {
            JSONObject().put("ok", false)
                .put("result", e.message ?: "Android command failed")
        }
    }

    override fun onDestroy() {
        client.close()
        discoveryListener?.let { nsd?.stopServiceDiscovery(it) }
        super.onDestroy()
    }
}
