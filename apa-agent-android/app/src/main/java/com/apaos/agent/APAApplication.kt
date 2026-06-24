package com.apaos.agent

import android.app.Application
import android.app.NotificationChannel
import android.app.NotificationManager
import android.os.Build

class APAApplication : Application() {

    companion object {
        lateinit var instance: APAApplication
            private set
    }

    override fun onCreate() {
        super.onCreate()
        instance = this
        createNotificationChannels()
    }

    private fun createNotificationChannels() {
        val manager = getSystemService(NotificationManager::class.java) ?: return

        val serviceChannel = NotificationChannel(
            "apa_service",
            "APA Service",
            NotificationManager.IMPORTANCE_LOW
        ).apply {
            description = "APA Agent background service"
            setShowBadge(false)
        }

        val alertChannel = NotificationChannel(
            "apa_alerts",
            "APA Alerts",
            NotificationManager.IMPORTANCE_HIGH
        ).apply {
            description = "Notifications from APA Agent"
            enableVibration(true)
        }

        manager.createNotificationChannels(listOf(serviceChannel, alertChannel))
    }
}
