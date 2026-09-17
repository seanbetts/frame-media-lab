"""Ten resumable stages; explicit changes and direct headset observations."""

from __future__ import annotations
import json
import shlex
import time
from pathlib import Path
from .core import Bundle, ROOT, Runner, STATUSES
from .collect import (
    doctor,
    inspect_host,
    android_status,
    retrieve_app,
    collect_playback,
)
from .actions import install, launch, resolve
from .reports import (
    render_report,
    priority,
    assess_drm,
    service_template,
    FIELDS,
    SERVICES,
)

STAGES = (
    "01-preflight",
    "02-host",
    "03-start-development",
    "04-android",
    "05-diagnostics",
    "06-flatscreen",
    "07-clear-media",
    "08-drm-assessment",
    "09-service",
    "10-report",
)


class Pause(Exception):
    pass


class Skipped(Exception):
    pass


def run_stage(bundle, name, action):
    prior = bundle.metadata["stages"].get(name, {}).get("status")
    if prior in ("PASS", "SKIPPED"):
        return True
    bundle.stage(name, "RUNNING")
    try:
        action()
        bundle.stage(name, "PASS")
        return True
    except Skipped as exc:
        bundle.stage(name, "SKIPPED", str(exc))
        return True
    except (ValueError, OSError, Pause, EOFError, KeyboardInterrupt) as exc:
        bundle.stage(
            name,
            "FAIL"
            if not isinstance(exc, (Pause, EOFError, KeyboardInterrupt))
            else "PAUSED",
            str(exc),
        )
        print(f"{name}: paused — {exc}")
        return False


def ask(prompt, input_fn=input):
    answer = input_fn(prompt + " ").strip()
    if answer.lower() in ("q", "quit", "pause"):
        raise Pause("User paused; resume with --bundle")
    return answer


def confirm(prompt, input_fn=input):
    return ask(prompt + " [yes/no; q pauses]", input_fn).lower() == "yes"


def observe(bundle, key, prompt, input_fn=input):
    prior = bundle.read("android/observations.json", {})
    if key in prior:
        return prior[key]
    answer = ask(prompt + " [yes/no/unknown]", input_fn).lower()
    value = {"yes": "PASS", "no": "FAIL"}.get(answer, "UNKNOWN")
    prior[key] = value
    bundle.write("android/observations.json", prior)
    return value


def record_service(bundle, key, input_fn=input):
    data = service_template(key)
    data.update(bundle.read("services/" + key + ".json", {}))
    for field in FIELDS:
        value = ask(
            f"{SERVICES[key]} {field}: "
            + ", ".join(STATUSES)
            + " [Enter keeps "
            + data[field]
            + "]",
            input_fn,
        ).upper()
        if value:
            if value not in STATUSES:
                raise ValueError("Invalid status; answers already recorded are saved")
            data[field] = value
            bundle.write("services/" + key + ".json", data)
    resolution = ask(
        "Actual encoded/source resolution (e.g. 1920x1080; Enter UNKNOWN):", input_fn
    )
    evidence = (
        ask(
            "Resolution evidence (provider stats/decoder format; NOT window or panel size):",
            input_fn,
        )
        if resolution
        else "NOT TESTED"
    )
    data["actual_resolution"] = {
        "value": resolution or "UNKNOWN",
        "evidence": evidence or "UNKNOWN",
    }
    protected = ask(
        "Was this a protected title (not a clear trailer/upload)? [yes/no/unknown]",
        input_fn,
    ).lower()
    data["protected_content"] = {"yes": "PASS", "no": "FAIL"}.get(protected, "UNKNOWN")
    quality = ask(
        "Observed source quality [LOW/HD/4K/UNKNOWN; requires the resolution evidence above]:",
        input_fn,
    ).upper()
    if quality not in ("LOW", "HD", "4K", "UNKNOWN", ""):
        raise ValueError("Invalid quality classification")
    data["quality"] = quality or "UNKNOWN"
    for field in (
        "android_window_resolution",
        "steamvr_panel_resolution",
        "package_version",
        "title",
        "subscription_tier",
        "region",
        "quality_setting",
        "notes",
    ):
        answer = ask(field + " [Enter keeps existing]:", input_fn)
        if answer:
            data[field] = answer
        bundle.write("services/" + key + ".json", data)
    return data


def helper(bundle, runner, kind, input_fn):
    packages = {
        "diagnostics": "diagnostics",
        "flatscreen-test": "flatscreen",
        "media-test": "media",
    }
    apk = ROOT / "build/android" / f"{kind}-debug.apk"
    if not apk.is_file():
        raise ValueError(f"Build APK first: {apk.name}; run build-android")
    print(
        "Lepton may relocate installed APKs into a common directory. Preserve previous exports; use a fresh Lepton Development session between helpers if needed. Never start a second dev instance."
    )
    if not confirm(
        f"Install {apk.name} into the currently selected Android endpoint, replacing this helper if present, then launch it?",
        input_fn,
    ):
        raise Skipped("Helper not installed")
    install(runner, [apk], bundle)
    component = "org.framemedialab." + packages[kind] + "/.MainActivity"
    bundle.record("android/launch-" + kind, launch(runner, component))
    return component


def first_hour(bundle: Bundle, runner: Runner, input_fn=input):
    if bundle.metadata["synthetic"]:
        raise ValueError("Use --synthetic ... first-hour for a simulated walkthrough")
    print(
        "Commands run locally on Mac, over SSH on Frame, or in the explicitly selected Android guest. Type q at any prompt to pause. Completed stages will not repeat."
    )

    def preflight():
        checks = doctor(runner.config, runner)
        bundle.write("host/doctor.json", checks)
        for c in checks:
            print(c["status"], c["check"], c["detail"])
        if not runner.config.host:
            raise ValueError("Configure --host before the first-hour workflow")
        if any(
            c["status"] == "FAIL"
            for c in checks
            if c["check"] in ("Frame SSH", "ssh", "python3")
        ):
            raise ValueError("Resolve preflight failure and resume")

    def host():
        inspect_host(bundle, runner)
        if bundle.metadata["stages"].get("host", {}).get("status") not in (
            "PASS",
            "PARTIAL",
        ):
            raise ValueError("Host inspection failed")

    def start():
        print(
            "Starting Lepton changes runtime state and may auto-install APKs in ~/lepton_auto_install_apks. Review host/auto-install.json. Prefer the Valve Lepton Development UI. Leave it running."
        )
        print(
            "REMOTE FRAME COMMAND (run in a separate SSH terminal if no dev context is running):\n"
            + shlex.join(
                [
                    "env",
                    "APP_WANTS_FLATSCREEN=true",
                    "lepton",
                    "start",
                    runner.config.context,
                ]
            )
        )
        if not confirm(
            "Development session is running and the explicit ADB serial targets its Android guest?",
            input_fn,
        ):
            raise Pause("Development context not ready")
        runner.require_android()
        for _ in range(12):
            r = runner.shell(["getprop", "sys.boot_completed"])
            if r["status"] == "PASS" and r["stdout"].strip() == "1":
                return
            time.sleep(2)
        raise ValueError(
            "Android boot did not complete within bounded polling; resume later"
        )

    def android():
        android_status(bundle, runner)
        if bundle.metadata["stages"].get("android", {}).get("status") not in (
            "PASS",
            "PARTIAL",
        ):
            raise ValueError("Android baseline failed")

    def diagnostics():
        old = None
        previous = runner.adb(
            [
                "exec-out",
                "run-as",
                "org.framemedialab.diagnostics",
                "cat",
                "files/diagnostics.json",
            ]
        )
        if previous["status"] == "PASS":
            try:
                old = json.loads(previous["stdout"]).get("run_id")
            except ValueError:
                pass
        helper(bundle, runner, "diagnostics", input_fn)
        for _ in range(20):
            try:
                data = retrieve_app(bundle, runner, reject_run_id=old)
                if data.get("run_id") != old:
                    return
            except ValueError:
                pass
            time.sleep(1)
        raise ValueError(
            "Fresh complete diagnostics export unavailable; rerun after app finishes"
        )

    def flatscreen():
        helper(bundle, runner, "flatscreen-test", input_fn)
        observe(
            bundle,
            "video_visible",
            "Can you see the FRAME MEDIA LAB test application inside the headset?",
            input_fn,
        )
        for key, prompt in [
            ("pointer", "Do buttons respond to controller/pointer input?"),
            ("text_input", "Can you type into the text field?"),
            ("scroll", "Can you scroll?"),
            ("resize", "Does resizing work?"),
            ("home_back", "Do Home and Back behave correctly?"),
            ("relaunch", "Can you relaunch and see lifecycle events?"),
        ]:
            observe(bundle, key, prompt, input_fn)

    def clear():
        previous = media_launch_id(runner)
        component = helper(bundle, runner, "media-test", input_fn)
        expected = wait_media_launch(runner, previous)
        print(
            "Start with generated H.264 1080p + AAC. Use the app file picker or an accessible clear-content HTTP(S) URL. A Mac path is not an Android path."
        )
        source = ask(
            "Guest file/content/HTTP(S) URI (Enter uses app picker):", input_fn
        )
        if source:
            bundle.record("media/launch", launch(runner, component, source))
            expected = wait_media_launch(runner, expected)
        bundle.write("media/expected-launch.json", {"launch_id": expected})
        visible = observe(
            bundle,
            "clear_video",
            "Is clear H.264 1080p video visible and playing smoothly in the headset?",
            input_fn,
        )
        observe(bundle, "audio", "Is the 440 Hz test tone audible?", input_fn)
        if visible == "PASS":
            print(
                "Basic test passed by observation. Higher codec/resolution tests may now be run explicitly with play; record each in a separate bundle."
            )
        else:
            print("Stop progression to harder clips until H.264 1080p is working.")
        try:
            retrieve_app(bundle, runner, "media", expected_launch_id=expected)
        except ValueError as exc:
            print("Media export:", exc)

    def assessment():
        data = bundle.read("android/diagnostics.json", {})
        drm = assess_drm(data.get("widevine", {}))
        print(json.dumps(drm, indent=2))
        print("Protected compositor path: UNKNOWN")
        for recommendation in priority(drm, data.get("codecs", [])):
            print(recommendation)
        if not confirm(
            "Continue to the optional authorised streaming-app test?", input_fn
        ):
            decline_service(bundle)

    def service():
        print(
            "Nothing will be downloaded. Provide APKs only from an authorised source; use a fresh Development session if changing apps."
        )
        key = ask(
            "Service: disney/apple/hbo/netflix/youtube, or Enter to skip:", input_fn
        )
        if not key:
            raise Skipped("No commercial app supplied")
        if key not in SERVICES:
            raise ValueError("Unknown service")
        paths = shlex.split(
            ask(
                "Authorised local APK path(s), shell-quoted for spaces (Enter to record an already installed app):",
                input_fn,
            )
        )
        if paths:
            from .apk import inspect_apk

            details = [inspect_apk(Path(p)) for p in paths]
            print(json.dumps(details, indent=2))
            if not confirm(
                "Install this reviewed APK/set and launch its resolved Activity?",
                input_fn,
            ):
                raise Skipped("Commercial install declined")
            install(runner, [Path(p) for p in paths], bundle)
            launch(runner, resolve(runner, details[0]["package"]))
        print(
            "Perform account login/playback in the app. Do not enter credentials in this terminal. Record actual source resolution only with supporting diagnostics."
        )
        record_service(bundle, key, input_fn)

    def report():
        if confirm(
            "Collect bounded codec/compositor snapshots and filtered logcat after playback?",
            input_fn,
        ):
            collect_playback(bundle, runner, logs=True)
        render_report(bundle)

    actions = (
        preflight,
        host,
        start,
        android,
        diagnostics,
        flatscreen,
        clear,
        assessment,
        service,
        report,
    )
    for name, action in zip(STAGES, actions):
        print("\n" + name)
        if not run_stage(bundle, name, action):
            break
    render_report(bundle)
    print(
        "Saved:",
        bundle.path,
        "\nResume: ./frame-media-lab --bundle "
        + shlex.quote(str(bundle.path))
        + " first-hour",
    )


def decline_service(bundle):
    bundle.stage(
        "09-service",
        "SKIPPED",
        "User declined commercial test at the DRM decision point; explicitly retry to revisit",
    )


def reset_stage(bundle, name):
    bundle.metadata["stages"].pop(name, None)
    fields = {
        "06-flatscreen": [
            "video_visible",
            "pointer",
            "text_input",
            "scroll",
            "resize",
            "home_back",
            "relaunch",
        ],
        "07-clear-media": ["clear_video", "audio"],
    }.get(name, [])
    observations = bundle.read("android/observations.json", {})
    for key in fields:
        observations.pop(key, None)
    if fields:
        bundle.write("android/observations.json", observations)
    bundle.save()


def media_launch_id(runner):
    r = runner.adb(
        ["exec-out", "run-as", "org.framemedialab.media", "cat", "files/media.json"]
    )
    if r["status"] == "PASS":
        try:
            d = json.loads(r["stdout"])
            if d.get("synthetic") is False and d.get("schema_version") == 1:
                return d.get("launch_id")
        except ValueError:
            pass
    return None


def wait_media_launch(runner, previous):
    for _ in range(10):
        current = media_launch_id(runner)
        if current and current != previous:
            return current
        time.sleep(0.3)
    raise ValueError("No fresh media Activity export; old results were not accepted")
