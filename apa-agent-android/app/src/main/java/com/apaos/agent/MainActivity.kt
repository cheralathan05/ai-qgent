package com.apaos.agent

import android.content.Intent
import android.os.Bundle
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.fragment.app.Fragment
import com.apaos.agent.databinding.ActivityMainBinding
import com.apaos.agent.ui.home.HomeFragment
import com.apaos.agent.ui.commands.CommandsFragment
import com.apaos.agent.ui.apps.AppsFragment
import com.apaos.agent.ui.automation.AutomationFragment
import com.apaos.agent.ui.activity.ActivityFragment
import com.apaos.agent.ui.settings.SettingsFragment
import com.apaos.agent.ui.onboarding.QRScanActivity
import com.apaos.agent.network.ApiClient

class MainActivity : AppCompatActivity() {

    private lateinit var binding: ActivityMainBinding

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        // Check if device is paired
        if (ApiClient.getInstance().getDeviceId().isEmpty()) {
            // Not paired, show QR scan
            startActivity(Intent(this, QRScanActivity::class.java))
            finish()
            return
        }

        setupBottomNav()
        loadFragment(HomeFragment())
    }

    private fun setupBottomNav() {
        binding.bottomNav.setOnItemSelectedListener { item ->
            when (item.itemId) {
                R.id.nav_home -> { loadFragment(HomeFragment()); true }
                R.id.nav_commands -> { loadFragment(CommandsFragment()); true }
                R.id.nav_apps -> { loadFragment(AppsFragment()); true }
                R.id.nav_automation -> { loadFragment(AutomationFragment()); true }
                R.id.nav_activity -> { loadFragment(ActivityFragment()); true }
                R.id.nav_settings -> { loadFragment(SettingsFragment()); true }
                else -> false
            }
        }
    }

    private fun loadFragment(fragment: Fragment) {
        supportFragmentManager.beginTransaction()
            .replace(R.id.fragmentContainer, fragment)
            .commit()
    }

    @Deprecated("Use OnBackPressedCallback instead")
    override fun onBackPressed() {
        if (supportFragmentManager.backStackEntryCount > 0) {
            supportFragmentManager.popBackStack()
        } else {
            super.onBackPressed()
        }
    }
}
