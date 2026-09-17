"""Read-only probes. Lepton launcher calls are isolated behind explicit consent."""

from __future__ import annotations
import json
import platform
import shutil
from .android_sdk import find_sdk, tool_path
from .core import (
    Bundle,
    Config,
    ROOT,
    Runner,
    parse_properties,
    parse_lepton_ps,
    redact,
)

HOST_QUERIES = {
    "uname": ["uname", "-a"],
    "os-release": ["cat", "/etc/os-release"],
    "cpu": ["lscpu", "--json"],
    "tools": [
        "sh",
        "-c",
        'for x in lepton podman gamescope adb python3; do command -v "$x" || true; done',
    ],
    "lepton-identity": [
        "sh",
        "-c",
        'p=$(command -v lepton) || exit 1; readlink -f "$p"; stat "$p"; sha256sum "$p"; pacman -Qo "$p"',
    ],
    "packages": [
        "sh",
        "-c",
        "pacman -Q 2>/dev/null | grep -Ei 'lepton|steam|gamescope|podman|mesa|vulkan|qcom|qualcomm|widevine|drm'",
    ],
    "podman-version": ["podman", "--version"],
    "devices": [
        "sh",
        "-c",
        'for p in /dev/dri /dev/binderfs /dev/video* /dev/tee* /dev/qsee* /dev/dma_heap /dev/ion /dev/kgsl*; do test ! -e "$p" || ls -ld "$p" "$p"/* 2>/dev/null; done',
    ],
    "sockets": [
        "sh",
        "-c",
        'r=${XDG_RUNTIME_DIR:-/run/user/$(id -u)}; find "$r" -maxdepth 2 -type s -printf "%p %m %u %g\\n" 2>/dev/null',
    ],
    "auto-install": [
        "sh",
        "-c",
        'if test -d "$HOME/lepton_auto_install_apks"; then find "$HOME/lepton_auto_install_apks" -type f -name "*.apk" -printf "%P\\n"; fi',
    ],
    "contexts": [
        "sh",
        "-c",
        'for p in "$HOME/.local/share/lepton" "$HOME/.local/share/Steam/steamapps/common/Lepton"; do if test -d "$p"; then find "$p" -maxdepth 2 -type d -print; fi; done',
    ],
    "kernel": ["sh", "-c", "uname -r; cat /proc/version; cat /proc/filesystems"],
}
ANDROID_QUERIES = {
    "properties": ["getprop"],
    "packages": ["pm", "list", "packages", "-f"],
    "features": ["pm", "list", "features"],
    "libraries": ["pm", "list", "libraries"],
    "services": ["service", "list"],
    "dumpsys-services": ["dumpsys", "-l"],
    "hal": ["lshal"],
    "webview": ["dumpsys", "webviewupdate"],
    "mountinfo": ["cat", "/proc/self/mountinfo"],
    "devices": [
        "sh",
        "-c",
        'for p in /dev/dri /dev/char /dev/binderfs /dev/video* /dev/tee* /dev/qsee* /dev/dma_heap /dev/ion; do test ! -e "$p" || ls -ld "$p" "$p"/* 2>/dev/null; done',
    ],
    "component-paths": [
        "sh",
        "-c",
        "find /vendor/lib64 /system/lib64 /apex /vendor/etc/vintf /vendor/etc/init -type f 2>/dev/null | grep -Ei 'widevine|oemcrypto|drm|codec|media|gralloc|allocator|mapper|hwcomposer|vulkan|qti|tee|openxr' | head -n 3000",
    ],
}
PROPERTY_KEYS = [
    "ro.build.version.release",
    "ro.build.version.sdk",
    "ro.build.version.security_patch",
    "ro.build.fingerprint",
    "ro.build.tags",
    "ro.product.cpu.abilist",
    "ro.product.model",
    "ro.product.manufacturer",
    "ro.secure",
    "ro.debuggable",
    "ro.boot.verifiedbootstate",
    "ro.boot.vbmeta.device_state",
    "ro.boot.flash.locked",
    "lepton.headless",
    "ro.hardware.gralloc",
    "ro.hardware.egl",
    "ro.hardware.vulkan",
    "debug.stagefright.ccodec",
]


def android_identity(properties: str, packages: str) -> dict:
    props = parse_properties(properties)
    return {
        "properties": {k: props.get(k, "UNKNOWN") for k in PROPERTY_KEYS},
        "gms_package_present": any(
            line.rsplit("=", 1)[-1].strip() == "com.google.android.gms"
            for line in packages.splitlines()
        ),
        "play_store_package_present": any(
            line.rsplit("=", 1)[-1].strip() == "com.android.vending"
            for line in packages.splitlines()
        ),
        "certification": "UNKNOWN",
    }


def doctor(config: Config, runner: Runner, remote=True) -> list[dict]:
    checks = []

    def add(name, status, detail):
        checks.append({"check": name, "status": status, "detail": redact(detail)})

    add(
        "control machine",
        "PASS"
        if platform.system() == "Darwin" and platform.machine() == "arm64"
        else "WARNING",
        platform.system() + " " + platform.machine(),
    )
    for name, required, hint in [
        ("python3", True, "Python 3.10+ from python.org"),
        ("ssh", True, "macOS includes OpenSSH"),
        (
            "adb",
            False,
            "Install Android SDK Platform-Tools from developer.android.com/tools/releases/platform-tools",
        ),
        ("java", False, "Use JDK 17; set JAVA_HOME to the installed JDK"),
        ("javac", False, "JDK 17 compiler needed for APK builds"),
        ("ffmpeg", False, "ffmpeg.org/download.html; only fixture generation needs it"),
        ("ffprobe", False, "Included with ffmpeg"),
    ]:
        found = tool_path(name)
        add(name, "PASS" if found else "FAIL" if required else "WARNING", found or hint)
    if shutil.which("java"):
        r = runner.run(["java", "-version"])
        add("working Java", "PASS" if r["status"] == "PASS" else "WARNING", r["stderr"])
    sdk = find_sdk()
    sdk_ready = sdk is not None and (sdk / "platforms/android-35/android.jar").is_file()
    sdk_ready = sdk_ready and all(
        (sdk / "build-tools/35.0.0" / n).is_file()
        for n in ("aapt", "aapt2", "d8", "zipalign", "apksigner")
    )
    add(
        "Android SDK",
        "PASS" if sdk_ready else "WARNING",
        f"SDK API 35 and Build-Tools 35.0.0 found at {sdk}"
        if sdk_ready
        else "Install Android Studio SDK or command-line tools; see docs/ANDROID.md",
    )
    for name in ("sdkmanager", "aapt", "aapt2"):
        found = tool_path(name)
        add(name, "PASS" if found else "WARNING", found or "See docs/ANDROID.md")
    if tool_path("adb"):
        r = runner.run(["adb", "version"])
        add("working ADB", r["status"], r["stdout"] + r["stderr"])
    if not config.host or not remote:
        add(
            "Frame SSH",
            "NOT TESTED",
            "No configured host" if not config.host else "Remote checks omitted",
        )
    else:
        r = runner.ssh(["uname", "-s"])
        add("Frame SSH", r["status"], r["stdout"] + r["stderr"])
        if r["status"] == "PASS":
            for name in ("os-release", "tools", "sockets"):
                r = runner.ssh(HOST_QUERIES[name])
                add("Frame " + name, r["status"], r["stdout"] + r["stderr"])
            for tool in ("lepton", "podman"):
                r = runner.ssh(["sh", "-c", "command -v " + tool])
                add("Frame " + tool, r["status"], r["stdout"] + r["stderr"])
            add(
                "Lepton running / ADB port",
                "NOT TESTED",
                "Use explicit runtime-probe or already connected Android; default doctor never invokes Lepton",
            )
    if config.serial:
        try:
            r = runner.require_android()
            add("Android endpoint", "PASS", "Android SDK " + r["stdout"].strip())
        except ValueError as exc:
            add("Android endpoint", "FAIL", str(exc))
    else:
        add(
            "Android endpoint",
            "NOT TESTED",
            "Select explicit Android guest serial after connection",
        )
    return checks


def inspect_host(bundle: Bundle, runner: Runner, containers=False):
    if not runner.config.host:
        bundle.stage("host", "NOT TESTED", "No Frame host configured")
        return
    reachable = runner.ssh(["uname", "-s"])
    bundle.record("host/connectivity", reachable)
    if reachable["status"] != "PASS":
        bundle.stage("host", "FAIL", "Frame unreachable")
        return
    for key, query in HOST_QUERIES.items():
        bundle.record("host/" + key, runner.ssh(query))
    identity = runner.ssh(
        ["python3", "-"],
        input_text=(ROOT / "scripts/inspect/installed_identity.py").read_text(),
    )
    bundle.record("lepton/installed-identity-command", identity)
    if identity["status"] == "PASS":
        try:
            bundle.write(
                "lepton/installed-identity.json", json.loads(identity["stdout"])
            )
        except ValueError:
            pass
    r = runner.ssh(
        ["python3", "-"],
        input_text=(ROOT / "scripts/inspect/overlay_inventory.py").read_text(),
        timeout=180,
    )
    bundle.record("host/overlay-command", r)
    if r["status"] == "PASS":
        try:
            bundle.write("host/overlay.json", json.loads(r["stdout"]))
        except ValueError:
            bundle.stage("overlay", "FAIL", "Inventory returned invalid JSON")
    else:
        bundle.stage(
            "overlay",
            "NOT TESTED",
            "Remote Python 3 or permissions unavailable; metadata query failed",
        )
    if containers:
        collect_mounts(bundle, runner)
    else:
        bundle.stage(
            "containers",
            "NOT TESTED",
            "Opt in with --containers: Podman may initialize local runtime state",
        )
    os_data = bundle.read("host/os-release.json", {}).get("stdout", "")
    bundle.metadata["frame"] = {
        "os_release": os_data,
        "uname": bundle.read("host/uname.json", {}).get("stdout", "UNKNOWN"),
    }
    bundle.save()
    bundle.stage("host", "PASS" if not bundle.metadata["errors"] else "PARTIAL")


def collect_mounts(bundle: Bundle, runner: Runner):
    """Query only selected fields, avoiding Config.Env and full inspect secrets."""
    r = runner.ssh(
        [
            "podman",
            "ps",
            "-a",
            "--format",
            '{"Id":{{json .ID}},"Names":{{json .Names}}}',
        ]
    )
    bundle.record("lepton/containers", r)
    mounts = []
    if r["status"] == "PASS":
        try:
            rows = [
                json.loads(line) for line in r["stdout"].splitlines() if line.strip()
            ]
            for row in rows:
                names = row.get("Names", [])
                if isinstance(names, str):
                    names = [names]
                if "lepton-" + runner.config.context not in names:
                    continue
                cid = row.get("Id") or row.get("ID")
                if not cid:
                    continue
                for name, fmt in [
                    ("mounts", "{{json .Mounts}}"),
                    ("identity", "{{json .ImageName}}"),
                    ("rootfs", "{{json .GraphDriver.Data}}"),
                ]:
                    result = runner.ssh(["podman", "inspect", "--format", fmt, cid])
                    bundle.record("lepton/" + name, result)
                    if name == "mounts" and result["status"] == "PASS":
                        mounts = [
                            {
                                "source": m.get("Source"),
                                "destination": m.get("Destination"),
                                "type": m.get("Type"),
                                "options": m.get("Options", []),
                            }
                            for m in json.loads(result["stdout"])
                        ]
        except (ValueError, TypeError, KeyError) as exc:
            bundle.stage("containers", "FAIL", str(exc))
            return
    bundle.write("lepton/mount-map.json", mounts)
    bundle.stage(
        "containers",
        "PASS" if mounts else "NOT TESTED",
        "No mounts found for selected context" if not mounts else "",
    )


def android_status(bundle: Bundle, runner: Runner):
    if not runner.config.serial:
        bundle.stage("android", "NOT TESTED", "No explicit Android serial")
        return
    try:
        runner.require_android()
    except ValueError as exc:
        bundle.stage("android", "FAIL", str(exc))
        return
    outputs = {}
    for key, query in ANDROID_QUERIES.items():
        r = runner.shell(query)
        bundle.record("android/" + key, r)
        outputs[key] = r
    identity = android_identity(
        outputs["properties"]["stdout"], outputs["packages"]["stdout"]
    )
    if outputs["packages"]["status"] != "PASS":
        identity["gms_package_present"] = "UNKNOWN"
        identity["play_store_package_present"] = "UNKNOWN"
    bundle.write("android/identity.json", identity)
    bundle.stage(
        "android",
        "PASS" if all(v["status"] == "PASS" for v in outputs.values()) else "PARTIAL",
        "Missing optional commands are retained as evidence",
    )


def retrieve_app(
    bundle: Bundle,
    runner: Runner,
    kind="diagnostics",
    reject_run_id=None,
    expected_launch_id=None,
) -> dict:
    runner.require_android()
    if kind == "media" and not expected_launch_id:
        expected_launch_id = bundle.read("media/expected-launch.json", {}).get(
            "launch_id"
        )
    package = "org.framemedialab." + (
        "diagnostics" if kind == "diagnostics" else "media"
    )
    r = runner.adb(["exec-out", "run-as", package, "cat", "files/" + kind + ".json"])
    bundle.record(("drm" if kind == "diagnostics" else "media") + "/export-command", r)
    if r["status"] != "PASS":
        raise ValueError(
            "No app JSON: install/launch the matching debug APK, wait for completion, then retry"
        )
    data = json.loads(r["stdout"])
    if (
        data.get("synthetic") is not False
        or data.get("schema_version") != 1
        or data.get("complete") is not True
    ):
        raise ValueError(
            "App export is incomplete, synthetic, or uses an unsupported schema"
        )
    if reject_run_id and data.get("run_id") == reject_run_id:
        raise ValueError("Old app export; waiting for a new run")
    if expected_launch_id and data.get("launch_id") != expected_launch_id:
        raise ValueError("Media export belongs to an older Activity launch")
    bundle.write(
        "android/diagnostics.json" if kind == "diagnostics" else "media/playback.json",
        data,
    )
    if kind == "diagnostics":
        bundle.write("drm/widevine.json", data.get("widevine", {}))
        bundle.write("codecs/advertised.json", data.get("codecs", []))
    return data


def collect_playback(
    bundle: Bundle, runner: Runner, logs=False, pid: int | None = None
):
    runner.require_android()
    errors_before = len(bundle.metadata["errors"])
    for service in ("media.codec", "SurfaceFlinger", "display", "media.audio_flinger"):
        bundle.record("logs/" + service, runner.shell(["dumpsys", service], timeout=30))
    if logs:
        # No all-buffer logcat, media.drm dumps or licence traffic. Redact before storage.
        bundle.record(
            "logs/logcat",
            runner.adb(
                [
                    "logcat",
                    "-d",
                    "-t",
                    "500",
                    "-v",
                    "threadtime",
                    "MediaCodec:I",
                    "ACodec:I",
                    "CCodec:I",
                    "SurfaceFlinger:W",
                    "hwcomposer:W",
                    "gralloc:W",
                    "*:S",
                ]
            ),
        )
    if pid is not None:
        if not 1 <= pid <= 4194304:
            raise ValueError("PID out of range")
        # Library paths only, never addresses or app heap/data mappings.
        query = f"awk '$NF ~ /^\\/(vendor|system|apex)\\// && $NF ~ /\\.so/ {{print $NF}}' /proc/{pid}/maps | sort -u"
        bundle.record("logs/library-paths", runner.shell(["sh", "-c", query]))
        bundle.record(
            "logs/process-mountinfo", runner.shell(["cat", f"/proc/{pid}/mountinfo"])
        )
    bundle.stage(
        "playback-evidence",
        "PARTIAL" if len(bundle.metadata["errors"]) > errors_before else "PASS",
        "Snapshots do not prove protected allocation or headset visibility",
    )


def runtime_probe(bundle: Bundle, runner: Runner):
    for key, args in [("ps", ["ps"]), ("help", ["help"]), ("version", ["version"])]:
        r = runner.ssh(["lepton"] + args)
        bundle.record("lepton/" + key, r)
        if key == "ps":
            bundle.write("lepton/endpoints.json", parse_lepton_ps(r["stdout"]))
    bundle.stage(
        "runtime-probe",
        "PASS",
        "Explicitly allowed Lepton pre-dispatch runtime side effects",
    )


def effective_components(bundle: Bundle, runner: Runner):
    """Hash a bounded selection of component binaries, never secret/configuration stores."""
    import re

    runner.require_android()
    rows = []
    inventory = bundle.read("host/overlay.json", {}).get("files", [])
    paths = [
        x["path"]
        for x in inventory
        if x.get("relevant") and x.get("sha256") and x["path"].endswith(".so")
    ]
    paths += [
        "vendor/lib64/hw/hwcomposer.waydroid.so",
        "vendor/lib64/libminigbm_gralloc_msm.so",
        "vendor/lib64/libgralloccore.so",
    ]
    for path in sorted(set(paths))[:100]:
        if not re.fullmatch(
            r"(?:vendor|system|apex|odm|product)/[A-Za-z0-9_.@/+:-]+\.so", path
        ):
            continue
        if re.search(
            "keybox|credential|provision|private|secret|token|persist", path, re.I
        ):
            continue
        r = runner.shell(["sha256sum", "/" + path])
        digest = (
            r["stdout"].split()[0]
            if r["status"] == "PASS" and r["stdout"].strip()
            else None
        )
        if digest and not re.fullmatch(r"[0-9a-f]{64}", digest):
            digest = None
        rows.append(
            {
                "path": path,
                "sha256": digest,
                "status": r["status"],
                "error": r["stderr"],
                "namespace": "ADB shell; not necessarily the consuming media service namespace",
            }
        )
    bundle.write("android/effective-components.json", rows)
    return rows
