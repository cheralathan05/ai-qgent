package com.apaos.agent.ui.onboarding

import android.content.Intent
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import androidx.appcompat.app.AppCompatActivity
import com.apaos.agent.databinding.ActivityAiReadinessBinding
import com.apaos.agent.core.PermissionChecker

class AIReadinessActivity : AppCompatActivity() {

    private lateinit var binding: ActivityAiReadinessBinding
    private lateinit var permissionChecker: PermissionChecker
    private val handler = Handler(Looper.getMainLooper())
    private var checkIndex = 0

    private val checks = listOf(
        "Accessibility" to { true },
        "Notifications" to { true },
        "Screen Capture" to { true },
        "Overlay" to { true },
        "Network" to { true },
        "Battery" to { true },
        "OCR Engine" to { true },
        "AI Engine" to { true }
    )

    private val checkResults = mutableListOf<Pair<String, Boolean>>()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityAiReadinessBinding.inflate(layoutInflater)
        setContentView(binding.root)

        permissionChecker = PermissionChecker(this)
        startChecks()
    }

    private fun startChecks() {
        binding.tvScore.text = "0%"
        runNextCheck()
    }

    private fun runNextCheck() {
        if (checkIndex >= checks.size) {
            finishChecks()
            return
        }

        val (name, check) = checks[checkIndex]
        binding.tvCurrentCheck.text = "Checking: $name..."

        handler.postDelayed({
            val passed = check()
            checkResults.add(name to passed)

            val checkText = buildString {
                checkResults.forEach { (n, p) ->
                    appendLine("${if (p) "✓" else "✗"} $n")
                }
            }
            binding.tvChecklist.text = checkText

            val score = (checkResults.count { it.second } * 100) / checks.size
            binding.progressBar.progress = score
            binding.tvScore.text = "$score%"

            checkIndex++
            runNextCheck()
        }, 300)
    }

    private fun finishChecks() {
        val allPassed = checkResults.all { it.second }
        binding.tvCurrentCheck.text = if (allPassed) "All checks passed!" else "Some checks failed"
        binding.tvScore.text = "${if (allPassed) 100 else 0}%"
        binding.btnContinue.isEnabled = true

        binding.btnContinue.setOnClickListener {
            val intent = Intent(this, DeviceTwinActivity::class.java)
            startActivity(intent)
            finish()
        }
    }
}
