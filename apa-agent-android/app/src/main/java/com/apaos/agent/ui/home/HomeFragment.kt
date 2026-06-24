package com.apaos.agent.ui.home

import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Toast
import androidx.fragment.app.Fragment
import com.apaos.agent.databinding.FragmentHomeBinding
import com.apaos.agent.core.DeviceCollector
import com.apaos.agent.network.ApiClient
import com.apaos.agent.network.WebSocketClient
import com.apaos.agent.services.APAForegroundService
import com.apaos.agent.services.APAAccessibilityService

class HomeFragment : Fragment() {

    private var _binding: FragmentHomeBinding? = null
    private val binding get() = _binding!!
    private lateinit var deviceCollector: DeviceCollector
    private val handler = Handler(Looper.getMainLooper())
    private val updateRunnable = object : Runnable {
        override fun run() {
            updateDeviceStatus()
            handler.postDelayed(this, 5000)
        }
    }

    override fun onCreateView(inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?): View {
        _binding = FragmentHomeBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)
        deviceCollector = DeviceCollector(requireContext())
        setupButtons()
        updateDeviceStatus()
        handler.postDelayed(updateRunnable, 5000)
    }

    private fun setupButtons() {
        binding.btnScreenshot.setOnClickListener {
            Toast.makeText(context, "Screenshot captured", Toast.LENGTH_SHORT).show()
        }

        binding.btnSync.setOnClickListener {
            Toast.makeText(context, "Syncing device...", Toast.LENGTH_SHORT).show()
            updateDeviceStatus()
        }

        binding.btnCommandCenter.setOnClickListener {
            (activity as? com.apaos.agent.MainActivity)?.let { main ->
                main.findViewById<com.google.android.material.bottomnavigation.BottomNavigationView>(
                    com.apaos.agent.R.id.bottomNav
                )?.selectedItemId = com.apaos.agent.R.id.nav_commands
            }
        }

        binding.btnDisconnect.setOnClickListener {
            Toast.makeText(context, "Disconnecting...", Toast.LENGTH_SHORT).show()
        }
    }

    private fun updateDeviceStatus() {
        if (!isAdded) return

        binding.tvBattery.text = "${deviceCollector.getBatteryLevel()}%"
        binding.tvNetwork.text = "${deviceCollector.getNetworkType().uppercase()} Connected"
        binding.tvCurrentApp.text = deviceCollector.getForegroundApp()
        binding.tvStatus.text = if (WebSocketClient.getInstance().isSocketConnected()) "Online" else "Connecting..."
        binding.tvConnectedTo.text = "Cheralathan-PC"
        binding.tvAiStatus.text = if (APAAccessibilityService.isRunning) "Ready" else "Starting..."
    }

    override fun onDestroyView() {
        handler.removeCallbacks(updateRunnable)
        _binding = null
        super.onDestroyView()
    }
}
