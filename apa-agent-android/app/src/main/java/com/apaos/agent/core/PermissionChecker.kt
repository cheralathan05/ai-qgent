package com.apaos.agent.core

import android.accessibilityservice.AccessibilityServiceInfo
import android.app.AppOpsManager
import android.content.Context
import android.content.Intent
import android.media.projection.MediaProjectionManager
import android.net.Uri
import android.os.Build
import android.provider.Settings
import android.view.accessibility.AccessibilityManager

data class PermissionState(
    val name: String,
    val granted: Boolean,
    val androidPermission: String,
    val description: String
)

class PermissionChecker(private val context: Context) {

    fun isAccessibilityEnabled(): Boolean {
        val am = context.getSystemService(Context.ACCESSIBILITY_SERVICE) as AccessibilityManager
        val enabledServices = am.getEnabledAccessibilityServiceList(AccessibilityServiceInfo.FEEDBACK_GENERIC)
        return enabledServices.any { it.resolveInfo.serviceInfo.packageName == context.packageName }
    }

    fun openAccessibilitySettings() {
        val intent = Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS).apply {
            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        }
        context.startActivity(intent)
    }

    fun isNotificationListenerEnabled(): Boolean {
        val packageName = context.packageName
        val flat = Settings.Secure.getString(context.contentResolver, "enabled_notification_listeners")
        return flat?.contains(packageName) == true
    }

    fun openNotificationListenerSettings() {
        val intent = Intent(Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS).apply {
            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        }
        context.startActivity(intent)
    }

    fun canDrawOverlays(): Boolean {
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            Settings.canDrawOverlays(context)
        } else {
            true
        }
    }

    fun requestOverlayPermission() {
        val intent = Intent(
            Settings.ACTION_MANAGE_OVERLAY_PERMISSION,
            Uri.parse("package:${context.packageName}")
        ).apply {
            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        }
        context.startActivity(intent)
    }

    fun isBatteryOptimizationDisabled(): Boolean {
        val appOps = context.getSystemService(Context.APP_OPS_SERVICE) as AppOpsManager
        val mode = appOps.unsafeCheckOpNoThrow(
            AppOpsManager.OPSTR_RUN_IN_BACKGROUND,
            android.os.Process.myUid(),
            context.packageName
        )
        return mode == AppOpsManager.MODE_ALLOWED
    }

    fun requestIgnoreBatteryOptimization() {
        val intent = Intent(Settings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS).apply {
            data = Uri.parse("package:${context.packageName}")
            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        }
        context.startActivity(intent)
    }

    fun isScreenCaptureAvailable(): Boolean {
        val mpManager = context.getSystemService(Context.MEDIA_PROJECTION_SERVICE) as MediaProjectionManager
        return mpManager.createScreenCaptureIntent() != null
    }

    fun getAllPermissions(): List<PermissionState> {
        return listOf(
            PermissionState(
                name = "accessibility",
                granted = isAccessibilityEnabled(),
                androidPermission = "BIND_ACCESSIBILITY_SERVICE",
                description = "Allows APA to navigate apps"
            ),
            PermissionState(
                name = "notifications",
                granted = isNotificationListenerEnabled(),
                androidPermission = "BIND_NOTIFICATION_LISTENER_SERVICE",
                description = "Allows APA to read notifications"
            ),
            PermissionState(
                name = "screen_capture",
                granted = isScreenCaptureAvailable(),
                androidPermission = "FOREGROUND_SERVICE",
                description = "Allows AI vision and OCR"
            ),
            PermissionState(
                name = "overlay",
                granted = canDrawOverlays(),
                androidPermission = "SYSTEM_ALERT_WINDOW",
                description = "Allows floating assistant"
            ),
            PermissionState(
                name = "battery_optimization",
                granted = isBatteryOptimizationDisabled(),
                androidPermission = "REQUEST_IGNORE_BATTERY_OPTIMIZATIONS",
                description = "Allow background operation"
            )
        )
    }

    fun getGrantedCount(): Int = getAllPermissions().count { it.granted }
    fun getTotalCount(): Int = getAllPermissions().size
    fun allGranted(): Boolean = getAllPermissions().all { it.granted }
}
