# Verification for v0.2.0

Date: 25 October 2026. Physical device: Amazon AFTKM (`karat`), Fire OS 8.1.8.5 (RS8185/3891), Android API 30.

## Automated checks

- 15 Python installer tests: compatibility refusal, argument/shell safety, checksum refusal, dry-run behavior, ownership tracking, first-backup preservation, partial-install recovery, wrong-device refusal, preservation of existing apps/permissions/services, canonical component names, disabled original services, and a fresh baseline after completed restoration.
- Seven pure Java favourite-order checks: valid package names, deduplication, stable order, add/remove, unchanged input, deliberate empty selection and a 30-item limit.
- Java compilation, Android DEX conversion, ZIP alignment and APK signature verification succeeded locally using JDK 17 / Android SDK 36 tools.
- The installer's download path fetched the pinned upstream Home on Fire v1.5.2 APK and verified its recorded SHA-256 successfully.

## Physical-device checks

- `install --dry-run` inspected the device without downloads, app/settings changes or backup writes.
- The real installer upgraded the existing signed personal build, preserved its ten-app layout and Home on Fire configuration, saved a recovery record, and read back enabled services and requested animation values.
- A favourite was removed from the main grid, confirmed absent after a process restart, added again from All Apps, and confirmed present after another process restart. The original ten-app selection was restored after this test.
- The visible Sleep control put the stick in standby after its service was enabled, and Home alone woke it back into Clear Home. A disabled service produces an explicit error state. Force-stop was observed to remove the Sleep accessibility entry on this firmware; the installer repairs it without removing unrelated services.
- The original personal build previously passed Netflix/YouTube launch, direct Network settings, Home return and full-device reboot/automatic-start tests with the same Home on Fire integration. The public release keeps those launch/redirect paths and adds persistent favourites.
- A fresh home-screen screenshot was captured from the public build.

Tests use ADB-injected remote-style/touch input and observed device state. The physical remote's pairing and TV-panel HDMI-CEC power-off were not independently tested. No account sign-in, purchase or video playback was performed. No claim is made that all streaming services or firmware versions were exercised.

## Recovery scope

Fresh-install and failure/restore scenarios were exercised with the simulated ADB transport, including unrelated services added after installation. The real restore was not run against the owner's existing customized TV because it would undo that setup. The real installer was tested as an upgrade/rerun, not as a factory-fresh-device installation.

Windows was the local build/install host. CI runs Python and Java tests on Windows and Linux and compiles a disposable Android debug APK on Linux. macOS host execution and Fire OS 7 remain unverified by this project.

There is no controlled before/after speed benchmark. Clear Home has no network permission, recommendations or downloaded wallpaper; optional 0.5 animation scales shorten transitions without changing CPU speed or streaming performance.

See GitHub Actions for the results associated with the published commit. Do not treat a successful build as universal device compatibility.
