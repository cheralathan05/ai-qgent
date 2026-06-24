package com.apaos.agent.services

import android.app.Notification
import android.app.PendingIntent
import android.app.Service
import android.content.Intent
import android.os.Build
import android.os.IBinder
import android.os.PowerManager
import android.util.Log
import com.apaos.agent.MainActivity
import com.apaos.agent.R
import com.apaos.agent.core.DeviceCollector
import com.apaos.agent.network.ApiClient
import com.apaos.agent.network.WebSocketClient
import kotlinx.coroutines.*

class APAForegroundService : Service() {

    companion object {
        private const val TAG = "APAForegroundService"
        private const val NOTIFICATION_ID = 1001
        private const val HEARTBEAT_INTERVAL = 30000L // 30 seconds

        var instance: APAForegroundService? = null
            private set
        var isRunning = false
            private set
    }

    private var wakeLock: PowerManager.WakeLock? = null
    private val scope = CoroutineScope(Dispatchers.IO + SupervisorJob())
    private var heartbeatJob: Job? = null

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onCreate() {
        super.onCreate()
        instance = this
        isRunning = true
        acquireWakeLock()
        Log.d(TAG, "APA Foreground Service created")
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            "START" -> {
                startForeground(NOTIFICATION_ID, createNotification("APA Agent Active", "Connected and ready"))
                startHeartbeat()
                connectWebSocket()
            }
            "STOP" -> {
                stopSelf()
            }
            "UPDATE" -> {
                val title = intent.getStringExtra("title") ?: "APA Agent"
                val message = intent.getStringExtra("message") ?: "Running"
                updateNotification(title, message)
            }
        }
        return START_STICKY
    }

    private fun startHeartbeat() {
        heartbeatJob?.cancel()
        heartbeatJob = scope.launch {
            while (isActive) {
                try {
                    val collector = DeviceCollector(this@APAForegroundService)
                    val battery = collector.getBatteryLevel()
                    val foregroundApp = collector.getForegroundApp()

                    WebSocketClient.getInstance().sendHeartbeat(battery, foregroundApp)

                    // Also send to API
                    ApiClient.getInstance().sendHeartbeat(
                        com.apaos.agent.network.DeviceHeartbeat(
                            deviceId = ApiClient.getInstance().getDeviceId(),
                            batteryLevel = battery,
                            foregroundApp = foregroundApp,
                            screenState = if (collector.isScreenOn()) "on" else "off",
                            lockState = if (collector.isDeviceLocked()) "locked" else "unlocked",
                            networkType = collector.getNetworkType(),
                            networkStrength = collector.getNetworkStrength()
                        )
                    ) { /* heartbeat sent */ }

                } catch (e: Exception) {
                    Log.e(TAG, "Heartbeat failed", e)
                }
                delay(HEARTBEAT_INTERVAL)
            }
        }
    }

    private fun connectWebSocket() {
        val deviceId = ApiClient.getInstance().getDeviceId()
        if (deviceId.isNotEmpty()) {
            WebSocketClient.getInstance().connect(deviceId)
        }
    }

    private fun createNotification(title: String, message: String): Notification {
        val pendingIntent = PendingIntent.getActivity(
            this, 0,
            Intent(this, MainActivity::class.java),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        val builder = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            Notification.Builder(this, "apa_service")
        } else {
            @Suppress("DEPRECATION")
            Notification.Builder(this)
        }

        return builder
            .setContentTitle(title)
            .setContentText(message)
            .setSmallIcon(R.drawable.ic_notification)
            .setContentIntent(pendingIntent)
            .setOngoing(true)
            .build()
    }

    fun updateNotification(title: String, message: String) {
        val notification = createNotification(title, message)
        val manager = getSystemService(NOTIFICATION_SERVICE) as android.app.NotificationManager
        manager.notify(NOTIFICATION_ID, notification)
    }

    private fun acquireWakeLock() {
        val powerManager = getSystemService(POWER_SERVICE) as PowerManager
        wakeLock = powerManager.newWakeLock(
            PowerManager.PARTIAL_WAKE_LOCK,
            "APA::AgentWakeLock"
        ).apply {
            acquire(10 * 60 * 1000L) // 10 minutes
        }
    }

    override fun onDestroy() {
        heartbeatJob?.cancel()
        scope.cancel()
        wakeLock?.let { if (it.isHeld) it.release() }
        WebSocketClient.getInstance().disconnect()
        instance = null
        isRunning = false
        super.onDestroy()
        Log.d(TAG, "APA Foreground Service destroyed")
    }
}
