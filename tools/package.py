#!/usr/bin/env python3
"""Package tracked source plus the verified signed APK; never include local backups/keys."""
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
manifest = json.loads((ROOT / "release-manifest.json").read_text(encoding="utf-8"))
apk = ROOT / "artifacts/ClearHome.apk"
apk_hash = hashlib.sha256(apk.read_bytes()).hexdigest()
if apk_hash != manifest["clear_home"]["sha256"]:
    raise SystemExit("APK does not match the pinned release manifest.")
tracked = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).decode().split("\0")
archive_path = ROOT / "artifacts" / ("ClearHome-Setup-v" + manifest["version"] + ".zip")
with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
    for name in filter(None, tracked):
        path = ROOT / name
        if (not path.resolve().is_relative_to(ROOT) or ".clear-home" in path.parts
                or path.suffix.lower() in (".p12", ".jks", ".keystore", ".key", ".pem", ".apk", ".idsig")
                or ".env" == path.name or "__pycache__" in path.parts):
            raise SystemExit("Refusing to package a private or unexpected tracked path: " + name)
        archive.write(path, name)
    archive.write(apk, "artifacts/ClearHome.apk")
archive_hash = hashlib.sha256(archive_path.read_bytes()).hexdigest()
(ROOT / "artifacts/SHA256SUMS.txt").write_text(
    apk_hash + "  ClearHome.apk\n" + archive_hash + "  " + archive_path.name + "\n", encoding="utf-8")
print(archive_path)
print("Verified tracked source and signed APK; local backups/signing keys excluded.")
