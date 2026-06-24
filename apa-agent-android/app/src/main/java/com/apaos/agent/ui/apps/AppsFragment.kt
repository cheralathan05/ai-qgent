package com.apaos.agent.ui.apps

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Toast
import androidx.fragment.app.Fragment
import androidx.recyclerview.widget.GridLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.apaos.agent.databinding.FragmentAppsBinding
import com.apaos.agent.core.DeviceCollector
import com.apaos.agent.network.ApiClient

class AppsFragment : Fragment() {

    private var _binding: FragmentAppsBinding? = null
    private val binding get() = _binding!!
    private lateinit var deviceCollector: DeviceCollector
    private val apps = mutableListOf<Map<String, String>>()

    override fun onCreateView(inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?): View {
        _binding = FragmentAppsBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)
        deviceCollector = DeviceCollector(requireContext())
        loadApps()
    }

    private fun loadApps() {
        apps.clear()
        apps.addAll(deviceCollector.getInstalledApps())

        // Add common apps if not in list
        val commonApps = listOf(
            mapOf("name" to "Instagram", "package" to "com.instagram.android"),
            mapOf("name" to "WhatsApp", "package" to "com.whatsapp"),
            mapOf("name" to "Chrome", "package" to "com.android.chrome"),
            mapOf("name" to "YouTube", "package" to "com.google.android.youtube"),
            mapOf("name" to "Spotify", "package" to "com.spotify.music"),
            mapOf("name" to "Camera", "package" to "com.android.camera"),
            mapOf("name" to "Gallery", "package" to "com.android.gallery3d"),
            mapOf("name" to "Phone", "package" to "com.android.dialer")
        )

        for (app in commonApps) {
            if (apps.none { it["package"] == app["package"] }) {
                apps.add(app)
            }
        }

        binding.tvAppCount.text = "${apps.size} apps installed"

        val adapter = AppsAdapter(apps) { app ->
            val appName = app["name"] ?: app["package"] ?: "Unknown"
            Toast.makeText(context, "Opening $appName...", Toast.LENGTH_SHORT).show()
            ApiClient.getInstance().executeCommand("Open $appName") { success, _ ->
                activity?.runOnUiThread {
                    Toast.makeText(context, if (success) "$appName opened" else "Failed to open $appName", Toast.LENGTH_SHORT).show()
                }
            }
        }

        binding.rvApps.layoutManager = GridLayoutManager(context, 3)
        binding.rvApps.adapter = adapter
    }

    override fun onDestroyView() {
        _binding = null
        super.onDestroyView()
    }
}

class AppsAdapter(
    private val apps: List<Map<String, String>>,
    private val onClick: (Map<String, String>) -> Unit
) : RecyclerView.Adapter<AppsAdapter.AppViewHolder>() {

    class AppViewHolder(val binding: com.apaos.agent.databinding.ItemAppBinding) : RecyclerView.ViewHolder(binding.root)

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): AppViewHolder {
        val binding = com.apaos.agent.databinding.ItemAppBinding.inflate(
            LayoutInflater.from(parent.context), parent, false
        )
        return AppViewHolder(binding)
    }

    override fun onBindViewHolder(holder: AppViewHolder, position: Int) {
        val app = apps[position]
        holder.binding.tvAppName.text = app["name"] ?: "Unknown"
        holder.binding.root.setOnClickListener { onClick(app) }
    }

    override fun getItemCount() = apps.size
}
