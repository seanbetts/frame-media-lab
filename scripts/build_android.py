#!/usr/bin/env python3
"""Build platform-only Java APKs using an already installed SDK; never downloads."""

import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from lab.android_sdk import find_sdk  # noqa: E402

MODULES = ("flatscreen-test", "diagnostics", "media-test")


def java_bootclasspath(sdk):
    # javac needs the SDK's lambda bootstrap stubs; D8 desugars the lambdas.
    # These compile-only stubs must never be packaged as app classes.
    return os.pathsep.join(
        str(p)
        for p in (
            sdk / "platforms/android-35/android.jar",
            sdk / "build-tools/35.0.0/core-lambda-stubs.jar",
        )
    )


def prerequisites(sdk):
    errors = []
    if sdk is None or not (sdk / "platforms/android-35/android.jar").is_file():
        errors.append(
            "Android SDK platform missing: install platforms;android-35 in an SDK you choose, then set ANDROID_HOME or pass --sdk."
        )
    for name in ("java", "javac", "keytool", "jar"):
        if shutil.which(name) is None:
            errors.append("JDK 17 tool missing from PATH: " + name)
    if sdk is None or not (sdk / "build-tools/35.0.0").is_dir():
        errors.append(
            "Android SDK build tools missing: install build-tools;35.0.0 using sdkmanager (no installation is performed here)."
        )
    else:
        for tool in ("aapt2", "d8", "zipalign", "apksigner", "core-lambda-stubs.jar"):
            if not (sdk / "build-tools/35.0.0" / tool).is_file():
                errors.append("Missing SDK build component: " + tool)
    return errors


def run(argv, env, cwd):
    subprocess.run([str(a) for a in argv], cwd=cwd, env=env, check=True, timeout=180)


def build(sdk):
    out = ROOT / "build/android"
    out.mkdir(parents=True, exist_ok=True)
    private = out / "private"
    private.mkdir(exist_ok=True, mode=0o700)
    temp = out / "tmp"
    temp.mkdir(exist_ok=True)
    env = dict(
        os.environ,
        GRADLE_USER_HOME=str(out / "gradle"),
        ANDROID_USER_HOME=str(private),
        TMPDIR=str(temp),
        JAVA_TOOL_OPTIONS="-Duser.home="
        + str(private)
        + " -Djava.io.tmpdir="
        + str(temp),
    )
    tools = sdk / "build-tools/35.0.0"
    platform = sdk / "platforms/android-35/android.jar"
    key = private / "debug.keystore"
    if not key.exists():
        run(
            [
                "keytool",
                "-genkeypair",
                "-keystore",
                key,
                "-storepass",
                "android",
                "-keypass",
                "android",
                "-alias",
                "androiddebugkey",
                "-dname",
                "CN=Frame Media Lab Debug",
                "-keyalg",
                "RSA",
                "-validity",
                "3650",
            ],
            env,
            out,
        )
        key.chmod(0o600)
    for module in MODULES:
        src = ROOT / "android" / module / "src/main"
        work = out / module
        work.mkdir(exist_ok=True)
        classes = work / "classes"
        classes.mkdir(exist_ok=True)
        dex = work / "dex"
        dex.mkdir(exist_ok=True)
        for previous in dex.glob("classes*.dex"):
            previous.unlink()
        # A fresh archive contains only current source classes even on repeated builds.
        for previous in classes.rglob("*.class"):
            previous.unlink()
        run(
            [
                "javac",
                "-encoding",
                "UTF-8",
                "-source",
                "8",
                "-target",
                "8",
                "-bootclasspath",
                java_bootclasspath(sdk),
                "-d",
                classes,
                *sorted((src / "java").rglob("*.java")),
            ],
            env,
            work,
        )
        archive = work / "classes.jar"
        run(["jar", "cf", archive, "-C", classes, "."], env, work)
        run(
            [
                tools / "d8",
                "--min-api",
                "26",
                "--lib",
                platform,
                "--output",
                dex,
                archive,
            ],
            env,
            work,
        )
        unsigned = work / "unsigned.apk"
        run(
            [
                tools / "aapt2",
                "link",
                "-I",
                platform,
                "--manifest",
                src / "AndroidManifest.xml",
                "-o",
                unsigned,
            ],
            env,
            work,
        )
        with zipfile.ZipFile(unsigned, "a", compression=zipfile.ZIP_STORED) as apk:
            for path in sorted(dex.glob("classes*.dex")):
                apk.write(path, path.name)
        aligned = work / "aligned.apk"
        run([tools / "zipalign", "-f", "4", unsigned, aligned], env, work)
        target = out / (module + "-debug.apk")
        run(
            [
                tools / "apksigner",
                "sign",
                "--ks",
                key,
                "--ks-key-alias",
                "androiddebugkey",
                "--ks-pass",
                "pass:android",
                "--key-pass",
                "pass:android",
                "--out",
                target,
                aligned,
            ],
            env,
            work,
        )
        run([tools / "apksigner", "verify", "--verbose", target], env, work)
        print(target)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sdk", help="Existing Android SDK root")
    parser.add_argument("--check", action="store_true", help="Only check prerequisites")
    args = parser.parse_args(argv)
    sdk = find_sdk(args.sdk)
    errors = prerequisites(sdk)
    if errors:
        for error in errors:
            print("FAIL: " + error, file=sys.stderr)
        print("No software was installed. See docs/ANDROID.md.", file=sys.stderr)
        return 2
    if args.check:
        print(
            "PASS: required SDK files and JDK commands found; compilation has not been tested."
        )
        return 0
    try:
        build(sdk)
    except (OSError, subprocess.SubprocessError) as error:
        print("FAIL: Android build: " + str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
