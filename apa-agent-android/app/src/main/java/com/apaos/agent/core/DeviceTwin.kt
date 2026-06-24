package com.apaos.agent.core

import android.content.Context
import com.apaos.agent.network.ApiClient
import com.google.gson.Gson
import com.google.gson.GsonBuilder

data class DeviceTwinData(
    val deviceId: String,
    val deviceName: String,
    val manufacturer: String,
    val model: String,
    val androidVersion: String,
    val batteryLevel: Int,
    val storageTotal: Long,
    val storageFree: Long,
    val installedApps: Int,
    val networkType: String,
    val permissions: Map<String, Boolean>,
    val capabilities: Map<String, Boolean>,
    val health: DeviceHealth
)

data class DeviceHealth(
    val batteryHealth: String,
    val storageHealth: String,
    val networkHealth: String,
    val overallScore: Int
)

class DeviceTwin(private val context: Context) {

    private val deviceCollector = DeviceCollector(context)
    private val permissionChecker = PermissionChecker(context)
    private val gson: Gson = GsonBuilder().create()

    fun createDeviceTwin(): DeviceTwinData {
        val deviceInfo = deviceCollector.collectDeviceInfo()
        val permissions = permissionChecker.getAllPermissions().associate { it.name to it.granted }
        val (totalStorage, freeStorage) = deviceCollector.getStorageInfo()
        val networkType = deviceCollector.getNetworkType()
        val batteryLevel = deviceCollector.getBatteryLevel()

        val capabilities = mapOf(
            "adb" to true,
            "ocr" to true,
            "screenshot" to true,
            "navigation" to permissionChecker.isAccessibilityEnabled(),
            "notifications" to permissionChecker.isNotificationListenerEnabled(),
            "voice" to true,
            "app_control" to permissionChecker.isAccessibilityEnabled()
        )

        val health = calculateHealth(batteryLevel, freeStorage, totalStorage, networkType)

        return DeviceTwinData(
            deviceId = ApiClient.getInstance().getDeviceId(),
            deviceName = deviceInfo.deviceName,
            manufacturer = deviceInfo.manufacturer,
            model = deviceInfo.model,
            androidVersion = deviceInfo.androidVersion,
            batteryLevel = batteryLevel,
            storageTotal = totalStorage,
            storageFree = freeStorage,
            installedApps = deviceCollector.getInstalledAppsCount(),
            networkType = networkType,
            permissions = permissions,
            capabilities = capabilities,
            health = health
        )
    }

    private fun calculateHealth(battery: Int, freeStorage: Long, totalStorage: Long, network: String): DeviceHealth {
        val batteryHealth = when {
            battery > 80 -> "Excellent"
            battery > 50 -> "Good"
            battery > 20 -> "Fair"
            else -> "Low"
        }

        val storageRatio = if (totalStorage > 0) freeStorage.toFloat() / totalStorage else 0f
        val storageHealth = when {
            storageRatio > 0.5 -> "Excellent"
            storageRatio > 0.25 -> "Good"
            storageRatio > 0.1 -> "Fair"
            else -> "Low"
        }

        val networkHealth = when (network) {
            "wifi" -> "Excellent"
            "mobile" -> "Good"
            "ethernet" -> "Excellent"
            else -> "No Connection"
        }

        val score = listOf(
            if (battery > 50) 25 else if (battery > 20) 15 else 5,
            if (storageRatio > 0.25) 25 else 10,
            if (network != "none") 25 else 0,
            25 // Base score
        ).sum()

        return DeviceHealth(batteryHealth, storageHealth, networkHealth, score)
    }

    fun toJson(twin: DeviceTwinData): String = gson.toJson(twin)
}
