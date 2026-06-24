package com.apaos.agent.services

import android.app.Activity
import android.app.Service
import android.content.Context
import android.content.Intent
import android.graphics.Bitmap
import android.graphics.PixelFormat
import android.hardware.display.DisplayManager
import android.hardware.display.VirtualDisplay
import android.media.ImageReader
import android.media.projection.MediaProjection
import android.media.projection.MediaProjectionManager
import android.os.Build
import android.os.Environment
import android.os.IBinder
import android.util.DisplayMetrics
import android.util.Log
import android.view.WindowManager
import java.io.File
import java.io.FileOutputStream
import java.text.SimpleDateFormat
import java.util.*

class ScreenCaptureService : Service() {

    companion object {
        private const val TAG = "ScreenCaptureService"
        private const val VIRTUAL_DISPLAY_NAME = "APA-ScreenCapture"
        private const val NOTIFICATION_ID = 1002
        private const val SCREENSHOT_DIR = "APA_Screenshots"

        var instance: ScreenCaptureService? = null
            private set
        var isRunning = false
            private set
        var resultCode: Int = Activity.RESULT_CANCELED
        var resultData: Intent? = null
    }

    private var mediaProjection: MediaProjection? = null
    private var virtualDisplay: VirtualDisplay? = null
    private var imageReader: ImageReader? = null
    private var screenWidth = 1080
    private var screenHeight = 1920
    private var screenDensity = 0

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onCreate() {
        super.onCreate()
        instance = this

        val wm = getSystemService(Context.WINDOW_SERVICE) as WindowManager
        val metrics = DisplayMetrics()
        @Suppress("DEPRECATION")
        wm.defaultDisplay.getMetrics(metrics)
        screenWidth = metrics.widthPixels
        screenHeight = metrics.heightPixels
        screenDensity = metrics.densityDpi
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (intent?.action == "CAPTURE") {
            startCapture()
        }
        return START_NOT_STICKY
    }

    private fun startCapture() {
        try {
            val projectionManager = getSystemService(MEDIA_PROJECTION_SERVICE) as MediaProjectionManager
            mediaProjection = projectionManager.getMediaProjection(resultCode, resultData!!)

            imageReader = ImageReader.newInstance(
                screenWidth, screenHeight, PixelFormat.RGBA_8888, 2
            )

            virtualDisplay = mediaProjection?.createVirtualDisplay(
                VIRTUAL_DISPLAY_NAME,
                screenWidth, screenHeight, screenDensity,
                DisplayManager.VIRTUAL_DISPLAY_FLAG_AUTO_MIRROR,
                imageReader?.surface,
                null, null
            )

            isRunning = true
            Log.d(TAG, "Screen capture started")
        } catch (e: Exception) {
            Log.e(TAG, "Failed to start capture", e)
        }
    }

    fun captureScreenshot(callback: (String?) -> Unit) {
        try {
            val image = imageReader?.acquireLatestImage()
            if (image != null) {
                val plane = image.planes[0]
                val buffer = plane.buffer
                val pixelStride = plane.pixelStride
                val rowStride = plane.rowStride
                val rowPadding = rowStride - pixelStride * screenWidth

                val bitmap = Bitmap.createBitmap(
                    screenWidth + rowPadding / pixelStride,
                    screenHeight,
                    Bitmap.Config.ARGB_8888
                )
                bitmap.copyPixelsFromBuffer(buffer)

                val croppedBitmap = Bitmap.createBitmap(bitmap, 0, 0, screenWidth, screenHeight)
                bitmap.recycle()

                val filepath = saveScreenshot(croppedBitmap)
                croppedBitmap.recycle()
                image.close()

                callback(filepath)
            } else {
                callback(null)
            }
        } catch (e: Exception) {
            Log.e(TAG, "Screenshot failed", e)
            callback(null)
        }
    }

    private fun saveScreenshot(bitmap: Bitmap): String {
        val dir = File(getExternalFilesDir(Environment.DIRECTORY_PICTURES), SCREENSHOT_DIR)
        if (!dir.exists()) dir.mkdirs()

        val timestamp = SimpleDateFormat("yyyyMMdd_HHmmss", Locale.US).format(Date())
        val file = File(dir, "APA_$timestamp.png")

        FileOutputStream(file).use { out ->
            bitmap.compress(Bitmap.CompressFormat.PNG, 100, out)
        }

        Log.d(TAG, "Screenshot saved: ${file.absolutePath}")
        return file.absolutePath
    }

    fun stopCapture() {
        virtualDisplay?.release()
        imageReader?.close()
        mediaProjection?.stop()
        isRunning = false
    }

    override fun onDestroy() {
        stopCapture()
        instance = null
        super.onDestroy()
        Log.d(TAG, "Screen capture service destroyed")
    }
}
