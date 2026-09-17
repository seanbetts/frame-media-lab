"""Frame Media Lab entry point. Global options precede the subcommand."""

from __future__ import annotations
import argparse
import json
import shlex
import sys
import zipfile
from pathlib import Path
from .core import Config, Bundle, ROOT, Runner, redact
from .android_sdk import tool_path
from .collect import (
    doctor,
    inspect_host,
    android_status,
    retrieve_app,
    collect_playback,
    runtime_probe,
    effective_components,
)
from .compare import compare
from .apk import inspect_apk
from .actions import install, launch, resolve, successful
from .reports import render_report, SERVICES
from .synthetic import populate, SCENARIOS
from .workflow import (
    first_hour,
    record_service,
    STAGES,
    run_stage,
    reset_stage,
    media_launch_id,
    wait_media_launch,
)
from .media import generate, ENCODERS


def parser():
    p = argparse.ArgumentParser(
        description="Safe Mac-side Steam Frame / Lepton media investigation. Global options go before the command."
    )
    p.add_argument(
        "--config",
        type=Path,
        help="Local JSON configuration (no automatic device discovery)",
    )
    p.add_argument(
        "--rebind-adb",
        action="store_true",
        help="Assert changed ADB endpoint is the same Frame/context when resuming",
    )
    p.add_argument("--host")
    p.add_argument(
        "--serial", help="Explicit Android guest ADB serial, not Linux USB host"
    )
    p.add_argument("--results", type=Path)
    p.add_argument("--bundle", type=Path, help="Append to/resume this existing bundle")
    p.add_argument(
        "--synthetic",
        choices=SCENARIOS,
        help="Offline synthetic evidence; never contacts Frame",
    )
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("doctor", help="Dependency and read-only connectivity preflight")
    sub.add_parser(
        "discover",
        help="List local ADB endpoints and inspect only the configured SSH host; no LAN scan",
    )
    i = sub.add_parser(
        "inspect", help="Read-only host/overlay inspection; never invokes Lepton"
    )
    i.add_argument(
        "--containers",
        action="store_true",
        help="Explicitly allow Podman metadata queries; it may initialize runtime state",
    )
    sub.add_parser(
        "effective-components",
        help="Hash a bounded component-library selection in the current ADB namespace",
    )
    sub.add_parser(
        "android-status",
        help="Android identity/packages/services through explicit ADB target",
    )
    for name in ("drm", "codecs"):
        sub.add_parser(
            name,
            help="Retrieve already-generated diagnostics JSON; does not install or launch",
        )
    sub.add_parser("media-result", help="Retrieve completed clear media JSON")
    a = sub.add_parser("inspect-apk", help="Read APK or .apks/.xapk metadata locally")
    a.add_argument("paths", nargs="+", type=Path)
    a = sub.add_parser(
        "install-apk",
        help="CHANGES ANDROID: install/replace one APK or explicit matching split set",
    )
    a.add_argument("paths", nargs="+", type=Path)
    a = sub.add_parser("resolve", help="Resolve MAIN/LAUNCHER or LEANBACK Activity")
    a.add_argument("package")
    a = sub.add_parser(
        "launch", help="CHANGES ANDROID: force-stop and launch the named Activity"
    )
    a.add_argument("component")
    a = sub.add_parser(
        "play", help="CHANGES ANDROID: launch our installed clear player"
    )
    a.add_argument("source")
    a = sub.add_parser(
        "collect", help="Codec/compositor snapshots; filtered logcat only if requested"
    )
    a.add_argument("--logs", action="store_true")
    a.add_argument("--pid", type=int)
    a = sub.add_parser(
        "compare",
        help="Compare relevant collected overlay hashes to exact public overlay paths",
    )
    a.add_argument("--source", type=Path, default=ROOT.parent / "Lepton")
    a = sub.add_parser(
        "report", help="Generate report.md + report.json from an existing bundle"
    )
    a.add_argument("directory", type=Path, nargs="?")
    a = sub.add_parser(
        "first-hour", help="Resumable interactive stages; confirms runtime/app changes"
    )
    a.add_argument("--retry-stage", choices=STAGES)
    a = sub.add_parser(
        "record-service", help="Record human service observations locally"
    )
    a.add_argument("service", choices=SERVICES)
    a = sub.add_parser(
        "runtime-probe",
        help="MAY CHANGE FRAME RUNTIME: lepton ps/help pre-dispatch setup",
    )
    a.add_argument("--allow-runtime-changes", action="store_true", required=True)
    a = sub.add_parser(
        "connection-plan", help="Print exact connection commands; executes none"
    )
    a.add_argument("--guest-port", type=int, required=True)
    a.add_argument("--local-port", type=int, default=15555)
    a.add_argument("--method", choices=("direct", "ssh", "usb"))
    a.add_argument("--usb-serial")
    a = sub.add_parser(
        "connect-adb", help="CHANGES CONNECTION STATE: explicit adb connect"
    )
    a.add_argument("endpoint")
    a = sub.add_parser(
        "build-android", help="Build with existing SDK/JDK; installs nothing"
    )
    a.add_argument("--sdk", type=Path)
    a.add_argument("--check", action="store_true")
    a = sub.add_parser(
        "generate-media",
        help="Generate local clear test patterns using installed ffmpeg",
    )
    a.add_argument("--codec", choices=tuple(ENCODERS) + ("all",), default="all")
    a.add_argument("--size", choices=("1080p", "4k", "all"), default="all")
    a.add_argument("--seconds", type=int, default=5)
    a = sub.add_parser(
        "redact", help="Write a redacted copy locally; review before sharing"
    )
    a.add_argument("input", type=Path)
    a.add_argument("output", type=Path)
    sub.add_parser(
        "verify-source",
        help="Compare protected source/archive hashes to the initial snapshot",
    )
    return p


def connection_plan(config, args):
    adb = tool_path("adb") or "adb"
    args.method = args.method or (
        config.adb_method if config.adb_method != "existing" else "ssh"
    )
    for n in (args.guest_port, args.local_port):
        if not 1 <= n <= 65535:
            raise ValueError("Ports must be 1..65535")
    if args.method == "direct":
        if not config.host:
            raise ValueError("Set --host")
        endpoint = (
            (f"[{config.host}]" if ":" in config.host else config.host)
            + ":"
            + str(args.guest_port)
        )
    else:
        endpoint = "127.0.0.1:" + str(args.local_port)
        if args.method == "ssh":
            if not config.host:
                raise ValueError("Set --host")
            print("LOCAL MAC COMMAND; keep tunnel running in a separate terminal:")
            print(
                shlex.join(
                    [
                        "ssh",
                        "-o",
                        "ExitOnForwardFailure=yes",
                        "-o",
                        "StrictHostKeyChecking=yes",
                        "-N",
                        "-L",
                        f"127.0.0.1:{args.local_port}:127.0.0.1:{args.guest_port}",
                        "-p",
                        str(config.ssh_port),
                        config.ssh_user + "@" + config.host,
                    ]
                )
            )
        else:
            if not args.usb_serial or args.usb_serial.startswith("-"):
                raise ValueError("Supply the observed Linux USB-host --usb-serial")
            print("LOCAL MAC COMMAND; changes ADB forwarding:")
            print(
                shlex.join(
                    [
                        adb,
                        "-s",
                        args.usb_serial,
                        "forward",
                        f"tcp:{args.local_port}",
                        f"tcp:{args.guest_port}",
                    ]
                )
            )
    print("LOCAL MAC COMMAND:\n" + shlex.join([adb, "connect", endpoint]))
    print(
        "ANDROID GUEST COMMAND:\n"
        + shlex.join([adb, "-s", endpoint, "shell", "getprop", "ro.build.version.sdk"])
    )
    print(
        "Set FML_SERIAL to "
        + shlex.quote(endpoint)
        + ". Do not assume USB host ADB is Android."
    )


def verify_source():
    import hashlib

    baseline = ROOT / "build/source-baseline.json"
    if not baseline.exists():
        raise ValueError(
            "Initial source hash snapshot missing; cannot establish unchanged state"
        )
    before = json.loads(baseline.read_text())
    after = {}
    for root in (ROOT.parent / "Lepton", ROOT.parent / "LEPTON_MEDIA_INVESTIGATION.md"):
        for f in sorted(root.rglob("*")) if root.is_dir() else [root]:
            if f.is_file():
                after[str(f.relative_to(ROOT.parent))] = hashlib.sha256(
                    f.read_bytes()
                ).hexdigest()
    changes = [
        p for p in sorted(before.keys() | after.keys()) if before.get(p) != after.get(p)
    ]
    print(
        json.dumps(
            {
                "status": "FAIL" if changes else "PASS",
                "files_checked": len(before),
                "changed": changes,
            },
            indent=2,
        )
    )
    return 1 if changes else 0


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        config = Config.load(
            args.config,
            {
                "host": args.host,
                "serial": args.serial,
                "results_dir": str(args.results) if args.results else None,
            },
        )
        runner = Runner(config)
        cmd = args.command
        if args.synthetic and cmd not in (
            "doctor",
            "discover",
            "inspect",
            "android-status",
            "drm",
            "codecs",
            "collect",
            "compare",
            "report",
            "first-hour",
        ):
            raise ValueError(
                "Synthetic mode cannot execute device mutations or unrelated local commands"
            )
        if cmd == "build-android":
            command = [sys.executable, str(ROOT / "scripts/build_android.py")]
            if args.sdk:
                command += ["--sdk", str(args.sdk)]
            if args.check:
                command += ["--check"]
            result = runner.run(command, timeout=300)
            print(result["stdout"])
            print(result["stderr"], file=sys.stderr)
            return result["returncode"] or 0
        if cmd == "generate-media":
            result = generate(
                tuple(ENCODERS) if args.codec == "all" else (args.codec,),
                ("1080p", "4k") if args.size == "all" else (args.size,),
                args.seconds,
                runner,
            )
            print(json.dumps(redact(result), indent=2))
            return 1 if any(x["status"] == "FAIL" for x in result) else 0
        if cmd == "verify-source":
            return verify_source()
        if cmd == "connection-plan":
            connection_plan(config, args)
            return 0
        if cmd == "redact":
            if args.input.resolve() == args.output.resolve():
                raise ValueError("Output must differ from input; raw file is preserved")
            if args.output.exists():
                raise ValueError("Output already exists; choose a new path")
            text = args.input.read_text()
            try:
                clean = json.dumps(redact(json.loads(text)), indent=2) + "\n"
            except ValueError:
                clean = str(redact(text))
            args.output.write_text(clean)
            args.output.chmod(0o600)
            print("REDACTED / REVIEW BEFORE SHARING:", args.output)
            return 0
        if cmd == "inspect-apk":
            print(json.dumps([inspect_apk(p) for p in args.paths], indent=2))
            return 0
        if cmd == "connect-adb":
            import re

            if not re.fullmatch(
                r"(?:[A-Za-z0-9][A-Za-z0-9_.-]*|\[[0-9a-fA-F:]+\]):[0-9]{1,5}",
                args.endpoint,
            ):
                raise ValueError("Supply explicit hostname:port endpoint")
            if not 1 <= int(args.endpoint.rsplit(":", 1)[1]) <= 65535:
                raise ValueError("Invalid ADB port")
            result = successful(runner.run(["adb", "connect", args.endpoint]))
            if (
                "connected to" not in result["stdout"]
                and "already connected" not in result["stdout"]
            ):
                raise ValueError(result["stdout"])
            print(redact(result["stdout"]))
            return 0
        if cmd == "resolve":
            print(resolve(runner, args.package))
            return 0
        selected = args.bundle or (args.directory if cmd == "report" else None)
        if (
            cmd in ("report", "compare", "record-service")
            and not selected
            and not args.synthetic
        ):
            raise ValueError(
                "Select an existing result directory with --bundle (or report DIRECTORY)"
            )
        bundle = (
            Bundle.open(
                selected,
                None
                if cmd in ("report", "compare") and not args.synthetic
                else bool(args.synthetic),
            )
            if selected
            else Bundle.create(Path(config.results_dir), config, bool(args.synthetic))
        )
        if (
            selected
            and not args.synthetic
            and cmd not in ("report", "compare", "record-service")
        ):
            bundle.check_target(config, args.rebind_adb)
        print("Result bundle:", bundle.path)
        if args.synthetic:
            populate(bundle, args.synthetic)
            if cmd == "first-hour":
                failure = {
                    "unreachable": 0,
                    "lepton-missing": 2,
                    "no-dev-context": 2,
                    "adb-unavailable": 3,
                }.get(args.synthetic)
                for i, name in enumerate(STAGES):
                    if failure is not None and i >= failure:
                        bundle.stage(
                            name,
                            "FAIL" if i == failure else "NOT TESTED",
                            "SYNTHETIC simulated failure or dependent stage",
                        )
                        continue
                    run_stage(bundle, name, lambda: None)
                    bundle.stage(
                        name,
                        "PASS",
                        "SYNTHETIC simulated stage; human observations are not real",
                    )
            compare(bundle, ROOT.parent / "Lepton")
            render_report(bundle)
            print("SYNTHETIC ONLY:", bundle.path / "report.md")
            return 0
        if cmd == "doctor":
            checks = doctor(config, runner)
            bundle.write("host/doctor.json", checks)
            for c in checks:
                print(f"{c['status']}: {c['check']} — {c['detail']}")
            return 1 if any(c["status"] == "FAIL" for c in checks) else 0
        if cmd == "discover":
            r = runner.run(["adb", "devices", "-l"])
            bundle.record("android/endpoints", r)
            print(redact(r["stdout"] or r["stderr"]))
            if config.host:
                inspect_host(bundle, runner)
            print(
                "Discovery makes no LAN scans. Use runtime-probe explicitly for actual Lepton ADB port; 5555 is not assumed."
            )
        elif cmd == "inspect":
            inspect_host(bundle, runner, args.containers)
        elif cmd == "android-status":
            android_status(bundle, runner)
        elif cmd == "effective-components":
            effective_components(bundle, runner)
        elif cmd in ("drm", "codecs", "media-result"):
            data = retrieve_app(
                bundle, runner, "media" if cmd == "media-result" else "diagnostics"
            )
            print(
                json.dumps(
                    data.get("widevine")
                    if cmd == "drm"
                    else data.get("codecs")
                    if cmd == "codecs"
                    else data,
                    indent=2,
                )
            )
        elif cmd == "install-apk":
            print(redact(install(runner, args.paths, bundle)["stdout"]))
        elif cmd in ("launch", "play"):
            previous = media_launch_id(runner) if cmd == "play" else None
            r = launch(
                runner,
                args.component
                if cmd == "launch"
                else "org.framemedialab.media/.MainActivity",
                args.source if cmd == "play" else None,
            )
            bundle.record("android/launch", r)
            print(redact(r["stdout"]))
            if cmd == "play":
                bundle.write(
                    "media/expected-launch.json",
                    {"launch_id": wait_media_launch(runner, previous)},
                )
        elif cmd == "collect":
            collect_playback(bundle, runner, args.logs, args.pid)
        elif cmd == "compare":
            print("Compared components:", len(compare(bundle, args.source)))
        elif cmd == "runtime-probe":
            runtime_probe(bundle, runner)
        elif cmd == "record-service":
            record_service(bundle, args.service)
        elif cmd == "first-hour":
            if args.retry_stage:
                reset_stage(bundle, args.retry_stage)
            first_hour(bundle, runner)
            return 0
        render_report(bundle)
        print("Report:", bundle.path / "report.md")
        return (
            1
            if any(s["status"] == "FAIL" for s in bundle.metadata["stages"].values())
            else 0
        )
    except (ValueError, OSError, KeyError, zipfile.BadZipFile) as exc:
        print("FAIL: " + str(redact(str(exc))), file=sys.stderr)
        return 2
    except (EOFError, KeyboardInterrupt):
        print("\nPaused. Existing bundle evidence is preserved.", file=sys.stderr)
        return 130
