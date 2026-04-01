#!/usr/bin/env python3
"""
tix_packager.py — CLI tool to create .tix extension packages.

Usage:
    python tix_packager.py pack   <extension_dir> [--out <output.tix>]
    python tix_packager.py verify <file.tix>
    python tix_packager.py info   <file.tix>

A .tix file is a ZIP archive containing at minimum:
    manifest.json   — extension metadata
    plugin.py       — Plugin(ExtensionBase) class

Example:
    python tix_packager.py pack taara_ide/extensions/builtin/remote_ssh
    → Produces:  remote-ssh-1.0.0.tix
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import zipfile
from pathlib import Path

# ── Required / optional files ─────────────────────────────────────────────────
_REQUIRED = {"manifest.json", "plugin.py"}
_SKIP_PATTERNS = {
    "__pycache__",
    ".pyc",
    ".pyo",
    ".git",
    ".DS_Store",
    "Thumbs.db",
}

MANIFEST_REQUIRED_FIELDS = ("id", "name", "version", "description")


def _should_skip(path: str) -> bool:
    for pat in _SKIP_PATTERNS:
        if pat in path:
            return True
    return False


# ── pack ──────────────────────────────────────────────────────────────────────

def cmd_pack(args) -> int:
    src = Path(args.source).resolve()
    if not src.is_dir():
        print(f"[error] Not a directory: {src}", file=sys.stderr)
        return 1

    manifest_path = src / "manifest.json"
    if not manifest_path.is_file():
        print(f"[error] manifest.json not found in {src}", file=sys.stderr)
        return 1

    try:
        with open(manifest_path, encoding="utf-8") as fh:
            manifest = json.load(fh)
    except Exception as exc:
        print(f"[error] Cannot parse manifest.json: {exc}", file=sys.stderr)
        return 1

    for field in MANIFEST_REQUIRED_FIELDS:
        if not manifest.get(field):
            print(f"[error] manifest.json is missing required field '{field}'", file=sys.stderr)
            return 1

    plugin_path = src / "plugin.py"
    if not plugin_path.is_file():
        print(f"[error] plugin.py not found in {src}", file=sys.stderr)
        return 1

    ext_id   = manifest["id"]
    version  = manifest["version"]

    if args.out:
        out_path = Path(args.out)
    else:
        out_path = Path(f"{ext_id}-{version}.tix")

    file_list = []
    for root, dirs, files in os.walk(src):
        # Skip hidden / cache dirs in-place
        dirs[:] = [d for d in dirs if not _should_skip(d)]
        for fname in files:
            abs_path = Path(root) / fname
            rel_path = abs_path.relative_to(src)
            if not _should_skip(str(rel_path)):
                file_list.append((abs_path, str(rel_path)))

    with zipfile.ZipFile(out_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for abs_path, rel_str in file_list:
            zf.write(abs_path, rel_str)
            print(f"  added  {rel_str}")

    size_kb = out_path.stat().st_size / 1024
    print(f"\nPacked {len(file_list)} files -> {out_path}  ({size_kb:.1f} KB)")
    return 0


# ── verify ────────────────────────────────────────────────────────────────────

def cmd_verify(args) -> int:
    tix = Path(args.file)
    if not tix.is_file():
        print(f"[error] File not found: {tix}", file=sys.stderr)
        return 1

    if not zipfile.is_zipfile(tix):
        print(f"[error] Not a valid ZIP/tix file: {tix}", file=sys.stderr)
        return 1

    with zipfile.ZipFile(tix, "r") as zf:
        names = set(zf.namelist())

        missing = _REQUIRED - names
        if missing:
            print(f"[error] Missing required files: {', '.join(sorted(missing))}", file=sys.stderr)
            return 1

        try:
            manifest = json.loads(zf.read("manifest.json").decode("utf-8"))
        except Exception as exc:
            print(f"[error] Cannot parse manifest.json: {exc}", file=sys.stderr)
            return 1

        errors = []
        for field in MANIFEST_REQUIRED_FIELDS:
            if not manifest.get(field):
                errors.append(f"  missing field '{field}' in manifest.json")

        if errors:
            for e in errors:
                print(e, file=sys.stderr)
            return 1

    print(f"[ok] {tix}  —  id={manifest['id']}  version={manifest['version']}")
    return 0


# ── info ──────────────────────────────────────────────────────────────────────

def cmd_info(args) -> int:
    tix = Path(args.file)
    if not tix.is_file():
        print(f"[error] File not found: {tix}", file=sys.stderr)
        return 1

    if not zipfile.is_zipfile(tix):
        print(f"[error] Not a valid ZIP/tix file: {tix}", file=sys.stderr)
        return 1

    with zipfile.ZipFile(tix, "r") as zf:
        if "manifest.json" not in zf.namelist():
            print("[error] manifest.json not found in archive", file=sys.stderr)
            return 1
        manifest = json.loads(zf.read("manifest.json").decode("utf-8"))
        contents = sorted(zf.namelist())

    print(f"Extension:   {manifest.get('name', '?')}  ({manifest.get('id', '?')})")
    print(f"Version:     {manifest.get('version', '?')}")
    print(f"Description: {manifest.get('description', '')}")
    print(f"Author:      {manifest.get('author', '')}")
    print(f"Category:    {manifest.get('category', '')}")
    print(f"Min IDE:     {manifest.get('minIdeVersion', '')}")
    deps = manifest.get("dependencies", [])
    if deps:
        print(f"Depends on:  {', '.join(deps)}")
    print(f"\nContents ({len(contents)} files):")
    for name in contents:
        print(f"  {name}")
    return 0


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        prog="tix_packager",
        description="Create and inspect .tix extension packages for Taara IDE",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_pack = sub.add_parser("pack", help="Pack a directory into a .tix file")
    p_pack.add_argument("source", help="Extension source directory")
    p_pack.add_argument("--out", metavar="FILE", help="Output .tix path (default: <id>-<ver>.tix)")

    p_verify = sub.add_parser("verify", help="Verify a .tix file is well-formed")
    p_verify.add_argument("file", help=".tix file to verify")

    p_info = sub.add_parser("info", help="Show metadata and contents of a .tix file")
    p_info.add_argument("file", help=".tix file to inspect")

    args = parser.parse_args()

    dispatch = {"pack": cmd_pack, "verify": cmd_verify, "info": cmd_info}
    sys.exit(dispatch[args.command](args))


if __name__ == "__main__":
    main()
