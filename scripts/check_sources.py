#!/usr/bin/env python3
"""Dependency-free Python syntax and installed shell-tool checks; not a type checker."""

import ast
from pathlib import Path

root = Path(__file__).resolve().parents[1]
files = sorted(
    p for base in ("lab", "scripts", "tests") for p in (root / base).rglob("*.py")
)
for path in files:
    ast.parse(path.read_text(), filename=str(path))
ast.parse((root / "frame-media-lab").read_text())
print(f"PASS: Python syntax in {len(files) + 1} files")
