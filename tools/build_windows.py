#!/usr/bin/env python3
"""Build the standalone Windows GUI with an embedded, checksum-verified setup payload."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--test-payload", action="store_true", help="CI-only build; installation is disabled")
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts/ClearHome-Windows-Setup.exe")
    args = parser.parse_args()
    if os.name != "nt":
        raise SystemExit("The Windows bootstrapper is compiled on Windows.")
    manifest = json.loads((ROOT / "release-manifest.json").read_text(encoding="utf-8"))
    build = ROOT / "build/windows"
    build.mkdir(parents=True, exist_ok=True)
    apk = ROOT / "artifacts/ClearHome.apk"
    if not args.test_payload:
        if not apk.is_file() or hashlib.sha256(apk.read_bytes()).hexdigest() != manifest["clear_home"]["sha256"]:
            raise SystemExit("Build Windows setup only with the APK matching release-manifest.json.")
    payload = build / "payload.zip"
    with zipfile.ZipFile(payload, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name in ("setup.py", "release-manifest.json", "LICENSE", "THIRD_PARTY_NOTICES.md", "windows/tools.json"):
            archive.write(ROOT / name, name)
        if args.test_payload:
            archive.writestr("TEST_ONLY", "This test build cannot install applications.")
        else:
            archive.write(apk, "artifacts/ClearHome.apk")
    assembly = build / "AssemblyInfo.cs"
    version = manifest["version"]
    assembly.write_text(
        'using System.Reflection;\n[assembly:AssemblyTitle("Clear Home for Fire TV Setup")]\n'
        '[assembly:AssemblyCompany("Arif Ali")]\n[assembly:AssemblyVersion("' + version + '.0")]\n'
        '[assembly:AssemblyFileVersion("' + version + '.0")]\n', encoding="utf-8")
    framework = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Microsoft.NET/Framework64/v4.0.30319"
    compiler = framework / "csc.exe"
    if not compiler.is_file():
        raise SystemExit("Windows .NET Framework 4.x compiler not found. Windows 10/11 with .NET Framework 4.8 is required.")
    references = ["System.dll", "System.Core.dll", "System.Drawing.dll", "System.Windows.Forms.dll",
                  "System.Net.Http.dll", "System.IO.Compression.dll", "System.Web.Extensions.dll"]
    args.output.resolve().parent.mkdir(parents=True, exist_ok=True)
    command = [str(compiler), "/nologo", "/target:winexe", "/platform:x64", "/optimize+",
               "/out:" + str(args.output.resolve()), "/win32manifest:" + str(ROOT / "windows/application.manifest"),
               "/resource:" + str(payload) + ",ClearHome.Payload"]
    command += ["/reference:" + str(framework / name) for name in references]
    command += [str(path) for path in sorted((ROOT / "windows").glob("*.cs"))] + [str(assembly)]
    subprocess.run(command, check=True)
    print(hashlib.sha256(args.output.read_bytes()).hexdigest() + "  " + args.output.name)


if __name__ == "__main__":
    main()
