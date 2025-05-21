plugins {
    id("com.android.application")
    // START: FlutterFire Configuration
    id("com.google.gms.google-services")
    // END: FlutterFire Configuration
    id("kotlin-android")
    id("dev.flutter.flutter-gradle-plugin")
}

android {
    namespace = "com.example.catalog_app"
    compileSdk = flutter.compileSdkVersion
    ndkVersion = "27.0.12077973" // NDK versiyonu burada düzeltildi

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_1_8
        targetCompatibility = JavaVersion.VERSION_1_8
        isCoreLibraryDesugaringEnabled = true // <-- BURADAKİ SATIR ÇOK ÖNEMLİ!
    }

    kotlinOptions {
        jvmTarget = "1.8"
    }

    defaultConfig {
        applicationId = "com.example.catalog_app"
        minSdk = flutter.minSdkVersion
        targetSdk = flutter.targetSdkVersion
        versionCode = flutter.versionCode
        versionName = flutter.versionName

        // Eğer hala hata alırsak, multidex'i de etkinleştirmeyi deneyebiliriz
        // multiDexEnabled = true // uncomment this if you encounter build errors related to method count or Java 8 features
    }

    buildTypes {
        release {
            signingConfig = signingConfigs.getByName("debug")
        }
    }
}

dependencies {
    // START: FlutterFire Configuration
    // Firebase BOM
    implementation(platform("com.google.firebase:firebase-bom:33.0.0")) // <-- Firebase BOM

    // Core library desugaring için
    coreLibraryDesugaring("com.android.tools:desugar_jdk_libs:2.0.4") // <-- Bu satırı değiştirdik!
    // END: FlutterFire Configuration

    // Eğer AndroidX ile ilgili hatalar alırsak aşağıdaki satırı da ekleyebiliriz
    // implementation("androidx.multidex:multidex:2.0.1") // Eğer multiDexEnabled = true yaparsak bu da lazım olabilir

    // Diğer bağımlılıklar buraya eklenebilir, örneğin:
    // implementation("androidx.core:core-ktx:1.13.1")
    // implementation("androidx.appcompat:appcompat:1.6.1")
}

flutter {
    source = "../.."
}