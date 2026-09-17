"""Exact-path/hash comparisons, with explicit limits on source versus binary evidence."""

import hashlib
import re
from pathlib import Path
from .core import Bundle

CONCEPT = re.compile(
    r"widevine|drm|oemcrypto|qsee|tee|codec|media|gralloc|allocator|mapper|hwcomposer|surface|vulkan|qti|qualcomm|secure|protected|openxr",
    re.I,
)


def compare_components(public, shipping, effective, mounts):
    p = {r["path"]: r for r in public}
    e = {r["path"]: r for r in effective}
    rows = []
    for s in shipping:
        key = s["path"]
        if not CONCEPT.search(key):
            continue
        base = p.get(key, {})
        guest = e.get(key, {})
        status = "UNKNOWN"
        if base.get("sha256") and s.get("sha256"):
            status = "SAME" if base["sha256"] == s["sha256"] else "DIFFERENT"
        sources = [m.get("source") for m in mounts if m.get("destination") == "/" + key]
        match = "UNKNOWN"
        if (
            len(sources) == 1
            and guest.get("sha256")
            and guest["sha256"] == s.get("sha256")
        ):
            match = "shipping overlay"
        rows.append(
            {
                "public_component": base.get("source", "No exact public-overlay file"),
                "shipping_component": key,
                "status": status,
                "sha256": s.get("sha256"),
                "public_sha256": base.get("sha256"),
                "effective_sha256": guest.get("sha256"),
                "package_owner": s.get("package_owner"),
                "mount_sources": sources,
                "effective_hash_matches": match,
                "notes": "Exact public overlay comparison only; source archive lacks built rootfs. Missing source file does not establish proprietary origin. Duplicate mounts/APEX namespaces require runtime evidence.",
            }
        )
    return rows


def compare(bundle: Bundle, source: Path):
    overlay = source / "compat_tool/images/rootfs_overlay"
    if not overlay.is_dir():
        raise ValueError(
            "Expected Lepton source archive with compat_tool/images/rootfs_overlay"
        )
    public = []
    for f in sorted(overlay.rglob("*")):
        if (
            f.is_file()
            and not f.is_symlink()
            and CONCEPT.search(str(f.relative_to(overlay)))
        ):
            public.append(
                {
                    "path": str(f.relative_to(overlay)),
                    "sha256": hashlib.sha256(f.read_bytes()).hexdigest(),
                    "source": str(f.relative_to(source)),
                }
            )
    rows = compare_components(
        public,
        bundle.read("host/overlay.json", {}).get("files", []),
        bundle.read("android/effective-components.json", []),
        bundle.read("lepton/mount-map.json", []),
    )
    bundle.write("lepton/comparison.json", rows)
    return rows
