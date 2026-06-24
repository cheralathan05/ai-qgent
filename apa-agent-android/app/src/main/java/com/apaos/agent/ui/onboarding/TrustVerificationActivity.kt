package com.apaos.agent.ui.onboarding

import android.content.Intent
import android.os.Bundle
import android.os.CountDownTimer
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import com.apaos.agent.databinding.ActivityTrustVerificationBinding
import com.apaos.agent.core.DeviceCollector
import com.apaos.agent.network.ApiClient

class TrustVerificationActivity : AppCompatActivity() {

    private lateinit var binding: ActivityTrustVerificationBinding
    private var trustCode = ""
    private var sessionId = ""
    private var timer: CountDownTimer? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityTrustVerificationBinding.inflate(layoutInflater)
        setContentView(binding.root)

        sessionId = intent.getStringExtra("session_id") ?: ApiClient.getInstance().getSessionId()
        trustCode = generateTrustCode()

        binding.tvTrustCode.text = trustCode
        binding.tvDescription.text = "Confirm this code matches the desktop."

        startTimer()

        binding.btnVerify.setOnClickListener { verifyCode() }
        binding.btnCancel.setOnClickListener { finish() }
    }

    private fun generateTrustCode(): String {
        return (100000..999999).random().toString()
    }

    private fun startTimer() {
        timer?.cancel()
        timer = object : CountDownTimer(120000, 1000) {
            override fun onTick(millisUntilFinished: Long) {
                val seconds = millisUntilFinished / 1000
                binding.tvTimer.text = "Code expires in ${seconds / 60}:${String.format("%02d", seconds % 60)}"
            }
            override fun onFinish() {
                binding.tvTimer.text = "Code expired"
                binding.btnVerify.isEnabled = false
            }
        }.start()
    }

    private fun verifyCode() {
        val enteredCode = binding.etCode.text.toString().trim()

        if (enteredCode.isEmpty()) {
            Toast.makeText(this, "Enter the trust code", Toast.LENGTH_SHORT).show()
            return
        }

        if (enteredCode != trustCode) {
            Toast.makeText(this, "Code doesn't match. Try again.", Toast.LENGTH_SHORT).show()
            return
        }

        binding.btnVerify.isEnabled = false
        binding.tvStatus.text = "Verifying..."

        val deviceCollector = DeviceCollector(this)
        val deviceInfo = deviceCollector.collectDeviceInfo()

        ApiClient.getInstance().reportQRScan(sessionId, deviceInfo) { success, returnedTrustCode ->
            runOnUiThread {
                if (success) {
                    ApiClient.getInstance().confirmQRPair(sessionId, trustCode) { confirmSuccess, deviceId ->
                        runOnUiThread {
                            if (confirmSuccess) {
                                Toast.makeText(this, "Trust verified!", Toast.LENGTH_SHORT).show()
                                val intent = Intent(this, PermissionSetupActivity::class.java).apply {
                                    putExtra("device_id", deviceId ?: "")
                                }
                                startActivity(intent)
                                finish()
                            } else {
                                binding.btnVerify.isEnabled = true
                                binding.tvStatus.text = "Verification failed"
                                Toast.makeText(this, "Verification failed", Toast.LENGTH_SHORT).show()
                            }
                        }
                    }
                } else {
                    binding.btnVerify.isEnabled = true
                    binding.tvStatus.text = "Scan failed"
                    Toast.makeText(this, "Failed to report scan", Toast.LENGTH_SHORT).show()
                }
            }
        }
    }

    override fun onDestroy() {
        timer?.cancel()
        super.onDestroy()
    }
}
