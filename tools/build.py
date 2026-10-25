#!/usr/bin/env python3
"""Build the native APK with Android SDK tools, without Gradle or network dependencies."""
import argparse
import hashlib
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def run(command, env=None):
    # Windows SDK .bat wrappers require cmd; subprocess handles them without shell=True.
    subprocess.run([str(value) for value in command], check=True, env=env)


def build(args):
    sdk = Path(args.sdk).expanduser()
    tools = sdk / "build-tools" / args.build_tools
    jar = sdk / "platforms" / args.platform / "android.jar"
    def tool(name):
        suffix = ".bat" if name in ("d8", "apksigner") else ".exe"
        return tools / (name + suffix if os.name == "nt" else name)
    for path in (jar, tool("aapt"), tool("d8"), tool("zipalign"), tool("apksigner")):
        if not path.is_file():
            raise SystemExit("Missing SDK file: " + str(path))
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    workspace = ROOT / "build"
    workspace.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="apk-", dir=workspace) as temporary:
        temp = Path(temporary)
        classes = temp / "classes"
        dex = temp / "dex"
        classes.mkdir()
        dex.mkdir()
        run([tool("aapt"), "package", "-f", "-M", ROOT / "app/AndroidManifest.xml", "-S", ROOT / "app/res",
             "-I", jar, "-F", temp / "resources.apk"])
        run(["javac", "-encoding", "UTF-8", "-source", "8", "-target", "8", "-bootclasspath", jar,
             "-d", classes] + sorted((ROOT / "app/src").rglob("*.java")))
        run([tool("d8"), "--min-api", "28", "--lib", jar, "--output", dex] + sorted(classes.rglob("*.class")))
        shutil.copyfile(temp / "resources.apk", temp / "unsigned.apk")
        with zipfile.ZipFile(temp / "unsigned.apk", "a", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.write(dex / "classes.dex", "classes.dex")
        run([tool("zipalign"), "-f", "4", temp / "unsigned.apk", temp / "aligned.apk"])
        env = os.environ.copy()
        keystore = args.keystore
        alias = args.alias
        password_args = []
        if args.debug:
            keystore = temp / "debug.p12"
            alias = "debug"
            env["CLEAR_HOME_BUILD_PASSWORD"] = secrets.token_urlsafe(32)
            run(["keytool", "-genkeypair", "-keystore", keystore, "-storetype", "PKCS12", "-alias", alias,
                 "-keyalg", "RSA", "-keysize", "3072", "-validity", "30", "-dname", "CN=Clear Home CI Debug",
                 "-storepass:env", "CLEAR_HOME_BUILD_PASSWORD"], env)
            password_args = ["--ks-pass", "env:CLEAR_HOME_BUILD_PASSWORD"]
        elif os.environ.get("CLEAR_HOME_KEYSTORE_PASSWORD"):
            password_args = ["--ks-pass", "env:CLEAR_HOME_KEYSTORE_PASSWORD"]
        if not keystore or not alias:
            raise SystemExit("Provide --keystore and --alias, or use --debug for a disposable development build.")
        run([tool("apksigner"), "sign", "--ks", keystore, "--ks-key-alias", alias] + password_args +
            ["--out", output, temp / "aligned.apk"], env)
        run([tool("apksigner"), "verify", "--verbose", output])
    print(hashlib.sha256(output.read_bytes()).hexdigest() + "  " + output.name)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sdk", default=os.environ.get("ANDROID_HOME", os.environ.get("ANDROID_SDK_ROOT", "")))
    parser.add_argument("--build-tools", default="36.0.0")
    parser.add_argument("--platform", default="android-36")
    parser.add_argument("--keystore")
    parser.add_argument("--alias")
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--output", default=str(ROOT / "artifacts/ClearHome.apk"))
    build(parser.parse_args())
