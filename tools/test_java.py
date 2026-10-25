#!/usr/bin/env python3
"""Run domain tests without Android, JUnit or network downloads."""
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parents[1]
build = root / "build"
build.mkdir(exist_ok=True)
with tempfile.TemporaryDirectory(prefix="java-tests-", dir=build) as directory:
    subprocess.run(["javac", "-d", directory,
                    str(root / "app/src/local/firetv/sleep/FavoriteOrder.java"),
                    str(root / "tests/FavoriteOrderTest.java")], check=True)
    subprocess.run(["java", "-cp", directory, "local.firetv.sleep.FavoriteOrderTest"], check=True)
