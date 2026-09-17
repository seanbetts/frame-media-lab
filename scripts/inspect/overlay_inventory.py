#!/usr/bin/env python3
"""Read-only metadata inventory. Runs over SSH stdin; never writes to Frame."""

import hashlib
import json
import os
import pwd
import grp
import re
import stat
import subprocess
from pathlib import Path

CONCEPTS = re.compile(
    r"widevine|drm|oemcrypto|qsee|trustzone|keymint|keymaster|tee|codec|media|gralloc|allocator|mapper|hwcomposer|surface|vulkan|qualcomm|qti|adreno|secure|protected|openxr",
    re.I,
)
SECRET = re.compile(
    r"keybox|credential|provision|private|secret|token|cookie|account|persist|\.pem$|\.key$|\.p12$|\.db$",
    re.I,
)


def inventory(root, owners=True):
    root = Path(root)
    rows = []
    errors = []
    if not root.is_dir():
        return {
            "status": "NOT TESTED",
            "root": str(root),
            "files": [],
            "errors": ["Directory unavailable"],
        }
    for current, dirs, files in os.walk(root, followlinks=False):
        dirs.sort()
        files.sort()
        for name in sorted(dirs + files):
            p = Path(current) / name
            rel = str(p.relative_to(root))
            if len(rows) >= 20000:
                return {
                    "status": "PARTIAL",
                    "root": str(root),
                    "files": rows,
                    "errors": ["Inventory limit 20000 reached"],
                }
            try:
                s = p.lstat()
                regular = stat.S_ISREG(s.st_mode)
                safe = regular and not SECRET.search(rel)
                row = {
                    "path": rel,
                    "type": "file"
                    if regular
                    else "directory"
                    if stat.S_ISDIR(s.st_mode)
                    else "symlink"
                    if stat.S_ISLNK(s.st_mode)
                    else "special",
                    "size": s.st_size,
                    "permissions": stat.filemode(s.st_mode),
                    "uid": s.st_uid,
                    "gid": s.st_gid,
                    "sha256": None,
                    "package_owner": None,
                    "relevant": bool(CONCEPTS.search(rel)),
                    "hash_note": "Skipped: secret-like path or nonregular file"
                    if not safe
                    else "",
                }
                try:
                    row["owner"] = pwd.getpwuid(s.st_uid).pw_name
                except KeyError:
                    row["owner"] = str(s.st_uid)
                try:
                    row["group"] = grp.getgrgid(s.st_gid).gr_name
                except KeyError:
                    row["group"] = str(s.st_gid)
                if safe and s.st_size <= 512 * 1024 * 1024:
                    # O_NOFOLLOW closes the final-component symlink race; no content is exported.
                    fd = os.open(p, os.O_RDONLY | os.O_NOFOLLOW)
                    with os.fdopen(fd, "rb") as stream:
                        opened = os.fstat(stream.fileno())
                        if not stat.S_ISREG(opened.st_mode) or (
                            opened.st_dev,
                            opened.st_ino,
                        ) != (s.st_dev, s.st_ino):
                            raise OSError("File changed during inspection")
                        h = hashlib.sha256()
                        for block in iter(lambda: stream.read(1024 * 1024), b""):
                            h.update(block)
                        row["sha256"] = h.hexdigest()
                elif safe:
                    row["hash_note"] = "Skipped: file larger than 512 MiB"
                if owners:
                    try:
                        owner = subprocess.run(
                            ["pacman", "-Qo", "--", str(p)],
                            capture_output=True,
                            text=True,
                            timeout=2,
                        )
                        row["package_owner"] = (
                            owner.stdout.strip() if owner.returncode == 0 else None
                        )
                    except (OSError, subprocess.TimeoutExpired):
                        pass
                rows.append(row)
            except OSError as exc:
                errors.append({"path": rel, "error": str(exc)})
    return {
        "status": "PARTIAL" if errors else "PASS",
        "root": str(root),
        "files": rows,
        "errors": errors,
    }


if __name__ == "__main__":
    print(json.dumps(inventory("/usr/share/guestos/android"), sort_keys=True))
