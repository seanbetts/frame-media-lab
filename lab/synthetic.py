"""Explicit fixture injection. This module never runs a transport command."""

import json
from .core import ROOT, Bundle, parse_lepton_ps
from .collect import android_identity
from .reports import service_template

SCENARIOS = (
    "baseline",
    "unreachable",
    "lepton-missing",
    "no-dev-context",
    "adb-unavailable",
    "widevine-unsupported",
    "provisioning-required",
    "l3",
    "l1",
    "software-only",
    "hardware-no-secure",
    "panel-absent",
    "protected-black",
    "login-failed",
    "low-resolution",
)


def populate(bundle: Bundle, scenario: str):
    if not bundle.metadata["synthetic"]:
        raise ValueError("Cannot inject fixtures into a real bundle")
    if scenario not in SCENARIOS:
        raise ValueError("Unknown synthetic scenario")
    f = json.loads((ROOT / "fixtures/mock/baseline.json").read_text())
    d = f["diagnostics"]
    bundle.metadata["scenario"] = scenario
    bundle.metadata["frame"] = f["host"]
    bundle.save()
    if scenario == "unreachable":
        bundle.record(
            "host/connectivity",
            {"status": "FAIL", "stderr": "SYNTHETIC SSH connection refused"},
        )
        bundle.stage("host", "FAIL", "SYNTHETIC unreachable")
        return
    bundle.stage("host", "PASS", "SYNTHETIC")
    bundle.write("host/overlay.json", f["overlay"])
    if scenario == "lepton-missing":
        bundle.stage("lepton", "FAIL", "SYNTHETIC lepton executable absent")
        return
    if scenario == "no-dev-context":
        bundle.stage("android", "NOT TESTED", "SYNTHETIC no dev context")
        return
    bundle.write("lepton/endpoints.json", parse_lepton_ps(f["lepton_ps"]))
    if scenario == "adb-unavailable":
        bundle.stage("android", "FAIL", "SYNTHETIC ADB missing")
        return
    bundle.write("android/identity.json", android_identity(f["getprop"], f["packages"]))
    bundle.write("android/properties.json", {"stdout": f["getprop"], "status": "PASS"})
    bundle.write("android/packages.json", {"stdout": f["packages"], "status": "PASS"})
    if scenario == "widevine-unsupported":
        d["widevine"] = {
            "supported": False,
            "construction": "UNSUPPORTED_SCHEME",
            "session": {"status": "NOT_TESTED"},
        }
    if scenario == "provisioning-required":
        d["widevine"]["session"] = {"status": "PROVISIONING_REQUIRED"}
    if scenario == "l1":
        d["widevine"]["properties"]["securityLevel"] = "L1"
        d["widevine"]["session"].update(
            security_level=5, security_level_name="HW_SECURE_ALL"
        )
        d["codecs"][0]["secure_playback"] = True
    if scenario == "software-only":
        d["codecs"][0].update(hardware_accelerated=False, software_only=True)
    bundle.write("android/diagnostics.json", d)
    bundle.write("drm/widevine.json", d["widevine"])
    bundle.write("codecs/advertised.json", d["codecs"])
    bundle.stage("android", "PASS", "SYNTHETIC")
    observations = {}
    if scenario == "panel-absent":
        observations = {"activity_rendered": "PASS", "video_visible": "FAIL"}
    if scenario == "protected-black":
        observations = {
            "clear_video": "PASS",
            "protected_video": "FAIL",
            "audio": "PASS",
        }
    if scenario in ("login-failed", "low-resolution"):
        s = service_template("disney")
        s.update(
            install="PASS",
            launch="PASS",
            login="FAIL" if scenario == "login-failed" else "PASS",
            notes="SYNTHETIC observation",
        )
        if scenario == "low-resolution":
            s.update(
                video_visible="PASS",
                actual_resolution={
                    "value": "854x480",
                    "evidence": "SYNTHETIC provider diagnostic",
                },
                quality="LOW",
            )
        bundle.write("services/disney.json", s)
        observations.update(s)
    bundle.write("android/observations.json", observations)
