package com.apaos.agent.ui.onboarding

import android.content.Intent
import android.os.Bundle
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import com.apaos.agent.databinding.ActivityPermissionSetupBinding
import com.apaos.agent.core.PermissionChecker

class PermissionSetupActivity : AppCompatActivity() {

    private lateinit var binding: ActivityPermissionSetupBinding
    private lateinit var permissionChecker: PermissionChecker
    private var currentStep = 0
    private val permissions = mutableListOf<PermissionItem>()

    data class PermissionItem(
        val name: String,
        val title: String,
        val description: String,
        val action: () -> Unit,
        val check: () -> Boolean
    )

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityPermissionSetupBinding.inflate(layoutInflater)
        setContentView(binding.root)

        permissionChecker = PermissionChecker(this)
        setupPermissions()

        binding.btnGrant.setOnClickListener {
            permissions[currentStep].action()
        }

        binding.btnNext.setOnClickListener {
            onNextClick()
        }

        binding.btnSkip.setOnClickListener {
            onSkipClick()
        }

        updateUI()
    }

    override fun onResume() {
        super.onResume()
        updatePermissionStatus()
    }

    private fun setupPermissions() {
        permissions.clear()
        permissions.addAll(listOf(
            PermissionItem(
                name = "accessibility",
                title = "Accessibility Permission",
                description = "Allows APA to navigate apps",
                action = { permissionChecker.openAccessibilitySettings() },
                check = { permissionChecker.isAccessibilityEnabled() }
            ),
            PermissionItem(
                name = "notifications",
                title = "Notification Access",
                description = "Allows APA to read notifications",
                action = { permissionChecker.openNotificationListenerSettings() },
                check = { permissionChecker.isNotificationListenerEnabled() }
            ),
            PermissionItem(
                name = "screen_capture",
                title = "Screen Capture",
                description = "Allows AI vision and OCR",
                action = { Toast.makeText(this, "Screen capture will be requested when needed", Toast.LENGTH_SHORT).show() },
                check = { permissionChecker.isScreenCaptureAvailable() }
            ),
            PermissionItem(
                name = "overlay",
                title = "Overlay Permission",
                description = "Allows floating assistant",
                action = { permissionChecker.requestOverlayPermission() },
                check = { permissionChecker.canDrawOverlays() }
            ),
            PermissionItem(
                name = "battery",
                title = "Battery Optimization",
                description = "Allow background operation",
                action = { permissionChecker.requestIgnoreBatteryOptimization() },
                check = { permissionChecker.isBatteryOptimizationDisabled() }
            )
        ))
    }

    private fun updateUI() {
        if (currentStep >= permissions.size) {
            // All permissions handled, move to next screen
            val intent = Intent(this, DeviceRegistrationActivity::class.java)
            startActivity(intent)
            finish()
            return
        }

        val perm = permissions[currentStep]
        val granted = perm.check()

        binding.tvStep.text = "Step ${currentStep + 1} of ${permissions.size}"
        binding.tvTitle.text = perm.title
        binding.tvDescription.text = perm.description
        binding.tvStatus.text = if (granted) "✓ Granted" else "Not granted"
        binding.tvStatus.setTextColor(getColor(if (granted) android.R.color.holo_green_dark else android.R.color.holo_red_dark))

        binding.btnGrant.text = if (granted) "Already Granted" else "Grant Access"
        binding.btnGrant.isEnabled = !granted

        binding.progressBar.max = permissions.size
        binding.progressBar.progress = currentStep + 1
    }

    private fun updatePermissionStatus() {
        updateUI()
    }

    fun onNextClick() {
        currentStep++
        updateUI()
    }

    fun onSkipClick() {
        currentStep++
        updateUI()
    }
}
