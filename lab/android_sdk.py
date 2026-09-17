"""Shared local SDK lookup; never changes PATH, installs tools, or contacts devices."""

import os
from pathlib import Path
import shutil

SDK_TOOLS = {
    "adb": "platform-tools/adb",
    "sdkmanager": "cmdline-tools/latest/bin/sdkmanager",
    **{
        name: "build-tools/35.0.0/" + name
        for name in ("aapt", "aapt2", "d8", "zipalign", "apksigner")
    },
}


def find_sdk(explicit=None):
    override = explicit or os.environ.get("FML_ANDROID_SDK")
    candidates = (
        [override]
        if override
        else [
            os.environ.get("ANDROID_HOME"),
            os.environ.get("ANDROID_SDK_ROOT"),
            Path.home() / "Library/Android/sdk",
            Path.home() / "Android/Sdk",
        ]
    )
    return next(
        (
            Path(p).expanduser().resolve()
            for p in candidates
            if p and Path(p).expanduser().is_dir()
        ),
        None,
    )


def tool_path(name):
    sdk = find_sdk() if name in SDK_TOOLS else None
    if sdk is not None:
        path = sdk / SDK_TOOLS[name]
        if path.is_file() and os.access(path, os.X_OK):
            return str(path)
    return shutil.which(name)
