package com.apaos.agent.ui.activity

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import androidx.fragment.app.Fragment
import com.apaos.agent.databinding.FragmentActivityBinding
import java.text.SimpleDateFormat
import java.util.*

class ActivityFragment : Fragment() {

    private var _binding: FragmentActivityBinding? = null
    private val binding get() = _binding!!

    override fun onCreateView(inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?): View {
        _binding = FragmentActivityBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)
        loadActivityTimeline()
    }

    private fun loadActivityTimeline() {
        val activities = listOf(
            ActivityItem("Device Connected", "Connected to Cheralathan-PC", "2 min ago", "connected"),
            ActivityItem("Permissions Granted", "All permissions enabled", "2 min ago", "permission"),
            ActivityItem("Command Executed", "Open Instagram", "5 min ago", "command"),
            ActivityItem("Screenshot Taken", "Screen capture saved", "8 min ago", "screenshot"),
            ActivityItem("Automation Triggered", "Battery saver enabled", "12 min ago", "automation"),
            ActivityItem("AI Decision", "Recommended app: Spotify", "15 min ago", "ai")
        )

        val adapter = ActivityAdapter(activities)
        binding.rvActivity.adapter = adapter
        binding.tvTotalCount.text = "${activities.size} activities"
    }

    override fun onDestroyView() {
        _binding = null
        super.onDestroyView()
    }
}

data class ActivityItem(
    val title: String,
    val description: String,
    val time: String,
    val type: String
)

class ActivityAdapter(private val items: List<ActivityItem>) : RecyclerView.Adapter<ActivityAdapter.ViewHolder>() {

    class ViewHolder(val binding: com.apaos.agent.databinding.ItemActivityBinding) : RecyclerView.ViewHolder(binding.root)

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ViewHolder {
        val binding = com.apaos.agent.databinding.ItemActivityBinding.inflate(
            LayoutInflater.from(parent.context), parent, false
        )
        return ViewHolder(binding)
    }

    override fun onBindViewHolder(holder: ViewHolder, position: Int) {
        val item = items[position]
        holder.binding.tvTitle.text = item.title
        holder.binding.tvDescription.text = item.description
        holder.binding.tvTime.text = item.time
    }

    override fun getItemCount() = items.size
}
