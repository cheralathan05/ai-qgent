-keepattributes Signature
-keepattributes *Annotation*
-keepattributes SourceFile,LineNumberTable

-keep class com.apaos.agent.** { *; }
-keep class kotlin.Metadata { *; }

# OkHttp
-dontwarn okhttp3.**
-dontwarn okio.**
-keep class okhttp3.** { *; }

# Gson
-keepattributes Signature
-keepattributes *Annotation*
-keep class com.google.gson.** { *; }
-keep class * implements com.google.gson.TypeAdapterFactory
-keep class * implements com.google.gson.JsonSerializer
-keep class * implements com.google.gson.JsonDeserializer

# Kotlin Coroutines
-keepnames class kotlinx.coroutines.internal.MainDispatcherFactory {}
-keepnames class kotlinx.coroutines.CoroutineExceptionHandler {}
-keepclassmembers class kotlinx.coroutines.** {
    volatile <fields>;
}

# Keep data classes for Gson
-keep class com.apaos.agent.network.* { *; }
-keep class com.apaos.agent.core.* { *; }
