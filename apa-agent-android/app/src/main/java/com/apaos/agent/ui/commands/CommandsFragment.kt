package com.apaos.agent.ui.commands

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Toast
import androidx.fragment.app.Fragment
import com.apaos.agent.databinding.FragmentCommandsBinding
import com.apaos.agent.network.ApiClient

class CommandsFragment : Fragment() {

    private var _binding: FragmentCommandsBinding? = null
    private val binding get() = _binding!!

    override fun onCreateView(inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?): View {
        _binding = FragmentCommandsBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)
        setupCommandInput()
    }

    private fun setupCommandInput() {
        binding.btnSend.setOnClickListener {
            val command = binding.etCommand.text.toString().trim()
            if (command.isEmpty()) {
                Toast.makeText(context, "Enter a command", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }

            binding.tvStatus.text = "Processing: $command"
            binding.btnSend.isEnabled = false

            ApiClient.getInstance().executeCommand(command) { success, result ->
                activity?.runOnUiThread {
                    binding.btnSend.isEnabled = true
                    if (success) {
                        binding.tvStatus.text = "Command completed"
                        binding.tvResult.text = result?.toString() ?: "Done"
                    } else {
                        binding.tvStatus.text = "Command failed"
                        binding.tvResult.text = "Failed to execute command"
                    }
                    binding.etCommand.text?.clear()
                }
            }
        }

        // Quick command buttons
        binding.btnQuickScreenshot.setOnClickListener { executeQuickCommand("Take screenshot") }
        binding.btnQuickOpenApp.setOnClickListener { executeQuickCommand("Open Instagram") }
        binding.btnQuickReply.setOnClickListener { executeQuickCommand("Reply to latest WhatsApp") }
        binding.btnQuickCall.setOnClickListener { executeQuickCommand("Call John") }
    }

    private fun executeQuickCommand(command: String) {
        binding.etCommand.setText(command)
        binding.btnSend.performClick()
    }

    override fun onDestroyView() {
        _binding = null
        super.onDestroyView()
    }
}
