# Manual installation

These steps are for an already authorized ADB connection to a supported Fire OS 7/8 device. `TV` means the TV's `IP:port` address. Download the signed ClearHome.apk from this repository's Releases and verify SHA256SUMS.txt. Obtain the pinned Home on Fire APK from its official upstream release linked in `release-manifest.json`; verify its hash too.

```text
adb connect TV
adb -s TV install -r ClearHome.apk
adb -s TV install -r home-on-fire.apk
adb -s TV shell pm grant io.github.toolicious.homeonfire android.permission.WRITE_SECURE_SETTINGS
adb -s TV shell settings get secure enabled_accessibility_services
```

Before modifying anything, record the returned service list and `accessibility_enabled` value. Append these entries to the existing list, separated by colons, without duplicating or removing other entries:

```text
local.firetv.sleep/.SleepService
io.github.toolicious.homeonfire/.HijackService
```

Write the merged value with `settings put secure enabled_accessibility_services MERGED_LIST` and set `settings put secure accessibility_enabled 1`. Use the installer if you are not comfortable preserving that list manually.

```text
adb -s TV shell am start -n io.github.toolicious.homeonfire/.MainActivity
```

On the TV choose **Clear Home** as the target, and keep Replace Home / Launch on boot / long-press Home escape enabled. Press Home. Hold OK on apps to manage favourites.

To open the launcher directly:

```text
adb -s TV shell am start -n local.firetv.sleep/.HomeActivity
```

Without Home on Fire, this direct launch works as an ordinary app; Home/boot redirection is not configured. Without the Sleep accessibility service, the Sleep button shows a setup error rather than pretending the TV is asleep.
