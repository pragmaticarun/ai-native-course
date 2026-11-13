plugins {
    alias(libs.plugins.kotlin.multiplatform)
    alias(libs.plugins.kotlin.serialization)
    alias(libs.plugins.android.kmp.library)
}

kotlin {
    jvmToolchain(21)
    // JVM target runs the commonMain tests in CI. The Android target (added 14 Nov 2026 after the
    // owner approved the Android SDK) builds the same code as an Android library and runs the
    // commonTest suite as host tests; device backends live in projects/p6.
    jvm()
    android {
        namespace = "course.shared"
        compileSdk = libs.versions.compileSdk.get().toInt()
        minSdk = libs.versions.minSdk.get().toInt()
        withHostTest {}
    }

    sourceSets {
        commonMain.dependencies {
            implementation(libs.coroutines.core)
            implementation(libs.serialization.json)
            implementation(libs.mcp.server)
        }
        commonTest.dependencies {
            implementation(kotlin("test"))
            implementation(libs.coroutines.test)
            implementation(libs.mcp.client)
            implementation(libs.mcp.testing)
        }
    }
}
