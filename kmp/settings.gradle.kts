rootProject.name = "ai-native-course-kmp"

pluginManagement {
    repositories {
        gradlePluginPortal()
        mavenCentral()
        google()
    }
}

dependencyResolutionManagement {
    repositories {
        mavenCentral()
        google()
    }
}

include(":shared")
// P6 "Field Notes" lives under projects/p6 with the other projects; the build is wired here.
include(":p6-agent")
project(":p6-agent").projectDir = file("../projects/p6/agent")
include(":p6-app")
project(":p6-app").projectDir = file("../projects/p6/app")
