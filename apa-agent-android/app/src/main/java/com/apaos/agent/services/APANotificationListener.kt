package com.apaos.agent.services

import android.app.Notification
import android.content.Intent
import android.service.notification.NotificationListenerService
import android.service.notification.StatusBarNotification
import android.util.Log
import com.apaos.agent.network.WebSocketClient

class APANotificationListener : NotificationListenerService() {

    companion object {
        private const val TAG = "APANotificationListener"
        var instance: APANotificationListener? = null
            private set
        var isRunning = false
            private set
    }

    override fun onCreate() {
        super.onCreate()
        instance = this
        isRunning = true
        Log.d(TAG, "APA Notification Listener created")
    }

    override fun onNotificationPosted(sbn: StatusBarNotification?) {
        sbn?.let { notification ->
            val packageName = notification.packageName
            val title = notification.notification.extras.getString(Notification.EXTRA_TITLE) ?: ""
            val text = notification.notification.extras.getString(Notification.EXTRA_TEXT) ?: ""

            // Skip our own notifications
            if (packageName == this.packageName) return

            Log.d(TAG, "Notification from $packageName: $title - $text")

            // Send to WebSocket for AI processing
            WebSocketClient.getInstance().sendNotification(title, text, packageName)
        }
    }

    override fun onNotificationRemoved(sbn: StatusBarNotification?) {
        // Notification dismissed
    }

    override fun onDestroy() {
        instance = null
        isRunning = false
        super.onDestroy()
        Log.d(TAG, "APA Notification Listener destroyed")
    }

    fun getActiveNotifications(): List<Map<String, String>> {
        val notifications = mutableListOf<Map<String, String>>()
        try {
            activeNotifications?.forEach { sbn ->
                val title = sbn.notification.extras.getString(Notification.EXTRA_TITLE) ?: ""
                val text = sbn.notification.extras.getString(Notification.EXTRA_TEXT) ?: ""
                notifications.add(mapOf(
                    "package" to sbn.packageName,
                    "title" to title,
                    "text" to text,
                    "timestamp" to sbn.postTime.toString()
                ))
            }
        } catch (e: Exception) {
            Log.e(TAG, "Failed to get notifications", e)
        }
        return notifications
    }
}
