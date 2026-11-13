// P6 agent module: Koog agent in commonMain, run on the JVM in CI and on Android via androidMain.
// Pick the variant with -Pp6.variant=starter|solution (default solution), like PROJECT_VARIANT for Python.
plugins {
    alias(libs.plugins.kotlin.multiplatform)
    alias(libs.plugins.kotlin.serialization)
    alias(libs.plugins.android.kmp.library)
}

val variant = (findProperty("p6.variant") as String?) ?: "solution"
require(variant == "solution" || variant == "starter") { "p6.variant must be solution or starter" }

kotlin {
    jvmToolchain(21)
    jvm()
    android {
        namespace = "course.fieldnotes.agent"
        compileSdk = libs.versions.compileSdk.get().toInt()
        minSdk = libs.versions.minSdk.get().toInt()
        withHostTest {}
    }

    sourceSets {
        commonMain {
            kotlin.srcDirs("../common/src/commonMain/kotlin", "../$variant/src/commonMain/kotlin")
            dependencies {
                implementation(libs.coroutines.core)
                implementation(libs.serialization.json)
                api(libs.koog.agents)
            }
        }
        commonTest {
            kotlin.srcDir("../evals/src/commonTest/kotlin")
            dependencies {
                implementation(kotlin("test"))
                implementation(libs.coroutines.test)
                implementation(libs.koog.test)
            }
        }
        androidMain {
            kotlin.srcDir("../common/src/androidMain/kotlin")
            dependencies {
                implementation(libs.litertlm.android)
                implementation(libs.koog.litert)
            }
        }
    }
}

tasks.withType<Test>().configureEach {
    testLogging { events("passed", "failed"); showStandardStreams = true }
}
