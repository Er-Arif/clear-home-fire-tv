# Development and release

## Requirements

Python 3.11+, JDK 17+, Android SDK `platforms;android-36` and `build-tools;36.0.0`. `ANDROID_HOME` can point to the SDK. No Gradle or downloaded app runtime dependency is needed. The app targets API 30, supports API 28+, and is designed specifically for Fire TV in landscape.

```text
python3 -m unittest discover -s tests -v
python3 tools/test_java.py
python3 tools/build.py --sdk /path/to/sdk --debug
```

The debug key is generated temporarily and discarded. Never publish a debug APK as a release; its signature changes on every build. The CI workflow compiles and signature-checks a disposable debug artifact, not the public release.

## Signed build

Create and keep a private RSA signing keystore, then:

```text
python3 tools/build.py --sdk /path/to/sdk --keystore /private/maintainer.p12 --alias YOUR_ALIAS
```

`apksigner` prompts for the password. For controlled local/CI use, `CLEAR_HOME_KEYSTORE_PASSWORD` supplies it through an environment variable rather than a command argument. Keep that value out of logs and files under version control. Back up the keystore securely; losing it prevents signed updates to existing installations. No signing key or password is included in this repository.

## Release procedure

1. Run Python/Java tests and build with the maintainer's persistent key.
2. Test the app and installer on a supported device. Check main grid, favourite persistence, All Apps, app launch, settings, Sleep, wake and boot redirection. Test restore on a test device or with the simulated transport; do not erase an existing user's setup to test rollback.
3. Update `release-manifest.json` to the versioned release URL and the APK SHA-256.
4. Package `Setup.cmd`, `setup.py`, `release-manifest.json`, `LICENSE`, `README.md`, `docs/`, and `artifacts/ClearHome.apk` in a setup ZIP. Exclude `.clear-home`, signing keys, build directories and third-party APKs.
5. Publish the signed APK, setup ZIP and `SHA256SUMS.txt` as GitHub Release assets. Only publish what was verified; include compatibility limits in release notes.

## Extending the app

Keep domain ordering in `FavoriteOrder`, persistence in `FavoriteStore`, app lookup in `AppCatalog`, and Android UI/lifecycle in `HomeActivity`. Prefer native views and local state over online feeds. Existing installed apps should remain launchable through All Apps. Add tests for changes to ordering, setup state, ownership or recovery rules.

The package name `local.firetv.sleep` is retained for update compatibility with the original personal build. This is now the whole Clear Home app, not just a standalone sleep tile.
