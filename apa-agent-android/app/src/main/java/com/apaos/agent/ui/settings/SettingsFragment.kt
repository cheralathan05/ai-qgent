package com.apaos.agent.ui.settings

import android.content.Intent
import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Toast
import androidx.fragment.app.Fragment
import com.apaos.agent.databinding.FragmentSettingsBinding
import com.apaos.agent.network.ApiClient
import com.apaos.agent.ui.onboarding.QRScanActivity
import com.apaos.agent.core.PermissionChecker
import com.apaos.agent.services.APAForegroundService

class SettingsFragment : Fragment() {

    private var _binding: FragmentSettingsBinding? = null
    private val binding get() = _binding!!
    private lateinit var permissionChecker: PermissionChecker

    override fun onCreateView(inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?): View {
        _binding = FragmentSettingsBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)
        permissionChecker = PermissionChecker(requireContext())
        loadSettings()
        setupActions()
    }

    private fun loadSettings() {
        binding.tvDeviceId.text = "Device: ${ApiClient.getInstance().getDeviceId().take(20)}"
        binding.tvUser.text = "User: ${ApiClient.getInstance().getUserId()}"

        val granted = permissionChecker.getGrantedCount()
        val total = permissionChecker.getTotalCount()
        binding.tvPermissions.text = "Permissions: $granted/$total granted"
    }

    private fun setupActions() {
        binding.btnConnectedDevices.setOnClickListener {
            Toast.makeText(context, "Connected devices list coming soon", Toast.LENGTH_SHORT).show()
        }

        binding.btnTrustedDevices.setOnClickListener {
            Toast.makeText(context, "Trusted devices list coming soon", Toast.LENGTH_SHORT).show()
        }

        binding.btnPermissions.setOnClickListener {
            Toast.makeText(context, "Permission management coming soon", Toast.LENGTH_SHORT).show()
        }

        binding.btnSecurity.setOnClickListener {
            Toast.makeText(context, "Security settings coming soon", Toast.LENGTH_SHORT).show()
        }

        binding.btnNotifications.setOnClickListener {
            Toast.makeText(context, "Notification settings coming soon", Toast.LENGTH_SHORT).show()
        }

        binding.btnAiSettings.setOnClickListener {
            Toast.makeText(context, "AI settings coming soon", Toast.LENGTH_SHORT).show()
        }

        binding.btnDeviceTwin.setOnClickListener {
            Toast.makeText(context, "Device twin info coming soon", Toast.LENGTH_SHORT).show()
        }

        binding.btnLogs.setOnClickListener {
            Toast.makeText(context, "Activity logs coming soon", Toast.LENGTH_SHORT).show()
        }

        binding.btnDisconnect.setOnClickListener {
            val serviceIntent = Intent(requireContext(), APAForegroundService::class.java).apply {
                action = "STOP"
            }
            requireContext().startService(serviceIntent)
            Toast.makeText(context, "Disconnected", Toast.LENGTH_SHORT).show()
        }

        binding.btnFactoryReset.setOnClickListener {
            ApiClient.getInstance().setDeviceId("")
            ApiClient.getInstance().setAuthToken("")
            val intent = Intent(requireContext(), QRScanActivity::class.java)
            intent.flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
            startActivity(intent)
        }
    }

    override fun onDestroyView() {
        _binding = null
        super.onDestroyView()
    }
}
