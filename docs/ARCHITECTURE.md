# Architecture

## Android app

- `HomeActivity`: native remote-driven grid, library view, settings chooser and navigation lifecycle.
- `AppCatalog`: installed-app discovery and launch intents. No remote app catalog.
- `FavoriteOrder`: pure Java ordering, deduplication, validation and 30-item bound.
- `FavoriteStore`: local SharedPreferences/JSON persistence. Empty favourites stay empty; corrupt stored JSON falls back to the installed defaults.
- `SleepActivity`: private activity with a bounded wait for the OS-bound service and a clear failure state.
- `SleepService`: Android accessibility global lock-screen action. It subscribes to no events, cannot retrieve screen contents and requests no key interception.

The app manifest requests no application permissions. The accessibility service binding is restricted by Android's `BIND_ACCESSIBILITY_SERVICE`. No device administrator, root shell, network access, permanent background loop, analytics or in-app updater is used.

## Host setup

`setup.py` is a standard-library Python CLI. It uses argument-list subprocess execution, remote-shell quoting and bounded ADB timeouts. Installation proceeds as:

```text
connect and authorize → inspect Fire OS/API → first local snapshot
→ verify APK hashes → install APKs → journal owned changes
→ merge service list → optional animation change → open helper configuration
```

Recovery records live only in `.clear-home/`, which is ignored by Git. They contain a device-identity hash, model/software version, relevant prior settings, app-presence flags and a progress journal. They do not contain ADB private keys, account credentials, a full settings dump or raw hardware serials. Matching uses a serial/model hash so a changed TV network address does not invalidate recovery, while a different TV cannot receive the wrong backup.

The baseline is retained across reruns, including partial installs. Recovery reconciles owned changes with the current service list rather than replacing all accessibility settings. Previously installed app versions and other apps' private configuration are outside its rollback boundary.

## External integration

Home on Fire owns the Home-button and boot/wake redirect. The installer enables its service and grants its documented one-time `WRITE_SECURE_SETTINGS` permission. This permission is broader than Clear Home's Sleep service; use the pinned official helper or inspect/rebuild its source. The user selects the target in the helper UI. If the helper was already installed, setup does not downgrade/replace it or overwrite its preferences.

Amazon's launcher, settings, Appstore, streaming apps and update services remain enabled. Future Fire OS changes can affect redirection; direct app launch and manual recovery remain available.
