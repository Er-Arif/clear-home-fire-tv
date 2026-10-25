#!/usr/bin/env python3
"""Install Clear Home over ADB. Python 3.11+, standard library only."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request

ROOT = Path(__file__).resolve().parent
APP = "local.firetv.sleep"
HELPER = "io.github.toolicious.homeonfire"
SLEEP = APP + "/.SleepService"
REDIRECT = HELPER + "/.HijackService"
SCALES = ("window_animation_scale", "transition_animation_scale", "animator_duration_scale")
COMPONENT = re.compile(r"^[A-Za-z0-9_.$]+/[A-Za-z0-9_.$]+$")


class SetupError(RuntimeError):
    pass


def services(value):
    result = []
    seen = set()
    for component in (value or "").split(":"):
        if component in ("", "null"):
            continue
        if not COMPONENT.fullmatch(component):
            raise SetupError("Device returned an invalid accessibility component; refusing to overwrite it.")
        key = component_key(component)
        if key not in seen:
            result.append(component)
            seen.add(key)
    return result


def component_key(component):
    package, name = component.split("/", 1)
    return package + "/" + (package + name if name.startswith(".") else name)


def merge_services(original, additions):
    result = services(original)
    seen = {component_key(entry) for entry in result}
    for component in additions:
        if component_key(component) not in seen:
            result.append(component)
            seen.add(component_key(component))
    return ":".join(result)


def compatible(profile):
    match = re.search(r"Fire OS ([78])\.", profile["os"], re.IGNORECASE)
    return bool(match and profile["sdk"] == {"7": "28", "8": "30"}[match.group(1)])


def fingerprint(serial, model):
    if not serial or serial.lower() in ("null", "unknown"):
        raise SetupError("Cannot identify this device reliably. No settings were changed.")
    return hashlib.sha256((serial + "\n" + model).encode()).hexdigest()


def atomic_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix="state-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(data, stream, indent=2)
            stream.write("\n")
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


class Adb:
    def __init__(self, executable, device, authorization_timeout=0):
        if not re.fullmatch(r"[A-Za-z0-9.-]+:[0-9]{1,5}", device or ""):
            raise SetupError("Use the Fire TV address in IP:port form, for example 192.168.1.50:5555.")
        if not 1 <= int(device.rsplit(":", 1)[1]) <= 65535:
            raise SetupError("Invalid ADB port.")
        self.executable = executable
        self.device = device
        self.authorization_timeout = authorization_timeout

    def run(self, *arguments, timeout=30, device=True):
        command = [self.executable] + (["-s", self.device] if device else []) + list(arguments)
        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=timeout,
                                    encoding="utf-8", errors="replace")
        except subprocess.TimeoutExpired as error:
            raise SetupError("ADB timed out. Reconnect the TV and rerun; an existing backup will be kept.") from error
        except OSError as error:
            raise SetupError("ADB could not run. Install Google's Platform Tools or pass --adb PATH.") from error
        output = (result.stdout + "\n" + result.stderr).strip()
        if result.returncode:
            raise SetupError("ADB failed: " + output[-1500:])
        return output

    def connect(self):
        try:
            self.run("connect", self.device, device=False)
        except SetupError as error:
            message = str(error).lower()
            if "authenticate" not in message and "unauthorized" not in message:
                raise
            # A first connection can exit nonzero while the approval dialog is open.
            # Keep waiting on that transport instead of forcing the user to restart.
        deadline = time.monotonic() + self.authorization_timeout
        announced = False
        while True:
            try:
                if self.run("get-state", timeout=8).strip() != "device":
                    raise SetupError("The ADB transport is not ready.")
                return
            except SetupError as error:
                if not self.authorization_timeout or time.monotonic() >= deadline:
                    raise SetupError("Approve 'Allow USB debugging?' on the TV, then retry. "
                                     "Check ADB debugging and the network address if no prompt appears.") from error
                if not announced:
                    print("Waiting for the TV: accept 'Allow USB debugging?' on its screen. Setup will continue automatically.", flush=True)
                    announced = True
                time.sleep(2)

    def shell(self, *tokens):
        # ADB shell joins arguments remotely: quote each token for Android's shell.
        return self.run("shell", " ".join(shlex.quote(str(token)) for token in tokens))

    def setting(self, namespace, key):
        value = self.shell("settings", "get", namespace, key).strip()
        return None if value == "null" else value

    def put(self, namespace, key, value):
        if value is None:
            self.shell("settings", "delete", namespace, key)
        else:
            self.shell("settings", "put", namespace, key, value)
        if self.setting(namespace, key) != value:
            raise SetupError("Fire OS did not retain setting " + key + ". Keep the backup and use restore.")

    def installed(self, package):
        return "package:" + package in self.shell("pm", "list", "packages", package).splitlines()

    def profile(self):
        get = lambda key: self.shell("getprop", key).strip()
        profile = {"model": get("ro.product.model"), "sdk": get("ro.build.version.sdk"),
                   "os": get("ro.build.version.name")}
        serial = get("ro.serialno") or get("ro.boot.serialno")
        profile["fingerprint"] = fingerprint(serial, profile["model"])
        return profile

    def install(self, path):
        output = self.run("install", "-r", str(path), timeout=120)
        if "Success" not in output:
            raise SetupError("APK installation did not succeed: " + output[-1000:])


def verified_asset(asset, local, cache):
    expected = asset["sha256"]
    if not re.fullmatch(r"[0-9a-f]{64}", expected):
        raise SetupError("Invalid release checksum.")
    target = local if local and local.is_file() else cache
    if not target.is_file():
        if not asset["url"].startswith("https://github.com/"):
            raise SetupError("Release downloads must use HTTPS GitHub URLs.")
        target.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary = tempfile.mkstemp(prefix="download-", dir=target.parent)
        os.close(descriptor)
        try:
            request = urllib.request.Request(asset["url"], headers={"User-Agent": "ClearHome-Setup/0.2"})
            with urllib.request.urlopen(request, timeout=60) as response, open(temporary, "wb") as stream:
                total = 0
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > 100 * 1024 * 1024:
                        raise SetupError("Unexpectedly large APK download.")
                    stream.write(chunk)
            if hashlib.sha256(Path(temporary).read_bytes()).hexdigest() != expected:
                raise SetupError("Download checksum mismatch; nothing from that file was installed.")
            os.replace(temporary, target)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
    if hashlib.sha256(target.read_bytes()).hexdigest() != expected:
        raise SetupError("Checksum mismatch for " + str(target) + ". Remove that download and retry.")
    return target


def snapshot(adb, profile):
    current_services = adb.setting("secure", "enabled_accessibility_services")
    services(current_services)  # Reject malformed values before recording any mutations.
    installed = {APP: adb.installed(APP), HELPER: adb.installed(HELPER)}
    permission = installed[HELPER] and "android.permission.WRITE_SECURE_SETTINGS: granted=true" in adb.shell("dumpsys", "package", HELPER)
    return {"schema": 1, "profile": profile, "settings": {
        "services": current_services,
        "accessibility_enabled": adb.setting("secure", "accessibility_enabled"),
        "scales": {key: adb.setting("global", key) for key in SCALES}},
        "installed_before": installed,
        "helper_permission_before": bool(permission),
        "managed_services": [], "changed_scales": False, "helper_grant_managed": False,
        "installed_by_setup": [], "phase": "backed_up"}


def load_state(path, profile):
    state = json.loads(path.read_text(encoding="utf-8"))
    if state.get("schema") != 1 or state.get("profile", {}).get("fingerprint") != profile["fingerprint"]:
        raise SetupError("Backup does not belong to this device or uses an unsupported format.")
    return state


def install(adb, args, profile, state_path):
    if not compatible(profile):
        raise SetupError("Automatic setup supports Android-based Fire OS 7 (API 28) or 8 (API 30) only. "
                         "Vega OS and older Fire OS are not supported.")
    plan = "Install Clear Home; enable its Sleep service"
    if not args.no_home_redirect:
        plan += "; install Home on Fire if missing; enable its service"
    if args.faster_animations:
        plan += "; set three animation scales to 0.5"
    print(plan + ".")
    if args.dry_run:
        print("Dry run: no downloads, installations, settings changes or backup writes.")
        return
    state = load_state(state_path, profile) if state_path.exists() else snapshot(adb, profile)
    if state["phase"] == "restored":
        atomic_json(state_path.parent / "history" / (state_path.stem + "-" + str(time.time_ns()) + ".json"), state)
        state = snapshot(adb, profile)
    atomic_json(state_path, state)  # First backup is never replaced with an already-modified baseline.
    print("Recovery backup: " + str(state_path))
    manifest = json.loads((ROOT / "release-manifest.json").read_text(encoding="utf-8"))
    cache = state_path.parent / "downloads"
    apk = verified_asset(manifest["clear_home"], ROOT / "artifacts" / "ClearHome.apk", cache / "ClearHome.apk")
    # Record ownership before an action so an interrupted install remains recoverable.
    if not state["installed_before"][APP] and APP not in state["installed_by_setup"]:
        state["installed_by_setup"].append(APP)
    state["phase"] = "installing_app"
    atomic_json(state_path, state)
    adb.install(apk)
    additions = [SLEEP]
    if not args.no_home_redirect:
        if not adb.installed(HELPER):
            helper_apk = verified_asset(manifest["home_on_fire"], None, cache / "home-on-fire.apk")
            if not state["installed_before"][HELPER] and HELPER not in state["installed_by_setup"]:
                state["installed_by_setup"].append(HELPER)
            atomic_json(state_path, state)
            adb.install(helper_apk)
        if not state["helper_permission_before"]:
            state["helper_grant_managed"] = True
            atomic_json(state_path, state)
        adb.shell("pm", "grant", HELPER, "android.permission.WRITE_SECURE_SETTINGS")
        additions.append(REDIRECT)
    before = {component_key(entry) for entry in services(state["settings"]["services"])}
    for component in additions:
        if component_key(component) not in before and component not in state["managed_services"]:
            state["managed_services"].append(component)
    state["phase"] = "enabling_services"
    atomic_json(state_path, state)
    adb.put("secure", "enabled_accessibility_services",
            merge_services(adb.setting("secure", "enabled_accessibility_services"), additions))
    adb.put("secure", "accessibility_enabled", "1")
    if args.faster_animations:
        state["changed_scales"] = True
        atomic_json(state_path, state)
        for key in SCALES:
            adb.put("global", key, "0.5")
    state["phase"] = "installed"
    atomic_json(state_path, state)
    if args.no_home_redirect:
        adb.shell("am", "start", "-n", APP + "/.HomeActivity")
    else:
        adb.shell("am", "start", "-n", HELPER + "/.MainActivity")
        print("ON THE TV: choose Clear Home as the target. Keep Replace Home, Launch on boot, "
              "and the long-press Home escape enabled. Existing helper settings are not overwritten.")
    print("Done. In Clear Home, hold OK on an app to add/remove a favourite. "
          "No streaming app, system package, or update service was removed.")


def restore(adb, args, profile, state_path):
    if not state_path.is_file():
        raise SetupError("No matching local backup found. See docs/RECOVERY.md for manual recovery.")
    state = load_state(state_path, profile)
    current = services(adb.setting("secure", "enabled_accessibility_services"))
    # Keep unrelated services added since setup, too; never restore the whole list blindly.
    owned = {component_key(entry) for entry in state["managed_services"]}
    remaining = [entry for entry in current if component_key(entry) not in owned]
    for entry in services(state["settings"]["services"]):
        if component_key(entry) not in {component_key(value) for value in remaining}:
            remaining.append(entry)
    if args.dry_run:
        print("Dry run: restore owned service/animation/permission changes using " + str(state_path))
        return
    original_raw = state["settings"]["services"]
    target = ":".join(remaining) if remaining else original_raw
    original_keys = {component_key(entry) for entry in services(original_raw)}
    remaining_keys = {component_key(entry) for entry in remaining}
    enabled = (state["settings"]["accessibility_enabled"] if original_keys == remaining_keys
               else adb.setting("secure", "accessibility_enabled"))
    adb.put("secure", "enabled_accessibility_services", target)
    adb.put("secure", "accessibility_enabled", enabled)
    if state["changed_scales"]:
        for key, value in state["settings"]["scales"].items():
            adb.put("global", key, value)
    if state["helper_grant_managed"] and adb.installed(HELPER):
        adb.shell("pm", "revoke", HELPER, "android.permission.WRITE_SECURE_SETTINGS")
    if args.remove_added_apps:
        for package in state["installed_by_setup"]:
            if not state["installed_before"][package] and adb.installed(package):
                adb.run("uninstall", package)
    state["phase"] = "restored"
    atomic_json(state_path, state)
    adb.shell("input", "keyevent", "KEYCODE_HOME")
    print("Setup changes restored. Backup retained. Previously installed app versions/data are not rolled back.")
    if REDIRECT in services(state["settings"]["services"]):
        print("Home on Fire was already active before setup: select your previous target in its TV configuration.")


def find_adb(explicit):
    if explicit:
        return str(Path(explicit).expanduser().resolve())
    candidates = [shutil.which("adb")]
    for name in ("ANDROID_HOME", "ANDROID_SDK_ROOT"):
        if os.environ.get(name):
            candidates.append(str(Path(os.environ[name]) / "platform-tools" / ("adb.exe" if os.name == "nt" else "adb")))
    if os.name == "nt":
        candidates.append(str(Path(os.environ.get("LOCALAPPDATA", "")) / "Android/SDK/platform-tools/adb.exe"))
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return candidate
    raise SetupError("Install Google's Android Platform Tools, add adb to PATH, or use --adb PATH. "
                     "https://developer.android.com/tools/releases/platform-tools")


def main(argv=None):
    if sys.version_info < (3, 11):
        print("Python 3.11 or newer is required.", file=sys.stderr)
        return 1
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("install", "restore", "status"))
    parser.add_argument("--device", help="TV IP:port; asked interactively when omitted")
    parser.add_argument("--adb", help="Path to Google's adb executable")
    parser.add_argument("--wait-for-authorization", action="store_true", help="Wait up to two minutes for TV approval")
    parser.add_argument("--state-dir", type=Path, default=ROOT / ".clear-home", help="Local recovery backup directory")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--faster-animations", action="store_true", help="Opt in to 0.5 animation scales")
    parser.add_argument("--no-home-redirect", action="store_true", help="Install without Home on Fire")
    parser.add_argument("--remove-added-apps", action="store_true", help="Restore only: uninstall apps newly added by setup")
    args = parser.parse_args(argv)
    try:
        device = args.device or input("Fire TV address (for example 192.168.1.50:5555): ").strip()
        adb = Adb(find_adb(args.adb), device, 120 if args.wait_for_authorization else 0)
        adb.connect()
        profile = adb.profile()
        print(profile["model"] + " - " + profile["os"] + " / API " + profile["sdk"])
        state_path = args.state_dir.resolve() / (profile["fingerprint"][:16] + ".json")
        if args.action == "install":
            install(adb, args, profile, state_path)
        elif args.action == "restore":
            restore(adb, args, profile, state_path)
        else:
            print("Automatic setup compatible: " + str(compatible(profile)))
            print("Clear Home installed: " + str(adb.installed(APP)))
            print("Home on Fire installed: " + str(adb.installed(HELPER)))
            print("Enabled accessibility services: " + str(adb.setting("secure", "enabled_accessibility_services")))
        return 0
    except (SetupError, OSError, ValueError, EOFError) as error:
        print("Setup stopped: " + str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
