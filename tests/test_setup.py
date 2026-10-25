import argparse
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("clear_home_setup", ROOT / "setup.py")
setup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(setup)


class FakeAdb:
    def __init__(self, existing=False):
        self.settings = {("secure", "enabled_accessibility_services"): "org.reader/.Service",
                         ("secure", "accessibility_enabled"): "1"}
        self.settings.update({("global", key): None for key in setup.SCALES})
        self.packages = {setup.APP, setup.HELPER} if existing else set()
        self.calls = []
        self.fail_install = False

    def setting(self, namespace, key):
        return self.settings.get((namespace, key))

    def put(self, namespace, key, value):
        self.calls.append(("put", namespace, key, value))
        self.settings[namespace, key] = value

    def installed(self, package):
        return package in self.packages

    def shell(self, *tokens):
        self.calls.append(tokens)
        if tokens[:2] == ("dumpsys", "package"):
            return "android.permission.WRITE_SECURE_SETTINGS: granted=true" if setup.HELPER in self.packages else ""
        return ""

    def install(self, path):
        self.calls.append(("install", str(path)))
        if self.fail_install:
            raise setup.SetupError("simulated installation failure")
        self.packages.add(setup.HELPER if "home-on-fire" in str(path) else setup.APP)

    def run(self, *tokens):
        self.calls.append(tokens)
        if tokens[0] == "uninstall":
            self.packages.discard(tokens[1])
        return "Success"


class SetupTests(unittest.TestCase):
    def setUp(self):
        self.stdout = patch("sys.stdout", new_callable=io.StringIO)
        self.stdout.start()
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.state_path = self.root / "backup.json"
        self.profile = {"model": "AFT-test", "sdk": "30", "os": "Fire OS 8.1.8.5", "fingerprint": "a" * 64}
        self.args = argparse.Namespace(no_home_redirect=False, faster_animations=True,
                                       dry_run=False, remove_added_apps=False)
        self.asset_patch = patch.object(setup, "verified_asset", side_effect=lambda asset, local, cache: cache)
        self.asset_patch.start()

    def tearDown(self):
        self.stdout.stop()
        self.asset_patch.stop()
        self.temp.cleanup()

    def install(self, adb):
        setup.install(adb, self.args, self.profile, self.state_path)

    def test_compatibility_rejects_vega_and_old_or_unexpected_sdk(self):
        self.assertTrue(setup.compatible(self.profile))
        for os_name, sdk in (("Vega OS 1", "30"), ("Fire OS 6.7.1", "25"), ("Fire OS 8.1", "35")):
            profile = dict(self.profile, os=os_name, sdk=sdk)
            with self.assertRaises(setup.SetupError):
                setup.install(FakeAdb(), self.args, profile, self.state_path)
        self.assertFalse(self.state_path.exists())

    def test_service_merge_preserves_order_and_rejects_shell_payload(self):
        self.assertEqual(setup.merge_services("org.reader/.Service:org.reader/.Service", [setup.SLEEP]),
                         "org.reader/.Service:" + setup.SLEEP)
        with self.assertRaises(setup.SetupError):
            setup.services("org.reader/.Service;reboot")
        self.assertEqual(setup.merge_services("org.reader/org.reader.Service", ["org.reader/.Service"]),
                         "org.reader/org.reader.Service")

    def test_dry_run_has_no_mutations_or_backup(self):
        self.args.dry_run = True
        adb = FakeAdb()
        self.install(adb)
        self.assertEqual(adb.calls, [])
        self.assertFalse(self.state_path.exists())
        setup.verified_asset.assert_not_called()

    def test_repeat_install_keeps_first_backup(self):
        adb = FakeAdb()
        self.install(adb)
        first = json.loads(self.state_path.read_text())["settings"]
        self.install(adb)
        second = json.loads(self.state_path.read_text())["settings"]
        self.assertEqual(first, second)
        self.assertEqual(first["scales"][setup.SCALES[0]], None)
        self.assertEqual(adb.setting("secure", "enabled_accessibility_services").count(setup.SLEEP), 1)

    def test_restore_preserves_services_added_after_setup_and_removes_only_new_apps(self):
        adb = FakeAdb()
        self.install(adb)
        adb.settings["secure", "enabled_accessibility_services"] += ":org.new.reader/.Service"
        self.args.remove_added_apps = True
        setup.restore(adb, self.args, self.profile, self.state_path)
        self.assertEqual(adb.setting("secure", "enabled_accessibility_services"),
                         "org.reader/.Service:org.new.reader/.Service")
        self.assertEqual(adb.setting("secure", "accessibility_enabled"), "1")
        self.assertEqual(adb.packages, set())
        for key in setup.SCALES:
            self.assertIsNone(adb.setting("global", key))

    def test_restore_never_uninstalls_preexisting_apps_or_revokes_preexisting_grant(self):
        adb = FakeAdb(existing=True)
        self.install(adb)
        self.args.remove_added_apps = True
        setup.restore(adb, self.args, self.profile, self.state_path)
        self.assertEqual(adb.packages, {setup.APP, setup.HELPER})
        self.assertFalse(any(call[:2] == ("pm", "revoke") for call in adb.calls))

    def test_partial_install_has_recoverable_journal(self):
        adb = FakeAdb()
        adb.fail_install = True
        with self.assertRaises(setup.SetupError):
            self.install(adb)
        state = json.loads(self.state_path.read_text())
        self.assertEqual(state["phase"], "installing_app")
        self.assertEqual(state["settings"]["services"], "org.reader/.Service")
        setup.restore(adb, self.args, self.profile, self.state_path)

    def test_wrong_device_backup_stops_before_mutation(self):
        adb = FakeAdb()
        self.install(adb)
        adb.calls.clear()
        with self.assertRaises(setup.SetupError):
            setup.restore(adb, self.args, dict(self.profile, fingerprint="b" * 64), self.state_path)
        self.assertEqual(adb.calls, [])

    def test_no_home_redirect_installs_only_our_app(self):
        self.args.no_home_redirect = True
        adb = FakeAdb()
        self.install(adb)
        self.assertEqual(adb.packages, {setup.APP})
        self.assertNotIn(setup.REDIRECT, adb.setting("secure", "enabled_accessibility_services"))

    def test_new_install_after_restore_captures_new_baseline_and_archives_old(self):
        adb = FakeAdb()
        self.install(adb)
        setup.restore(adb, self.args, self.profile, self.state_path)
        adb.settings["global", setup.SCALES[0]] = "2.0"
        self.install(adb)
        state = json.loads(self.state_path.read_text())
        self.assertEqual(state["settings"]["scales"][setup.SCALES[0]], "2.0")
        self.assertEqual(len(list((self.root / "history").glob("*.json"))), 1)

    def test_preexisting_fully_qualified_service_is_not_owned_or_removed(self):
        adb = FakeAdb()
        full = setup.APP + "/" + setup.APP + ".SleepService"
        adb.settings["secure", "enabled_accessibility_services"] = full
        self.install(adb)
        setup.restore(adb, self.args, self.profile, self.state_path)
        self.assertEqual(adb.setting("secure", "enabled_accessibility_services"), full)

    def test_restore_original_absent_services_and_enabled_flag(self):
        adb = FakeAdb()
        adb.settings["secure", "enabled_accessibility_services"] = None
        adb.settings["secure", "accessibility_enabled"] = "0"
        self.install(adb)
        setup.restore(adb, self.args, self.profile, self.state_path)
        self.assertIsNone(adb.setting("secure", "enabled_accessibility_services"))
        self.assertEqual(adb.setting("secure", "accessibility_enabled"), "0")

    def test_restore_prepopulated_but_disabled_services_stays_disabled(self):
        adb = FakeAdb()
        adb.settings["secure", "accessibility_enabled"] = "0"
        self.install(adb)
        setup.restore(adb, self.args, self.profile, self.state_path)
        self.assertEqual(adb.setting("secure", "enabled_accessibility_services"), "org.reader/.Service")
        self.assertEqual(adb.setting("secure", "accessibility_enabled"), "0")

    def test_adb_uses_argument_list_and_quotes_remote_shell_tokens(self):
        adb = setup.Adb("adb", "192.168.1.50:5555")
        with patch.object(adb, "run", return_value="") as runner:
            adb.shell("settings", "put", "secure", "example", "value; reboot")
            self.assertEqual(runner.call_args.args, ("shell", "settings put secure example 'value; reboot'"))
        for device in ("-x", "192.168.1.50:99999", "host;reboot:5555"):
            with self.assertRaises(setup.SetupError):
                setup.Adb("adb", device)

    def test_local_checksum_mismatch_rejected(self):
        self.asset_patch.stop()
        path = self.root / "local.apk"
        path.write_bytes(b"changed")
        with self.assertRaises(setup.SetupError):
            setup.verified_asset({"sha256": "0" * 64}, path, self.root / "unused")
        expected = hashlib.sha256(path.read_bytes()).hexdigest()
        self.assertEqual(setup.verified_asset({"sha256": expected}, path, self.root / "unused"), path)


if __name__ == "__main__":
    unittest.main()
