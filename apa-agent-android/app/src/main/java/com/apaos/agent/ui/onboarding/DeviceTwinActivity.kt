package com.apaos.agent.ui.onboarding

import android.content.Intent
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import androidx.appcompat.app.AppCompatActivity
import com.apaos.agent.databinding.ActivityDeviceTwinBinding
import com.apaos.agent.core.DeviceTwin
import com.apaos.agent.core.DeviceCollector
import com.apaos.agent.services.APAForegroundService

class DeviceTwinActivity : AppCompatActivity() {

    private lateinit var binding: ActivityDeviceTwinBinding
    private lateinit var deviceTwin: DeviceTwin
    private val handler = Handler(Looper.getMainLooper())

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityDeviceTwinBinding.inflate(layoutInflater)
        setContentView(binding.root)

        deviceTwin = DeviceTwin(this)
        startTwinCreation()
    }

    private fun startTwinCreation() {
        binding.tvStatus.text = "Generating Digital Twin..."
        binding.animationView.setAnimation("twin_generation.json")

        handler.postDelayed({
            val twin = deviceTwin.createDeviceTwin()
            displayTwin(twin)
        }, 2000)
    }

    private fun displayTwin(twin: com.apaos.agent.core.DeviceTwinData) {
        binding.tvStatus.text = "Your Device Twin is Ready"

        val health = twin.health
        binding.tvBatteryHealth.text = health.batteryHealth
        binding.tvStorageHealth.text = health.storageHealth
        binding.tvNetworkHealth.text = health.networkHealth
        binding.tvScore.text = "${health.overallScore}%"

        val storageUsed = twin.storageTotal - twin.storageFree
        val storageGB = String.format("%.1f", storageUsed / (1024.0 * 1024 * 1024))
        val totalGB = String.format("%.1f", twin.storageTotal / (1024.0 * 1024 * 1024))
        binding.tvStorage.text = "$storageGB / $totalGB GB"
        binding.tvApps.text = "${twin.installedApps} apps"
        binding.tvNetworkType.text = twin.networkType.uppercase()

        binding.btnLaunch.isEnabled = true
        binding.btnLaunch.setOnClickListener {
            // Start foreground service
            val serviceIntent = Intent(this, APAForegroundService::class.java).apply {
                action = "START"
            }
            startForegroundService(serviceIntent)

            // Launch main dashboard
            val intent = Intent(this, com.apaos.agent.MainActivity::class.java).apply {
                flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
            }
            startActivity(intent)
            finish()
        }
    }
}
