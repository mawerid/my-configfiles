#!/usr/bin/env python3
import argparse
import base64
import hashlib
import io
import json
import os
import re
import shutil
import stat
import sys
import tarfile
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile, mkdtemp

SOURCE = Path(__file__).resolve().parents[1] / "config/herdr-app"
PREVIEW_LAYOUT = "layouts/files-preview.json"
ICONS = "mods/files-preview/icons"
# Shipped panels the generated layout swaps for this repo's copies.
LAYOUT_MODS = {
    "files": "files-preview",
    "spaces": "spaces-icons",
    "changes": "changes-diff",
}
ICON_PACKAGE = "https://registry.npmjs.org/material-icon-theme/latest"
ICON_TABLES = ("fileNames", "fileExtensions", "folderNames", "folderNamesExpanded")
SAFE_ICON = re.compile(r"[a-z0-9][a-z0-9_.-]*\.svg")


def fetch(url):
    with urllib.request.urlopen(url, timeout=60) as response:
        return response.read()


def icon_table(manifest, available):
    """Map lowercased names to SVG files, dropping icons the package lacks."""
    files = {
        name: Path(definition["iconPath"]).name
        for name, definition in manifest["iconDefinitions"].items()
    }

    def resolve(tables):
        table = {}
        for kind in ICON_TABLES:
            entries = {}
            for key, icon in tables.get(kind, {}).items():
                if files.get(icon) in available:
                    entries.setdefault(key.lower(), files[icon])
            table[kind] = entries
        return table

    table = resolve(manifest)
    for kind in ("file", "folder", "folderExpanded"):
        table[kind] = files[manifest[kind]]
    table["light"] = resolve(manifest.get("light", {}))
    return table


def unpack_icons(archive, integrity, version, staging):
    algorithm, _, digest = integrity.partition("-")
    if algorithm != "sha512" or hashlib.sha512(archive).digest() != base64.b64decode(
        digest
    ):
        raise ValueError("material-icon-theme checksum mismatch")
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as tar:
        manifest = json.load(tar.extractfile("package/dist/material-icons.json"))
        (staging / "LICENSE").write_bytes(tar.extractfile("package/LICENSE").read())
        for member in tar.getmembers():
            name = member.name.removeprefix("package/icons/")
            if name != member.name and member.isfile() and SAFE_ICON.fullmatch(name):
                (staging / name).write_bytes(tar.extractfile(member).read())
    table = icon_table(manifest, {path.name for path in staging.glob("*.svg")})
    table["version"] = version
    (staging / "icons.json").write_text(json.dumps(table), encoding="utf-8")


def install_icons(target):
    destination = target / ICONS
    if destination.is_symlink():
        raise ValueError(f"Invalid icon directory: {destination}")
    package = json.loads(fetch(ICON_PACKAGE))
    version = package["version"]
    try:
        installed = json.loads((destination / "icons.json").read_text(encoding="utf-8"))
        if installed.get("version") == version:
            print(f"Material icons {version} are current")
            return
    except (FileNotFoundError, ValueError):
        pass
    archive = fetch(package["dist"]["tarball"])
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(mkdtemp(prefix=".icons-", dir=destination.parent))
    try:
        unpack_icons(archive, package["dist"]["integrity"], version, staging)
        if destination.exists():
            old = Path(mkdtemp(prefix=".icons-old-", dir=destination.parent))
            destination.replace(old / "icons")
            staging.replace(destination)
            shutil.rmtree(old)
        else:
            staging.replace(destination)
    finally:
        shutil.rmtree(staging, ignore_errors=True)
    print(f"Installed material icons {version} to {destination}")


def preview_layout(target):
    source = target / "layouts/main.json"
    if source.parent.is_symlink() or source.is_symlink():
        raise ValueError(f"Invalid layout source: {source}")
    try:
        layout = json.loads(source.read_text(encoding="utf-8"))
    except FileNotFoundError:
        print("Open Herdr once, then rerun setup to add the Files Preview layout.")
        return None
    nodes, swapped = [layout], set()
    while nodes:
        node = nodes.pop()
        content = node.get("content", {})
        if content.get("mod") in LAYOUT_MODS:
            swapped.add(content["mod"])
            content["mod"] = LAYOUT_MODS[content["mod"]]
        nodes.extend(node.get("children", []))
    if "files" not in swapped:
        raise ValueError(f"No Files panel found in {source}")
    return (json.dumps(layout, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def install(target):
    paths = [
        "settings.json",
        "mods/files-preview/main.js",
        "mods/files-preview/mod.json",
        "mods/files-preview/html_server.py",
        "mods/spaces-icons/main.js",
        "mods/spaces-icons/mod.json",
        "mods/space-icon/main.js",
        "mods/space-icon/mod.json",
        "mods/changes-diff/main.js",
        "mods/changes-diff/mod.json",
        "mods/tmux-mode/main.js",
        "mods/tmux-mode/mod.json",
    ]
    files = {name: (SOURCE / name).read_bytes() for name in paths}
    # Herdr's own defaults for the platform plus the Ctrl-A tmux-mode bindings.
    keys = "keys.macos.json" if sys.platform == "darwin" else "keys.linux.json"
    files["keys.json"] = (SOURCE / keys).read_bytes()
    layout = preview_layout(target)
    if layout is not None:
        files[PREVIEW_LAYOUT] = layout

    pending = []
    for name, contents in files.items():
        path = target / name
        for parent in Path(name).parents:
            if parent != Path(".") and (target / parent).is_symlink():
                raise ValueError(f"Invalid destination parent: {target / parent}")
        try:
            mode = path.lstat().st_mode
        except FileNotFoundError:
            mode = None
        if mode is not None and not (stat.S_ISREG(mode) or stat.S_ISLNK(mode)):
            raise ValueError(f"Invalid destination: {path}")
        if mode is None or stat.S_ISLNK(mode) or path.read_bytes() != contents:
            pending.append((path, contents, mode is not None))

    backups = None
    if any(exists for _, _, exists in pending):
        backup_root = target / ".setup-backups"
        if backup_root.is_symlink():
            raise ValueError(f"Invalid backup directory: {backup_root}")
        backup_root.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        backups = Path(mkdtemp(prefix=f"{stamp}-", dir=backup_root))
    for path, contents, exists in pending:
        path.parent.mkdir(parents=True, exist_ok=True)
        if exists:
            backup = backups / path.relative_to(target)
            backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, backup, follow_symlinks=False)
            print(f"Backed up {path} to {backup}")
        staged = NamedTemporaryFile(dir=path.parent, delete=False)
        temporary = Path(staged.name)
        try:
            with staged:
                staged.write(contents)
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)
    print(f"Installed Herdr configuration to {target} ({len(pending)} files changed)")


def main():
    parser = argparse.ArgumentParser(
        description="Install the Herdr desktop app configuration."
    )
    parser.add_argument("--target-dir", type=Path, help="Override the Herdr app home")
    args = parser.parse_args()
    target = args.target_dir or Path(
        os.environ.get("HERDR_APP_HOME") or Path.home() / ".config/herdr-app"
    )
    try:
        install(target)
    except (OSError, ValueError) as error:
        sys.exit(f"Installation failed: {error}")
    try:
        install_icons(target)
    except (OSError, ValueError, KeyError, tarfile.TarError) as error:
        print(f"Warning: material icons not updated: {error}", file=sys.stderr)


if __name__ == "__main__":
    main()
