"""Explicit, narrowly scoped device-changing operations."""

import re
from pathlib import Path
from .apk import inspect_apk
from .core import Bundle, Runner

COMPONENT = re.compile(r"[A-Za-z][A-Za-z0-9_.$]*/[A-Za-z_.][A-Za-z0-9_.$]*")
PACKAGE = re.compile(r"[A-Za-z][A-Za-z0-9_]*(?:\.[A-Za-z0-9_]+)+")


def successful(result):
    if result["status"] != "PASS":
        raise ValueError(result["stderr"] or result["stdout"] or "Command failed")
    return result


def install(runner: Runner, paths: list[Path], bundle: Bundle | None = None):
    if not paths:
        raise ValueError(
            "Supply an authorised APK or explicit matching split APK paths"
        )
    inspected = []
    for p in paths:
        if p.suffix.lower() != ".apk" or not p.is_file():
            raise ValueError(
                "Installation accepts explicit .apk files only; inspect .apks then select matching splits"
            )
        inspected.append(inspect_apk(p))
    packages = {x["package"] for x in inspected}
    versions = {x["version_code"] for x in inspected}
    if len(packages) != 1 or len(versions) != 1:
        raise ValueError("APK set package/version mismatch")
    if len(paths) > 1 and sum(not x.get("split") for x in inspected) != 1:
        raise ValueError("Split set must contain exactly one base APK")
    runner.require_android()
    result = runner.adb(
        ["install" if len(paths) == 1 else "install-multiple", "-r"]
        + [str(p.resolve()) for p in paths],
        timeout=180,
    )
    if result["status"] == "PASS" and "Success" not in result["stdout"]:
        result["status"] = "FAIL"
    if bundle:
        bundle.write("android/installed-apk-metadata.json", inspected)
        bundle.record("android/install", result)
    return successful(result)


def resolve(runner: Runner, package: str):
    if not PACKAGE.fullmatch(package):
        raise ValueError("Invalid Android package name")
    runner.require_android()
    for category in (
        "android.intent.category.LAUNCHER",
        "android.intent.category.LEANBACK_LAUNCHER",
    ):
        r = runner.shell(
            [
                "cmd",
                "package",
                "resolve-activity",
                "--brief",
                "-a",
                "android.intent.action.MAIN",
                "-c",
                category,
                "-p",
                package,
            ]
        )
        for line in r["stdout"].splitlines():
            if COMPONENT.fullmatch(line.strip()):
                return line.strip()
    raise ValueError(
        "No launcher resolved. Inspect APK activity aliases/exported state, then supply explicit package/activity"
    )


def launch(runner: Runner, component: str, source: str | None = None):
    if not COMPONENT.fullmatch(component):
        raise ValueError("Expected package/activity")
    runner.require_android()
    argv = ["am", "start", "-W", "-S", "-n", component]
    if source is not None:
        if not source.startswith(("https://", "http://", "content://", "file://", "/")):
            raise ValueError(
                "Source must be a clear-content URL, content URI or absolute guest file path"
            )
        argv += ["--es", "source", source]
    r = runner.shell(argv, timeout=45)
    if re.search(
        r"(?im)^\s*(Error|Exception|Status:\s*(?:timeout|error))", r["stdout"]
    ):
        r["status"] = "FAIL"
    return successful(r)
