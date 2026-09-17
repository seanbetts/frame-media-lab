#!/usr/bin/env python3
"""Read installation identity files selected by current Lepton source, without executing it."""

import json
import shutil
from pathlib import Path

exe = shutil.which("lepton")
result = {"executable": exe, "files": {}, "paths": {}, "status": "NOT TESTED"}
if exe:
    base = Path(exe).resolve().parent
    result["resolved_executable"] = str(Path(exe).resolve())
    for relative in ("version.txt", "images/version.txt"):
        p = base / relative
        try:
            if p.is_file() and p.stat().st_size < 65536:
                result["files"][relative] = p.read_text(errors="replace")
        except OSError as exc:
            result["files"][relative] = {"error": str(exc)}
    for relative in (
        "images/rootfs",
        "images/rootfs_overlay",
        "sysbake",
        "sysbake.xattrs",
    ):
        p = base / relative
        result["paths"][relative] = {"path": str(p), "exists": p.exists()}
    context = Path.home() / ".local/share/lepton/contexts"
    result["contexts"] = (
        [p.name for p in sorted(context.iterdir()) if p.is_dir()]
        if context.is_dir()
        else []
    )
    result["status"] = "PASS"
print(json.dumps(result, sort_keys=True))
