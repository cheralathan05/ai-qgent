package com.apaos.agent.network

import android.content.Context
import android.content.SharedPreferences
import com.google.gson.Gson
import com.google.gson.GsonBuilder
import okhttp3.*
import java.io.IOException
import java.util.concurrent.TimeUnit

data class ApiResponse(
    val success: Boolean,
    val message: String = "",
    val data: Any? = null
)

data class PairingSession(
    val sessionId: String,
    val pairCode: String,
    val trustCode: String = "",
    val status: String = "pending"
)

data class DeviceRegistration(
    val deviceName: String,
    val manufacturer: String,
    val model: String,
    val androidVersion: String,
    val batteryLevel: Int,
    val screenWidth: Int,
    val screenHeight: Int,
    val serialNumber: String
)

data class TrustVerification(
    val deviceId: String,
    val trustCode: String,
    val trustLevel: String = "always_trusted"
)

data class PermissionUpdate(
    val deviceId: String,
    val permissionName: String,
    val status: String
)

data class CommandExecution(
    val command: String,
    val deviceId: String,
    val parameters: Map<String, Any> = emptyMap()
)

data class DeviceHeartbeat(
    val deviceId: String,
    val batteryLevel: Int,
    val foregroundApp: String,
    val screenState: String,
    val lockState: String,
    val networkType: String,
    val networkStrength: Int
)

class ApiClient private constructor() {

    companion object {
        private const val PREFS_NAME = "apa_agent_prefs"
        private const val KEY_BASE_URL = "base_url"
        private const val KEY_AUTH_TOKEN = "auth_token"
        private const val KEY_REFRESH_TOKEN = "refresh_token"
        private const val KEY_DEVICE_ID = "device_id"
        private const val KEY_USER_ID = "user_id"
        private const val KEY_SESSION_ID = "session_id"
        private const val DEFAULT_BASE_URL = "http://10.0.2.2:8000"

        private var instance: ApiClient? = null

        fun initialize(context: Context) {
            if (instance == null) {
                instance = ApiClient().apply {
                    prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
                    gson = GsonBuilder().create()
                }
            }
        }

        fun getInstance(): ApiClient {
            return instance ?: throw IllegalStateException("ApiClient not initialized")
        }
    }

    private lateinit var prefs: SharedPreferences
    private lateinit var gson: Gson

    private val client = OkHttpClient.Builder()
        .connectTimeout(30, TimeUnit.SECONDS)
        .readTimeout(30, TimeUnit.SECONDS)
        .writeTimeout(30, TimeUnit.SECONDS)
        .addInterceptor { chain ->
            val request = chain.request().newBuilder()
            val token = getAuthToken()
            if (token.isNotEmpty()) {
                request.addHeader("Authorization", "Bearer $token")
            }
            request.addHeader("Content-Type", "application/json")
            chain.proceed(request.build())
        }
        .build()

    fun getBaseUrl(): String = prefs.getString(KEY_BASE_URL, DEFAULT_BASE_URL) ?: DEFAULT_BASE_URL
    fun setBaseUrl(url: String) = prefs.edit().putString(KEY_BASE_URL, url).apply()
    fun getAuthToken(): String = prefs.getString(KEY_AUTH_TOKEN, "") ?: ""
    fun setAuthToken(token: String) = prefs.edit().putString(KEY_AUTH_TOKEN, token).apply()
    fun setRefreshToken(token: String) = prefs.edit().putString(KEY_REFRESH_TOKEN, token).apply()
    fun getDeviceId(): String = prefs.getString(KEY_DEVICE_ID, "") ?: ""
    fun setDeviceId(id: String) = prefs.edit().putString(KEY_DEVICE_ID, id).apply()
    fun getUserId(): String = prefs.getString(KEY_USER_ID, "mobile_user") ?: "mobile_user"
    fun setUserId(id: String) = prefs.edit().putString(KEY_USER_ID, id).apply()
    fun getSessionId(): String = prefs.getString(KEY_SESSION_ID, "") ?: ""
    fun setSessionId(id: String) = prefs.edit().putString(KEY_SESSION_ID, id).apply()

    // ==================== Auth APIs ====================

    fun login(email: String, password: String, callback: (Boolean, String, String?) -> Unit) {
        val body = gson.toJson(mapOf("email" to email, "password" to password))
        post("/api/v2/auth/login", body) { success, response ->
            try {
                val json = gson.fromJson(response, Map::class.java)
                if (success && json["success"] == true) {
                    val token = json["token"] as? String ?: ""
                    val refreshToken = json["refresh_token"] as? String ?: ""
                    val userId = json["user_id"] as? String ?: ""
                    setAuthToken(token)
                    setRefreshToken(refreshToken)
                    setUserId(userId)
                    callback(true, "Login successful", userId)
                } else {
                    callback(false, json["message"] as? String ?: "Login failed", null)
                }
            } catch (e: Exception) {
                callback(false, "Login failed: ${e.message}", null)
            }
        }
    }

    // ==================== Pairing APIs ====================

    fun createQRSession(callback: (Boolean, PairingSession?) -> Unit) {
        post("/api/v2/devices/qr/create", "") { success, response ->
            try {
                val json = gson.fromJson(response, Map::class.java)
                if (success && json["success"] == true) {
                    val session = PairingSession(
                        sessionId = json["session_id"] as? String ?: "",
                        pairCode = json["pair_code"] as? String ?: ""
                    )
                    setSessionId(session.sessionId)
                    callback(true, session)
                } else {
                    callback(false, null)
                }
            } catch (e: Exception) {
                callback(false, null)
            }
        }
    }

    fun reportQRScan(sessionId: String, deviceInfo: DeviceRegistration, callback: (Boolean, String?) -> Unit) {
        val body = gson.toJson(mapOf(
            "session_id" to sessionId,
            "device_serial" to deviceInfo.serialNumber,
            "device_info" to mapOf(
                "device_name" to deviceInfo.deviceName,
                "manufacturer" to deviceInfo.manufacturer,
                "model" to deviceInfo.model,
                "android_version" to deviceInfo.androidVersion,
                "battery_level" to deviceInfo.batteryLevel,
                "screen_width" to deviceInfo.screenWidth,
                "screen_height" to deviceInfo.screenHeight,
                "serial" to deviceInfo.serialNumber
            )
        ))
        post("/api/v2/devices/qr/scan", body) { success, response ->
            try {
                val json = gson.fromJson(response, Map::class.java)
                if (success && json["success"] == true) {
                    val trustCode = json["trust_code"] as? String
                    callback(true, trustCode)
                } else {
                    callback(false, null)
                }
            } catch (e: Exception) {
                callback(false, null)
            }
        }
    }

    fun confirmQRPair(sessionId: String, trustCode: String, callback: (Boolean, String?) -> Unit) {
        val body = gson.toJson(mapOf(
            "session_id" to sessionId,
            "trust_code" to trustCode
        ))
        post("/api/v2/devices/qr/confirm", body) { success, response ->
            try {
                val json = gson.fromJson(response, Map::class.java)
                if (success && json["success"] == true) {
                    val deviceId = json["device_id"] as? String
                    if (deviceId != null) setDeviceId(deviceId)
                    callback(true, deviceId)
                } else {
                    callback(false, null)
                }
            } catch (e: Exception) {
                callback(false, null)
            }
        }
    }

    fun trustDevice(deviceId: String, callback: (Boolean) -> Unit) {
        val body = gson.toJson(mapOf(
            "device_id" to deviceId,
            "trust_level" to "always_trusted",
            "duration_days" to 365
        ))
        post("/api/v2/trust/grant", body) { success, response ->
            callback(success)
        }
    }

    // ==================== Permission APIs ====================

    fun updatePermission(deviceId: String, permission: String, status: String, callback: (Boolean) -> Unit) {
        val body = gson.toJson(mapOf(
            "device_id" to deviceId,
            "permission_name" to permission,
            "status" to status
        ))
        post("/api/v2/permissions/request", body) { success, _ ->
            callback(success)
        }
    }

    // ==================== Device APIs ====================

    fun getDeviceInfo(callback: (Boolean, Map<String, Any>?) -> Unit) {
        val deviceId = getDeviceId()
        get("/api/v2/devices/$deviceId") { success, response ->
            try {
                val json = gson.fromJson(response, Map::class.java)
                if (success && json["success"] == true) {
                    @Suppress("UNCHECKED_CAST")
                    callback(true, json["device"] as? Map<String, Any>)
                } else {
                    callback(false, null)
                }
            } catch (e: Exception) {
                callback(false, null)
            }
        }
    }

    fun sendHeartbeat(heartbeat: DeviceHeartbeat, callback: (Boolean) -> Unit) {
        val body = gson.toJson(heartbeat)
        post("/api/v2/devices/heartbeat", body) { success, _ ->
            callback(success)
        }
    }

    // ==================== Command APIs ====================

    fun executeCommand(command: String, callback: (Boolean, Map<String, Any>?) -> Unit) {
        val body = gson.toJson(mapOf(
            "command" to command,
            "device_id" to getDeviceId()
        ))
        post("/api/v2/agents/execute", body) { success, response ->
            try {
                val json = gson.fromJson(response, Map::class.java)
                callback(success, json as? Map<String, Any>)
            } catch (e: Exception) {
                callback(false, null)
            }
        }
    }

    fun getInstalledApps(callback: (Boolean, List<Map<String, Any>>?) -> Unit) {
        get("/api/v2/devices/${getDeviceId()}/apps") { success, response ->
            try {
                val json = gson.fromJson(response, Map::class.java)
                @Suppress("UNCHECKED_CAST")
                val apps = json["apps"] as? List<Map<String, Any>>
                callback(success, apps)
            } catch (e: Exception) {
                callback(false, null)
            }
        }
    }

    // ==================== HTTP Helpers ====================

    private fun post(path: String, body: String, callback: (Boolean, String) -> Unit) {
        val requestBody = body.toRequestBody("application/json".toMediaTypeOrNull())
        val request = Request.Builder()
            .url("${getBaseUrl()}$path")
            .post(requestBody)
            .build()

        client.newCall(request).enqueue(object : Callback {
            override fun onFailure(call: Call, e: IOException) {
                callback(false, "{\"success\":false,\"message\":\"${e.message}\"}")
            }

            override fun onResponse(call: Call, response: Response) {
                val responseBody = response.body?.string() ?: "{\"success\":false,\"message\":\"Empty response\"}"
                callback(response.isSuccessful, responseBody)
            }
        })
    }

    private fun get(path: String, callback: (Boolean, String) -> Unit) {
        val request = Request.Builder()
            .url("${getBaseUrl()}$path")
            .get()
            .build()

        client.newCall(request).enqueue(object : Callback {
            override fun onFailure(call: Call, e: IOException) {
                callback(false, "{\"success\":false,\"message\":\"${e.message}\"}")
            }

            override fun onResponse(call: Call, response: Response) {
                val responseBody = response.body?.string() ?: "{\"success\":false,\"message\":\"Empty response\"}"
                callback(response.isSuccessful, responseBody)
            }
        })
    }
}
