"""Bounded ZIP + binary Android XML metadata inspection; no APK code execution."""

from __future__ import annotations
import hashlib
import io
import struct
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

ANDROID = "{http://schemas.android.com/apk/res/android}"


def xml_tree(data: bytes) -> ET.Element:
    if len(data) > 8 * 1024 * 1024:
        raise ValueError("Manifest exceeds 8 MiB limit")
    if data.lstrip().startswith(b"<"):
        if b"<!DOCTYPE" in data.upper() or b"<!ENTITY" in data.upper():
            raise ValueError("DTD/entity declarations not accepted")
        return ET.fromstring(data)

    def u16(p):
        return struct.unpack_from("<H", data, p)[0]

    def u32(p):
        return struct.unpack_from("<I", data, p)[0]

    if len(data) < 8 or u16(0) != 3 or u32(4) != len(data):
        raise ValueError("Invalid binary XML header")
    strings = []
    stack = []
    root = None
    offset = u16(2)

    def string(i):
        if i == 0xFFFFFFFF:
            return ""
        if i >= len(strings):
            raise ValueError("Invalid string index")
        return strings[i]

    try:
        while offset < len(data):
            kind, header, size = struct.unpack_from("<HHI", data, offset)
            if size < header or header < 8 or offset + size > len(data):
                raise ValueError("Invalid XML chunk size")
            if kind == 1:
                count = u32(offset + 8)
                flags = u32(offset + 16)
                start = offset + u32(offset + 20)
                if count > 100000 or offset + header + count * 4 > offset + size:
                    raise ValueError("Invalid string pool")
                strings = []
                for i in range(count):
                    pos = start + u32(offset + header + i * 4)

                    def length8(p):
                        n = data[p]
                        return (
                            (((n & 127) << 8) | data[p + 1], p + 2)
                            if n & 128
                            else (n, p + 1)
                        )

                    def length16(p):
                        n = u16(p)
                        return (
                            (((n & 32767) << 16) | u16(p + 2), p + 4)
                            if n & 32768
                            else (n, p + 2)
                        )

                    if flags & 256:
                        _, pos = length8(pos)
                        n, pos = length8(pos)
                        end = pos + n
                        encoding = "utf-8"
                    else:
                        n, pos = length16(pos)
                        end = pos + n * 2
                        encoding = "utf-16le"
                    if end > offset + size:
                        raise ValueError("String outside pool")
                    strings.append(data[pos:end].decode(encoding, errors="replace"))
            elif kind == 0x102:
                ext = offset + header
                name = string(u32(ext + 4))
                node = ET.Element(name)
                attr_start = u16(ext + 8)
                attr_size = u16(ext + 10)
                count = u16(ext + 12)
                if (
                    attr_size < 20
                    or ext + attr_start + attr_size * count > offset + size
                ):
                    raise ValueError("Invalid attributes")
                for i in range(count):
                    pos = ext + attr_start + i * attr_size
                    ns = string(u32(pos))
                    key = string(u32(pos + 4))
                    raw = u32(pos + 8)
                    dtype = data[pos + 15]
                    val = u32(pos + 16)
                    value = (
                        string(raw)
                        if raw != 0xFFFFFFFF
                        else string(val)
                        if dtype == 3
                        else ("true" if val else "false")
                        if dtype == 18
                        else "@0x%08x" % val
                        if dtype in (1, 2)
                        else str(val)
                    )
                    node.set("{" + ns + "}" + key if ns else key, value)
                if stack:
                    stack[-1].append(node)
                elif root is not None:
                    raise ValueError("Multiple roots")
                else:
                    root = node
                stack.append(node)
            elif kind == 0x103:
                if not stack:
                    raise ValueError("Unbalanced XML")
                stack.pop()
            offset += size
        if root is None or stack:
            raise ValueError("Incomplete XML")
        return root
    except (IndexError, struct.error) as exc:
        raise ValueError("Truncated binary XML") from exc


def parse_manifest(data: bytes) -> dict:
    root = xml_tree(data)
    package = root.get("package", "UNKNOWN")

    def attr(node, key, default=None):
        return node.get(ANDROID + key, default)

    def full(name):
        return (
            package + name
            if name.startswith(".")
            else package + "." + name
            if "." not in name
            else name
        )

    sdk = root.find("uses-sdk")
    app = root.find("application")
    activities = []
    aliases = []
    launchers = []
    links = []
    for node in list(app) if app is not None else []:
        if node.tag not in ("activity", "activity-alias"):
            continue
        name = full(attr(node, "name", "UNKNOWN"))
        filters = []
        for f in node.findall("intent-filter"):
            actions = [attr(n, "name") for n in f.findall("action")]
            cats = [attr(n, "name") for n in f.findall("category")]
            datas = [
                {k.removeprefix(ANDROID): v for k, v in n.attrib.items()}
                for n in f.findall("data")
            ]
            filters.append({"actions": actions, "categories": cats, "data": datas})
            links.extend({"activity": name, **d} for d in datas)
            if "android.intent.action.MAIN" in actions and any(
                c in cats
                for c in (
                    "android.intent.category.LAUNCHER",
                    "android.intent.category.LEANBACK_LAUNCHER",
                )
            ):
                launchers.append(package + "/" + name)
        item = {
            "name": name,
            "exported": attr(node, "exported", "SDK-dependent default"),
            "enabled": attr(node, "enabled", "true"),
            "intent_filters": filters,
        }
        if node.tag == "activity-alias":
            item["target"] = full(attr(node, "targetActivity", "UNKNOWN"))
            aliases.append(item)
        else:
            activities.append(item)
    uses_splits = [attr(n, "name") for n in root.findall("uses-split")]
    metadata = (
        [
            {k.removeprefix(ANDROID): v for k, v in n.attrib.items()}
            for n in app.findall("meta-data")
        ]
        if app is not None
        else []
    )
    return {
        "package": package,
        "version_name": attr(root, "versionName"),
        "version_code": attr(root, "versionCode"),
        "min_sdk": attr(sdk, "minSdkVersion", "1") if sdk is not None else "1",
        "target_sdk": attr(sdk, "targetSdkVersion", "UNKNOWN")
        if sdk is not None
        else "UNKNOWN",
        "split": root.get("split"),
        "uses_splits": uses_splits,
        "split_required": attr(root, "isSplitRequired", "UNKNOWN"),
        "split_metadata": [m for m in metadata if "split" in str(m).lower()],
        "permissions": [
            attr(n, "name") for n in root if n.tag.startswith("uses-permission")
        ],
        "features": [
            {k.removeprefix(ANDROID): v for k, v in n.attrib.items()}
            for n in root.findall("uses-feature")
        ],
        "activities": activities,
        "activity_aliases": aliases,
        "launchers": sorted(set(launchers)),
        "deep_links": links,
    }


def inspect_zip(z: zipfile.ZipFile) -> dict:
    infos = z.infolist()
    if len(infos) > 100000:
        raise ValueError("APK has excessive ZIP entries")
    manifest = z.getinfo("AndroidManifest.xml")
    if manifest.file_size > 8 * 1024 * 1024:
        raise ValueError("Manifest too large")
    result = parse_manifest(z.read(manifest))
    names = [i.filename for i in infos]
    libs = sorted(n for n in names if n.startswith("lib/") and n.endswith(".so"))
    result.update(
        native_libraries=libs,
        abis=sorted({n.split("/")[1] for n in libs if len(n.split("/")) > 2}),
        gms_reference_detected=False,
        media_references=[],
    )
    patterns = {
        b"com/google/android/gms": "GMS",
        b"com.google.android.gms": "GMS",
        b"android/media/MediaDrm": "MediaDrm",
        b"android/media/MediaCodec": "MediaCodec",
        b"widevine": "Widevine string",
        b"exoplayer": "ExoPlayer string",
        b"media3": "Media3 string",
    }
    refs = set()
    for info in infos:
        if info.filename.endswith(".dex") and info.file_size <= 64 * 1024 * 1024:
            content = z.read(info)
            refs.update(
                label for pattern, label in patterns.items() if pattern in content
            )
    result["gms_reference_detected"] = "GMS" in refs
    result["media_references"] = sorted(refs - {"GMS"})
    result["limitations"] = [
        "References are hints, not runtime dependency proofs; obfuscation and dynamic loading can hide them.",
        "Resource IDs are not resolved; signature consistency and device-compatible split selection require Android tools/installer.",
        "No account, DRM credential or licence data is inspected.",
    ]
    return result


def inspect_apk(path: Path) -> dict:
    if not path.is_file():
        raise ValueError("APK path does not exist")
    with zipfile.ZipFile(path) as z:
        if path.suffix.lower() in (".apks", ".xapk"):
            members = [i for i in z.infolist() if i.filename.endswith(".apk")]
            if len(members) > 200:
                raise ValueError("APK set has more than 200 members")
            results = []
            for info in members:
                if info.file_size > 256 * 1024 * 1024:
                    raise ValueError("Nested APK exceeds 256 MiB inspection limit")
                with zipfile.ZipFile(io.BytesIO(z.read(info))) as nested:
                    results.append({"member": info.filename, **inspect_zip(nested)})
            return {
                "kind": "APK SET",
                "members": results,
                "installation": "Select the matching base and required splits explicitly; do not install every variant.",
            }
        result = inspect_zip(z)
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return {"filename": path.name, "sha256": h.hexdigest(), **result}
