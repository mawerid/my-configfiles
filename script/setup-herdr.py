#!/usr/bin/env python3
import argparse
import json
import os
import shutil
import stat
import sys
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile, mkdtemp

SOURCE = Path(__file__).resolve().parents[1] / "config/herdr-app"
PREVIEW_LAYOUT = "layouts/files-preview.json"


def preview_layout(target):
    source = target / "layouts/main.json"
    if source.parent.is_symlink() or source.is_symlink():
        raise ValueError(f"Invalid layout source: {source}")
    try:
        layout = json.loads(source.read_text(encoding="utf-8"))
    except FileNotFoundError:
        print("Open Herdr once, then rerun setup to add the Files Preview layout.")
        return None
    nodes = [layout]
    while nodes:
        node = nodes.pop()
        content = node.get("content", {})
        if node.get("id") == "files" and content.get("mod") == "files":
            content["mod"] = "files-preview"
            return (json.dumps(layout, ensure_ascii=False, indent=2) + "\n").encode(
                "utf-8"
            )
        nodes.extend(node.get("children", []))
    raise ValueError(f"No Files panel found in {source}")


def install(target):
    paths = [
        "settings.json",
        "mods/files-preview/main.js",
        "mods/files-preview/mod.json",
    ]
    if sys.platform == "darwin":
        paths.extend(("mods/tmux-mode/main.js", "mods/tmux-mode/mod.json"))
    files = {name: (SOURCE / name).read_bytes() for name in paths}
    if sys.platform == "darwin":
        files["keys.json"] = (SOURCE / "keys.macos.json").read_bytes()
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


if __name__ == "__main__":
    main()
