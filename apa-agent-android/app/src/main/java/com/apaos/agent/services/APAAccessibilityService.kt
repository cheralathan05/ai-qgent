package com.apaos.agent.services

import android.accessibilityservice.AccessibilityService
import android.accessibilityservice.AccessibilityServiceInfo
import android.content.Intent
import android.util.Log
import android.view.accessibility.AccessibilityEvent
import com.apaos.agent.network.WebSocketClient

class APAAccessibilityService : AccessibilityService() {

    companion object {
        private const val TAG = "APAAccessibility"
        var instance: APAAccessibilityService? = null
            private set
        var isRunning = false
            private set
    }

    override fun onServiceConnected() {
        super.onServiceConnected()
        instance = this
        isRunning = true

        serviceInfo = serviceInfo.apply {
            eventTypes = AccessibilityEvent.TYPES_ALL_MASK
            feedbackType = AccessibilityServiceInfo.FEEDBACK_GENERIC
            flags = AccessibilityServiceInfo.FLAG_INCLUDE_NOT_IMPORTANT_VIEWS or
                    AccessibilityServiceInfo.FLAG_REPORT_VIEW_IDS or
                    AccessibilityServiceInfo.FLAG_RETRIEVE_INTERACTIVE_WINDOWS
            notificationTimeout = 100
        }

        Log.d(TAG, "APA Accessibility Service connected")
    }

    override fun onAccessibilityEvent(event: AccessibilityEvent?) {
        if (!isRunning) return

        event?.let {
            val packageName = it.packageName?.toString() ?: "unknown"
            val eventType = it.eventType

            // Forward events to WebSocket for AI processing
            when (eventType) {
                AccessibilityEvent.TYPE_VIEW_CLICKED -> {
                    val source = it.source
                    val text = source?.contentDescription?.toString() ?: ""
                    Log.d(TAG, "Click detected: $text in $packageName")
                }
                AccessibilityEvent.TYPE_WINDOW_STATE_CHANGED -> {
                    Log.d(TAG, "Window changed: $packageName")
                }
                AccessibilityEvent.TYPE_VIEW_TEXT_CHANGED -> {
                    Log.d(TAG, "Text changed in $packageName")
                }
            }
        }
    }

    override fun onInterrupt() {
        Log.d(TAG, "APA Accessibility Service interrupted")
    }

    override fun onDestroy() {
        instance = null
        isRunning = false
        super.onDestroy()
        Log.d(TAG, "APA Accessibility Service destroyed")
    }

    fun performAction(action: String, params: Map<String, Any> = emptyMap()): Boolean {
        return try {
            when (action) {
                "back" -> performGlobalAction(GLOBAL_ACTION_BACK)
                "home" -> performGlobalAction(GLOBAL_ACTION_HOME)
                "recents" -> performGlobalAction(GLOBAL_ACTION_RECENTS)
                "notifications" -> performGlobalAction(GLOBAL_ACTION_NOTIFICATIONS)
                "power_dialog" -> performGlobalAction(GLOBAL_ACTION_POWER_DIALOG)
                "take_screenshot" -> {
                    if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.R) {
                        performGlobalAction(GLOBAL_ACTION_TAKE_SCREENSHOT)
                    } else false
                }
                else -> false
            }
        } catch (e: Exception) {
            Log.e(TAG, "Action failed: $action", e)
            false
        }
    }

    fun getActiveWindowTitle(): String {
        val rootNode = rootInActiveWindow ?: return "unknown"
        return rootNode.packageName?.toString() ?: "unknown"
    }
}
