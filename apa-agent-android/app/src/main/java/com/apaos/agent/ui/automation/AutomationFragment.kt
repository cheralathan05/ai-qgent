package com.apaos.agent.ui.automation

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Toast
import androidx.fragment.app.Fragment
import com.apaos.agent.databinding.FragmentAutomationBinding

class AutomationFragment : Fragment() {

    private var _binding: FragmentAutomationBinding? = null
    private val binding get() = _binding!!

    override fun onCreateView(inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?): View {
        _binding = FragmentAutomationBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        binding.btnCreateAutomation.setOnClickListener {
            Toast.makeText(context, "Create automation wizard coming soon", Toast.LENGTH_SHORT).show()
        }

        // Example automations
        val automations = listOf(
            "When battery below 20% → Enable Power Saving",
            "When WhatsApp from boss → Notify immediately",
            "When connected to office WiFi → Open Slack",
            "When screen on → Take screenshot for memory",
            "When notification received → Summarize with AI"
        )

        val adapter = AutomationAdapter(automations)
        binding.rvAutomations.adapter = adapter
    }

    override fun onDestroyView() {
        _binding = null
        super.onDestroyView()
    }
}

class AutomationAdapter(private val items: List<String>) : RecyclerView.Adapter<AutomationAdapter.ViewHolder>() {

    class ViewHolder(val binding: com.apaos.agent.databinding.ItemAutomationBinding) : RecyclerView.ViewHolder(binding.root)

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ViewHolder {
        val binding = com.apaos.agent.databinding.ItemAutomationBinding.inflate(
            LayoutInflater.from(parent.context), parent, false
        )
        return ViewHolder(binding)
    }

    override fun onBindViewHolder(holder: ViewHolder, position: Int) {
        holder.binding.tvAutomation.text = items[position]
    }

    override fun getItemCount() = items.size
}
