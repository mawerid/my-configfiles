#!/usr/bin/env python3
import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SETTINGS = {"codex": "config.toml", "claude": "settings.json"}
LEGACY = {"codex": (), "claude": ("repo-managed-permissions.json",)}


def backup(path, folder):
    destination = folder / path.relative_to(path.anchor)
    destination.parent.mkdir(parents=True, exist_ok=True)
    path.rename(destination)
    return destination


def install(tool, target, *, skills_dir=None):
    target = target.resolve()
    if skills_dir is not None:
        skills_dir = skills_dir.parent.resolve() / skills_dir.name
    legacy_skills = target / "skills"
    migrate_skills = (
        skills_dir is not None
        and skills_dir != legacy_skills
        and not legacy_skills.is_symlink()
    )
    root = ROOT / "agents"
    native = root / tool
    instruction = "AGENTS.md" if tool == "codex" else "CLAUDE.md"
    links = {instruction: root / "AGENTS.md"}
    legacy = [target / name for name in LEGACY[tool]]
    for skill in sorted((root / "skills").iterdir()):
        if (skill / "SKILL.md").is_file():
            links[(skills_dir or legacy_skills) / skill.name] = skill
            if migrate_skills:
                legacy.append(legacy_skills / skill.name)
    for source in sorted(native.rglob("*")):
        if source.is_file() and not source.name.startswith("."):
            links[str(source.relative_to(native))] = source

    pending = []
    for relative, source in links.items():
        path = target / relative
        if any(
            parent.is_symlink() or (parent.exists() and not parent.is_dir())
            for parent in path.parents
        ):
            raise ValueError(f"Invalid destination parent for {path}")
        if path == source:
            raise ValueError(f"Destination overlaps source: {path}")
        if not path.is_symlink() or path.readlink() != source:
            pending.append((path, source))
    legacy = [
        path for path in legacy if os.path.lexists(path) and not path.is_symlink()
    ]
    backup_root = target / ".setup-backups"
    if legacy or any(os.path.lexists(path) for path, _ in pending):
        if backup_root.is_symlink() or (
            backup_root.exists() and not backup_root.is_dir()
        ):
            raise ValueError(f"Invalid backup directory: {backup_root}")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    backups = backup_root / stamp
    for path, source in pending:
        path.parent.mkdir(parents=True, exist_ok=True)
        moved = backup(path, backups) if os.path.lexists(path) else None
        try:
            path.symlink_to(source, target_is_directory=source.is_dir())
        except OSError:
            if moved is not None and not os.path.lexists(path):
                moved.rename(path)
            raise
        if moved is not None:
            print(f"Backed up {path} to {moved}")
    for path in legacy:
        print(f"Moved legacy {path} to {backup(path, backups)}")
    (native / SETTINGS[tool]).chmod(0o600)
    print(f"Installed {tool} configuration to {target} ({len(pending)} links changed)")


def main():
    parser = argparse.ArgumentParser(
        description="Link global agent configuration from this checkout."
    )
    parser.add_argument("tool", choices=("codex", "claude"))
    parser.add_argument(
        "--target-dir",
        type=Path,
        help="Override the destination (also useful for testing)",
    )
    args = parser.parse_args()
    if os.geteuid() == 0:
        parser.error("Run as your normal user, without sudo.")
    variable = "CODEX_HOME" if args.tool == "codex" else "CLAUDE_CONFIG_DIR"
    target = args.target_dir or Path(
        os.environ.get(variable) or Path.home() / f".{args.tool}"
    )
    try:
        skills_dir = None
        if args.tool == "codex" and args.target_dir is None:
            skills_dir = Path.home() / ".agents/skills"
        install(args.tool, target.absolute(), skills_dir=skills_dir)
    except (OSError, ValueError, TypeError) as error:
        sys.exit(f"Installation failed: {error}")


if __name__ == "__main__":
    main()
