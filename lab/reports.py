"""Evidence-led summaries: advertisements and window sizes never become playback facts."""

from __future__ import annotations

import re
from .core import Bundle, redact

SERVICES = {
    "disney": "Disney+",
    "apple": "Apple TV",
    "hbo": "HBO Max",
    "netflix": "Netflix",
    "youtube": "YouTube",
}
FIELDS = [
    "install",
    "launch",
    "login",
    "catalog",
    "drm_session",
    "licence",
    "decoder",
    "video_visible",
    "audio",
    "hdr",
]
BASELINE = {
    "Netflix": ["1920x1080", "1920x1080", "1920x1080"],
    "Disney+": ["854x480", "854x480", "1920x1080"],
    "HBO Max": ["1024x576", "1024x576", "1920x1080"],
    "Apple TV": ["playback fails", "playback fails", "~3840x1920"],
    "YouTube": ["3840x2160", "NOT TESTED", "NOT TESTED"],
}


def service_template(key):
    return {
        "service": SERVICES[key],
        **{f: "NOT TESTED" for f in FIELDS},
        "actual_resolution": {"value": "UNKNOWN", "evidence": "NOT TESTED"},
        "source_resolution": "UNKNOWN",
        "android_window_resolution": "UNKNOWN",
        "steamvr_panel_resolution": "UNKNOWN",
        "package_version": "UNKNOWN",
        "title": "UNKNOWN",
        "subscription_tier": "UNKNOWN",
        "region": "UNKNOWN",
        "quality_setting": "UNKNOWN",
        "quality": "UNKNOWN",
        "protected_content": "UNKNOWN",
        "duration_seconds": 0,
        "notes": "",
    }


def assess_drm(data):
    session = data.get("session", {})
    status = session.get("status", "NOT TESTED")
    return {
        "supported": data.get("supported", "UNKNOWN"),
        "support_query_status": data.get("support_query_status", "NOT TESTED"),
        "support_query_error": data.get("support_query_error"),
        "construction": data.get("construction", "NOT TESTED"),
        "construction_error": data.get("error"),
        "properties": data.get("properties", {}),
        "session_status": status,
        "actual_session": session.get("security_level_name", "UNKNOWN")
        if status == "OPENED"
        else "NOT TESTED",
        "provisioning": "PROVISIONING REQUIRED"
        if status == "PROVISIONING_REQUIRED"
        else "No provisioning attempt made by toolkit",
        "hdcp": {
            "connected_level": data.get("connected_hdcp_level", "UNKNOWN"),
            "maximum_level": data.get("max_hdcp_level", "UNKNOWN"),
            "error": data.get("hdcp_error"),
        },
        "protected_playback": "NOT TESTED",
    }


def classify(observed):
    labels = []
    for field, label in [
        ("install", "APK INSTALLATION FAILED"),
        ("launch", "ACTIVITY FAILED"),
        ("login", "LOGIN FAILED"),
        ("licence", "LICENCE REJECTED"),
        ("secure_decoder", "SECURE DECODER UNAVAILABLE"),
        ("protected_allocation", "PROTECTED ALLOCATION FAILED"),
        ("protected_import", "PROTECTED IMPORT FAILED"),
    ]:
        if observed.get(field) == "FAIL":
            labels.append(label)
    if observed.get("widevine_supported") is False:
        labels.append("WIDEVINE UNSUPPORTED")
    if observed.get("session_status") == "PROVISIONING_REQUIRED":
        labels.append("PROVISIONING REQUIRED")
    if (
        observed.get("activity_rendered") == "PASS"
        and observed.get("video_visible") == "FAIL"
    ):
        labels.append("HOST PANEL ABSENT")
    if (
        observed.get("protected_video") == "FAIL"
        or (
            observed.get("protected_content") == "PASS"
            and observed.get("video_visible") == "FAIL"
        )
    ) and observed.get("audio") == "PASS":
        labels.append("PROTECTED VIDEO BLACK")
    if (
        observed.get("video_visible") == "PASS"
        and observed.get("screenshot_video") == "FAIL"
    ):
        labels.append("POSSIBLE CAPTURE PROTECTION")
    if observed.get("quality") == "LOW":
        labels.append("PLAYBACK AT LOW QUALITY")
    if observed.get("quality") in ("HD", "4K") and observed.get(
        "actual_resolution", {}
    ).get("evidence") not in (None, "", "UNKNOWN", "NOT TESTED"):
        labels.append("OBSERVED " + observed["quality"] + " SOURCE PLAYBACK")
    return labels or ["NO FAILURE BOUNDARY ESTABLISHED"]


def priority(drm, codecs):
    if drm.get("supported") is False:
        return [
            "YouTube clear uploads: validate native clear playback; DRM service tests remain useful only to identify rejection boundaries.",
            "Disney+ / Apple TV / HBO Max after a legitimate DRM implementation is established.",
        ]
    if not any(c.get("hardware_accelerated") for c in codecs):
        return [
            "Clear H.264 performance first; hardware decode has not been established.",
            "Then Disney+, Apple TV, HBO Max; record actual service quality.",
        ]
    return [
        "Disney+, Apple TV, HBO Max: greatest gap from the measured Chrome baseline.",
        "Netflix Android may underperform browser 1080p if only software-secure sessions are available.",
        "YouTube clear uploads are useful for decode/input comparisons; premium titles are a separate DRM test.",
    ]


def render_report(bundle: Bundle) -> dict:
    diag = bundle.read("android/diagnostics.json", {})
    if diag and diag.get("synthetic") != bundle.metadata["synthetic"]:
        raise ValueError("Evidence provenance mismatch")
    drm = assess_drm(diag.get("widevine", bundle.read("drm/widevine.json", {})))
    codecs = diag.get("codecs", bundle.read("codecs/advertised.json", []))
    services = []
    for key in SERVICES:
        s = service_template(key)
        s.update(bundle.read("services/" + key + ".json", {}))
        services.append(s)
    observations = bundle.read("android/observations.json", {})
    media = bundle.read("media/playback.json", {})
    expected = bundle.read("media/expected-launch.json", {}).get("launch_id")
    if expected and media.get("launch_id") != expected:
        media = {
            "status": "NOT TESTED",
            "reason": "Previous playback belongs to a different launch; fresh completed export unavailable",
        }
    comparison = bundle.read("lepton/comparison.json", [])
    measured = (
        media.get("video_actually_used") is True
        and isinstance(media.get("video_output_width"), int)
        and isinstance(media.get("video_output_height"), int)
    )
    tested = {
        "decoder": media.get("video_decoder", "UNKNOWN"),
        "resolution": str(media["video_output_width"])
        + "x"
        + str(media["video_output_height"])
        if measured
        else "NOT TESTED",
        "result": "DECODED OUTPUT OBSERVED" if measured else "NOT TESTED",
        "headset_visibility": observations.get("clear_video", "NOT TESTED"),
    }
    diagnostic_observations = {
        "widevine_supported": drm["supported"],
        "session_status": drm["session_status"],
    }
    classifications = classify({**observations, **diagnostic_observations})
    facts = []
    if drm["session_status"] == "OPENED":
        facts.append(
            "Diagnostic app opened a Widevine session reporting "
            + str(drm["actual_session"])
            + ". This is an API observation, not a service-playback result."
        )
    if drm["supported"] is False:
        facts.append(
            "MediaDrm reported Widevine UUID unsupported in the sampled environment."
        )
    if diag:
        facts.append(
            "Diagnostic export timestamp: "
            + str(diag.get("timestamp", "UNKNOWN"))
            + "; run_id: "
            + str(diag.get("run_id", "UNKNOWN"))
        )
    data = {
        "schema_version": 1,
        "synthetic": bundle.metadata["synthetic"],
        "privacy": bundle.metadata["privacy"],
        "device": {
            "host": bundle.metadata.get("frame", {}),
            "android": bundle.read("android/identity.json", {}),
            "probe_device": diag.get("device", {}),
        },
        "lepton": {
            "installed": bundle.read("lepton/installed-identity.json", {}),
            "container_image": bundle.read("lepton/identity.json", {}).get(
                "stdout", "UNKNOWN"
            ),
            "stages": bundle.metadata["stages"],
            "mounts": bundle.read("lepton/mount-map.json", []),
            "identity": bundle.read("host/lepton-identity.json", {}).get(
                "stdout", "UNKNOWN"
            ),
        },
        "overlay": {
            "inventory_status": bundle.read("host/overlay.json", {}).get(
                "status", "NOT TESTED"
            ),
            "files": len(bundle.read("host/overlay.json", {}).get("files", [])),
            "comparison": comparison,
        },
        "drm": drm,
        "clearkey": diag.get("clearkey", {"status": "NOT TESTED"}),
        "codecs": codecs,
        "flatscreen": observations,
        "clear_video": media,
        "protected_pipeline": {
            "allocation": "UNKNOWN",
            "hwc_import": "UNKNOWN",
            "host_compositor": "UNKNOWN",
            "playback": observations.get("protected_video", "NOT TESTED"),
        },
        "tested_decode": tested,
        "services": services,
        "browser_baseline": BASELINE,
        "classifications": classifications,
        "service_classifications": {s["service"]: classify(s) for s in services},
        "recommended_next_tests": priority(drm, codecs),
        "conclusions": {
            "FACT": facts or ["No device capability has been measured."],
            "INFERENCE": [
                "Component names and codec advertisements guide the next test; they do not prove secure media or resolution."
            ],
            "UNKNOWN": [
                "Enforced protected allocation/import and complete trusted presentation path.",
                "Provider acceptance, actual per-service source resolution, HDR, audio sync, power and thermals unless separately observed.",
            ],
        },
        "errors": bundle.metadata["errors"],
    }
    if data["synthetic"]:
        data["conclusions"]["FACT"] = [
            "SYNTHETIC simulation: " + item for item in data["conclusions"]["FACT"]
        ]
    data = redact(data)
    bundle.write("report.json", data)
    lines = [
        "# Steam Frame Media Diagnostic Report",
        "",
        "**SYNTHETIC FIXTURE — NOT FRAME EVIDENCE**"
        if data["synthetic"]
        else "**LIVE COLLECTION — capabilities require the evidence below**",
        "",
        "**REDACTED / REVIEW BEFORE SHARING.** Only report.md and report.json form the report; inspect free-text observations before sharing.",
        "",
        "## Device",
        str(data["device"]["host"].get("os_release", "SteamOS: NOT TESTED")),
        str(data["device"]["host"].get("uname", "Hardware: NOT TESTED")),
    ]
    props = data["device"]["android"].get("properties", {})
    lines += ["", "| Android property | Observed value |", "|---|---|"] + [
        f"| {k} | {cell(v)} |" for k, v in props.items()
    ]
    if not props:
        lines.append("| Android baseline | NOT TESTED |")
    lines += [
        "",
        "## Lepton Environment",
        cell(data["lepton"]["identity"]),
        "Installed build versions: "
        + cell(data["lepton"]["installed"].get("files", "NOT TESTED")),
        "Container image identity: " + cell(data["lepton"]["container_image"]),
        "",
        "Container mount records: "
        + str(len(data["lepton"]["mounts"]))
        + ". Overlay precedence remains UNKNOWN until matched to effective guest hashes and the consuming process mount namespace.",
        "",
        "| Stage | Status | Notes |",
        "|---|---|---|",
    ]
    lines += [
        f"| {cell(k)} | {cell(v['status'])} | {cell(v.get('notes', ''))} |"
        for k, v in data["lepton"]["stages"].items()
    ]
    lines += [
        "",
        "## Host-supplied Android Components",
        f"Inventory: {data['overlay']['inventory_status']}; entries: {data['overlay']['files']}.",
        "",
        "| Public component | Shipping component | Comparison | Hash | Package owner | Effective hash match |",
        "|---|---|---|---|---|---|",
    ]
    lines += [
        f"| {cell(r['public_component'])} | {cell(r['shipping_component'])} | {r['status']} | {cell(r['sha256'])} | {cell(r['package_owner'])} | {cell(r['effective_hash_matches'])} |"
        for r in comparison
    ]
    lines += [
        "",
        "No exact source-overlay counterpart means UNKNOWN, not proof of a proprietary binary. This archive does not contain a built base rootfs.",
        "",
        "## DRM",
        f"- Widevine UUID support: {drm['supported']}",
        f"- Plugin construction: {drm['construction']}",
        f"- Session: {drm['session_status']}; actual API security level: {drm['actual_session']}",
        f"- Provisioning: {drm['provisioning']}",
        "- Properties (advertised): " + cell(drm["properties"]),
        "- HDCP: " + cell(drm["hdcp"]),
        "- ClearKey: " + cell(data["clearkey"]),
        "- Successful authorised protected playback: "
        + cell(data["protected_pipeline"]["playback"]),
        "",
        "An advertised L1 property is not an actual session result. Even HW_SECURE_ALL does not establish end-to-end authorised service playback.",
        "",
        "## Video Decode",
        "| Decoder | MIME | Hardware advertised | Secure advertised | Max tested resolution | Result |",
        "|---|---|---|---|---|---|",
    ]
    lines += [
        f"| {cell(c.get('name'))} | {cell(c.get('mime'))} | {cell(c.get('hardware_accelerated', 'UNKNOWN'))} | {cell(c.get('secure_playback', 'UNKNOWN'))} | {tested['resolution'] if c.get('name') == tested['decoder'] else 'NOT TESTED'} | {tested['result'] if c.get('name') == tested['decoder'] else 'ADVERTISED ONLY'} |"
        for c in codecs
    ]
    if not codecs:
        lines.append("| NOT TESTED | | | | NOT TESTED | NOT TESTED |")
    lines += ["", "Selected decoder test: " + cell(tested)]
    lines += [
        "",
        "## Protected Video Pipeline",
        cell(data["protected_pipeline"]),
        "",
        "## 2D Android Test",
        *details_table(observations),
        "",
        "## Clear Video",
        *details_table(media),
        "",
        "A supplied/decoded source size, Android window size and SteamVR panel size are separate measurements. Sustained efficiency and visible/audible output require physical observation.",
        "",
        "## Streaming Services",
        "| Service | Install | Launch | Login | Catalog | DRM session | Licence | Decoder | Video | Actual source resolution | Audio | HDR | Notes |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for s in services:
        lines.append(
            "| "
            + " | ".join(
                cell(x)
                for x in [
                    s["service"],
                    s["install"],
                    s["launch"],
                    s["login"],
                    s["catalog"],
                    s["drm_session"],
                    s["licence"],
                    s["decoder"],
                    s["video_visible"],
                    s["actual_resolution"],
                    s["audio"],
                    s["hdr"],
                    s["notes"],
                ]
            )
            + " |"
        )
    lines += [
        "",
        "## Browser Baseline Comparison",
        "User-provided prior measurements, not Frame tests. Chrome reported Software Secure; Bazzite hardware decoding and Windows user-agent spoofing did not improve Disney+.",
        "",
        "| Service | Bazzite Chrome | macOS Chrome | macOS Safari | Frame actual resolution |",
        "|---|---|---|---|---|",
    ]
    for s in services:
        lines.append(
            "| "
            + " | ".join(
                [s["service"]] + BASELINE[s["service"]] + [cell(s["actual_resolution"])]
            )
            + " |"
        )
    lines += ["", "## Conclusions"]
    for label, items in data["conclusions"].items():
        lines.extend([""] + [f"- **{label}:** {x}" for x in items])
    lines += [
        "",
        "Failure boundaries: " + ", ".join(data["classifications"]),
        "",
        "Service failure boundaries: " + cell(data["service_classifications"]),
        "",
        "Next tests:",
    ] + ["- " + x for x in data["recommended_next_tests"]]
    lines += ["", "## Collection Errors"] + (
        ["- " + cell(e) for e in data["errors"]]
        or ["None recorded. Skipped/NOT TESTED stages are listed separately."]
    )
    (bundle.path / "report.md").write_text(
        re.sub(
            r"(?m)^(## .+)\n(?=\S)", r"\1\n\n", "\n".join(str(redact(x)) for x in lines)
        )
        + "\n"
    )
    return data


def cell(value):
    if isinstance(value, dict):
        value = "; ".join(str(k) + ": " + cell(v) for k, v in value.items())
    elif isinstance(value, list):
        value = ", ".join(cell(v) for v in value)
    return (
        str(value if value is not None else "UNKNOWN")
        .replace("|", "\\|")
        .replace("\n", "; ")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def details_table(values):
    if not values:
        return ["NOT TESTED"]
    return ["| Measurement | Evidence |", "|---|---|"] + [
        f"| {cell(k)} | {cell(v)} |" for k, v in values.items()
    ]
