package com.apaos.agent.ui.onboarding

import android.content.Intent
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import androidx.appcompat.app.AppCompatActivity
import com.apaos.agent.databinding.ActivityDeviceRegistrationBinding
import com.apaos.agent.core.DeviceCollector
import com.apaos.agent.network.ApiClient

class DeviceRegistrationActivity : AppCompatActivity() {

    private lateinit var binding: ActivityDeviceRegistrationBinding
    private lateinit var deviceCollector: DeviceCollector
    private val handler = Handler(Looper.getMainLooper())
    private var progress = 0

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityDeviceRegistrationBinding.inflate(layoutInflater)
        setContentView(binding.root)

        deviceCollector = DeviceCollector(this)
        startRegistration()
    }

    private fun startRegistration() {
        val deviceInfo = deviceCollector.collectDeviceInfo()

        binding.tvDeviceName.text = deviceInfo.deviceName
        binding.tvManufacturer.text = deviceInfo.manufacturer
        binding.tvModel.text = deviceInfo.model
        binding.tvAndroidVersion.text = "Android ${deviceInfo.androidVersion}"
        binding.tvBattery.text = "${deviceInfo.batteryLevel}%"
        binding.tvScreen.text = "${deviceInfo.screenWidth} x ${deviceInfo.screenHeight}"
        binding.tvSerial.text = deviceInfo.serialNumber
        binding.tvApps.text = "${deviceCollector.getInstalledAppsCount()} apps"
        binding.tvNetwork.text = deviceCollector.getNetworkType().uppercase()

        simulateProgress()
    }

    private fun simulateProgress() {
        handler.postDelayed(object : Runnable {
            override fun run() {
                progress += 2
                binding.progressBar.progress = progress
                binding.tvProgress.text = "$progress%"

                when {
                    progress < 25 -> binding.tvStatus.text = "Scanning device..."
                    progress < 50 -> binding.tvStatus.text = "Collecting info..."
                    progress < 75 -> binding.tvStatus.text = "Registering device..."
                    progress < 100 -> binding.tvStatus.text = "Almost done..."
                    else -> {
                        binding.tvStatus.text = "Device registered!"
                        handler.postDelayed({
                            val intent = Intent(this@DeviceRegistrationActivity, AIReadinessActivity::class.java)
                            startActivity(intent)
                            finish()
                        }, 500)
                        return
                    }
                }

                if (progress < 100) handler.postDelayed(this, 30)
            }
        }, 100)
    }
}
