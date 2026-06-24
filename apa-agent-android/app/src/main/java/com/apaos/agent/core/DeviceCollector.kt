package com.apaos.agent.core

import android.annotation.SuppressLint
import android.app.ActivityManager
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.content.pm.PackageManager
import android.net.wifi.WifiManager
import android.os.BatteryManager
import android.os.Build
import android.os.Environment
import android.os.StatFs
import android.provider.Settings
import android.telephony.TelephonyManager
import com.apaos.agent.network.DeviceRegistration

class DeviceCollector(private val context: Context) {

    @SuppressLint("HardwareIds")
    fun collectDeviceInfo(): DeviceRegistration {
        return DeviceRegistration(
            deviceName = getDeviceName(),
            manufacturer = Build.MANUFACTURER,
            model = Build.MODEL,
            androidVersion = Build.VERSION.RELEASE,
            batteryLevel = getBatteryLevel(),
            screenWidth = context.resources.displayMetrics.widthPixels,
            screenHeight = context.resources.displayMetrics.heightPixels,
            serialNumber = getSerialNumber()
        )
    }

    fun getDeviceName(): String {
        val manufacturer = Build.MANUFACTURER
        val model = Build.MODEL
        return if (model.lowercase().startsWith(manufacturer.lowercase())) {
            model.replaceFirstChar { it.uppercase() }
        } else {
            "$manufacturer $model"
        }
    }

    fun getBatteryLevel(): Int {
        val batteryIntent = context.registerReceiver(null, IntentFilter(Intent.ACTION_BATTERY_CHANGED))
        val level = batteryIntent?.getIntExtra(BatteryManager.EXTRA_LEVEL, -1) ?: -1
        val scale = batteryIntent?.getIntExtra(BatteryManager.EXTRA_SCALE, -1) ?: -1
        return if (level == -1 || scale == -1) 0 else (level * 100 / scale)
    }

    fun isCharging(): Boolean {
        val batteryIntent = context.registerReceiver(null, IntentFilter(Intent.ACTION_BATTERY_CHANGED))
        val status = batteryIntent?.getIntExtra(BatteryManager.EXTRA_STATUS, -1) ?: -1
        return status == BatteryManager.BATTERY_STATUS_CHARGING || status == BatteryManager.BATTERY_STATUS_FULL
    }

    fun getNetworkType(): String {
        val connectivityManager = context.getSystemService(Context.CONNECTIVITY_SERVICE) as android.net.ConnectivityManager
        val network = connectivityManager.activeNetwork ?: return "none"
        val capabilities = connectivityManager.getNetworkCapabilities(network) ?: return "none"
        return when {
            capabilities.hasTransport(android.net.NetworkCapabilities.TRANSPORT_WIFI) -> "wifi"
            capabilities.hasTransport(android.net.NetworkCapabilities.TRANSPORT_CELLULAR) -> "mobile"
            capabilities.hasTransport(android.net.NetworkCapabilities.TRANSPORT_ETHERNET) -> "ethernet"
            else -> "other"
        }
    }

    fun getNetworkStrength(): Int {
        try {
            val wifiManager = context.applicationContext.getSystemService(Context.WIFI_SERVICE) as WifiManager
            val wifiInfo = wifiManager.connectionInfo
            return WifiManager.calculateSignalLevel(wifiInfo.rssi, 5)
        } catch (e: Exception) {
            return 0
        }
    }

    fun getStorageInfo(): Pair<Long, Long> {
        val stat = StatFs(Environment.getDataDirectory().path)
        val totalBytes = stat.totalBytes
        val freeBytes = stat.availableBytes
        return Pair(totalBytes, freeBytes)
    }

    fun getInstalledAppsCount(): Int {
        return context.packageManager.getInstalledApplications(PackageManager.GET_META_DATA).size
    }

    fun getInstalledApps(): List<Map<String, String>> {
        val apps = mutableListOf<Map<String, String>>()
        val packages = context.packageManager.getInstalledApplications(PackageManager.GET_META_DATA)
        for (pkg in packages) {
            val appInfo = context.packageManager.getApplicationInfo(pkg.packageName, 0)
            if ((appInfo.flags and android.content.pm.ApplicationInfo.FLAG_SYSTEM) == 0) {
                apps.add(mapOf(
                    "package" to pkg.packageName,
                    "name" to context.packageManager.getApplicationLabel(pkg).toString()
                ))
            }
        }
        return apps
    }

    fun getForegroundApp(): String {
        val activityManager = context.getSystemService(Context.ACTIVITY_SERVICE) as ActivityManager
        val runningTasks = activityManager.getRunningTasks(1)
        return if (runningTasks.isNotEmpty()) {
            val componentInfo = runningTasks[0].topActivity
            componentInfo?.packageName ?: "unknown"
        } else {
            "unknown"
        }
    }

    fun isScreenOn(): Boolean {
        return Settings.System.getInt(context.contentResolver, Settings.System.SCREEN_ON, 0) == 1
    }

    fun isDeviceLocked(): Boolean {
        val keyguardManager = context.getSystemService(Context.KEYGUARD_SERVICE) as android.app.KeyguardManager
        return keyguardManager.isKeyguardLocked
    }

    fun getAndroidVersion(): String = Build.VERSION.RELEASE
    fun getSDKVersion(): Int = Build.VERSION.SDK_INT
    fun getDeviceId(): String = "${Build.MANUFACTURER}_${Build.MODEL}_${Build.DEVICE}".replace(" ", "_")

    @SuppressLint("HardwareIds")
    fun getSerialNumber(): String {
        return try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                Build.getSerial()
            } else {
                Build.SERIAL ?: "unknown"
            }
        } catch (e: Exception) {
            "unknown"
        }
    }
}
