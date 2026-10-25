# Recovery and troubleshooting

## Setup stopped or was interrupted

Rerun the same command after fixing the reported connection/download issue. The first backup is kept. If you want to undo the recorded changes instead:

```text
python3 setup.py restore --device YOUR_TV_IP:5555
```

Use `py -3` on Windows. Pass the same `--state-dir` if you used a custom backup location. A dry run is available for install and restore.

## Cannot connect / unauthorized / wireless timeout

- Check the TV IP, same-network access and ADB Debugging.
- Accept the TV's authorization prompt yourself, then rerun.
- Some wireless transports stall after standby. `adb disconnect YOUR_TV_IP:5555`, then rerun setup/status to reconnect.
- Modern wireless pairing, if required by your device, must be completed using Google's ADB pairing instructions before running this installer. This installer does not automate pairing codes or authorize a computer on your behalf.
- A Fire OS remote-detection message is separate from Clear Home. Check remote batteries/pairing using the TV's instructions.

## Home goes to Amazon / redirection stops after an update

Open Home on Fire from the Amazon app list. Check that its accessibility service is enabled, its target is Clear Home and Replace Home/Launch on boot are enabled. A short flash is possible; Fire OS 7 has an additional upstream-documented app-switch delay. No firmware downgrade or update blocker is included.

## Sleep says its service is disabled

Rerun setup to re-enable the Sleep component while keeping unrelated accessibility services. The app does not silently grant itself permissions. Standby does not guarantee TV-panel power-off through HDMI-CEC.

On the tested Fire OS build, force-stopping Clear Home also removed its enabled accessibility-service entry. Rerun setup after force-stop; ordinary Home navigation and reboot do not require a computer to remain connected.

## Lost the backup

Hold Home to reach Amazon Home / quick settings, or open Home on Fire's configuration and turn off Replace Home. Disable **Sleep shortcut** and **Home on Fire** in the TV's accessibility settings if the device exposes those controls. Then uninstall Clear Home and, if it was newly installed for this setup, Home on Fire using Fire TV application settings.

If using ADB manually, first inspect:

```text
adb -s YOUR_TV_IP:5555 shell settings get secure enabled_accessibility_services
```

Remove only `local.firetv.sleep/.SleepService` and `io.github.toolicious.homeonfire/.HijackService` from that colon-separated list. Preserve any other entries. Do not paste a command that replaces the entire list with an empty value if you use other accessibility services. Without the backup, original animation values and whether the helper permission existed before setup cannot be inferred safely.

## Existing Home on Fire installation

The helper's private target/button configuration is changed only through its own UI. A backup cannot read or restore that private configuration. If it was already active and you selected Clear Home manually, select your previous launcher when undoing. Restoration preserves its pre-existing service and grant.

## APK cannot update an existing app

An Android signature mismatch means the installed copy was signed by another key (for example a debug build). Setup stops instead of uninstalling app data. Choose which build to keep; uninstalling Clear Home removes its local favourite selection. The signed public releases use a persistent maintainer key; rebuilding with your own key creates a separate update lineage.

## Share diagnostics carefully

Include Fire OS version, model, setup command with the network address removed, and the error message. Do not upload `.clear-home`, ADB keys, device serials, account details, full settings dumps or signing keys. Setup does not upload diagnostics.
