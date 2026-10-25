# Automatic Windows setup

Download the standalone Windows executable from Releases. The only computer prerequisite is a supported Windows 10/11 x64 installation with the built-in .NET Framework. Python, pip, a separate ADB installation and PATH changes are not required for this route.

## What happens

1. The executable unpacks its embedded CLI and verified Android APK into a private per-user setup directory.
2. It probes Python installations registered for the user/machine and available on PATH. Python 3.11+ is reused. Windows Store placeholder executables are skipped.
3. It probes ADB on PATH and in common Android SDK locations.
4. Missing tools are downloaded from pinned official URLs in `windows/tools.json`. Python's portable runtime uses the checksum from its official release manifest. ADB's pinned package was checked against Google's repository metadata; a SHA-256 is pinned here for subsequent downloads.
5. Verified archives are extracted with path traversal checks. Matching cached tools are reused without overwriting running binaries. No administrator elevation or global environment change is performed.
6. The app checks local mDNS ADB advertisements and already-connected network devices. It prefers a device's port-5555 endpoint over a duplicate TLS advertisement. This is discovery, not a subnet scan. The Python installer still verifies Fire OS/API before changing any TV settings.
7. Setup waits for the TV's debugging authorization, installs the APKs, enables the required services while keeping unrelated services, and opens Home on Fire for its one-time target selection.

ADB debugging and computer authorization remain TV-owner actions. Setup cannot grant itself those permissions. Modern wireless pairing codes, if your device requires them, are not automated. Multiple advertised devices require a selection; if the TV does not advertise, its IP must be entered.

## Files and privacy

Under `%LOCALAPPDATA%\ClearHome`:

- `Downloads/`: checksum-verified tool ZIPs.
- `Tools/`: private Python/ADB copies, only when existing compatible tools were unavailable.
- `Setup/`: embedded versioned setup payloads.
- `State/`: recovery records, kept independently of the executable and payload version.

The executable does not upload diagnostics, TV addresses, backups, identifiers or account data. It accesses official tool download sites and the pinned GitHub APK releases. Python and Android Platform Tools are downloaded separately under their respective terms and retain their included notices.

## Cancel and retry

Cancel stops the active child/download. An ADB action already submitted to the TV may complete; setup journals owned changes before mutation. Reopen setup and use **Undo setup** if needed. Closing the window while work is active requests cancellation and leaves it open until the current task exits. The app does not reboot the TV or test Sleep automatically.

The Windows executable is unsigned; the Android APK retains its maintainer signature. No signing certificate or signing key is embedded in the executable. Organization policies can restrict unsigned applications; this project does not disable or bypass Windows security controls.

## Build and test

```text
python tools/build_windows.py
```

The compiler is Windows' .NET Framework C# compiler; the build needs no NuGet dependency. The APK must match `release-manifest.json`. For CI, `--test-payload` builds a binary that can run self-tests but refuses to start the installer. `--self-test REPORT_PATH` exercises argument quoting, discovery parsing, checksum failure, cache checks, archive boundaries, cancellation and child-process timeouts.

Windows host setup v0.3.0 deliberately reuses the v0.2.0 Android APK. The TV UI and app signing lineage are unchanged.
