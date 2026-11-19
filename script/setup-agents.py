#!/usr/bin/env python3
import argparse
import os
import sys
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]


def install(tool, target, *, skills_dir=None):
    root = ROOT / "agents"
    native = root / tool
    instruction = "AGENTS.md" if tool == "codex" else "CLAUDE.md"
    links = {instruction: root / "AGENTS.md"}
    for skill in sorted((root / "skills").iterdir()):
        if (skill / "SKILL.md").is_file():
            links[(skills_dir or target / "skills") / skill.name] = skill
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
    for path, source in pending:
        path.parent.mkdir(parents=True, exist_ok=True)
        backup = None
        if os.path.lexists(path):
            backup = path.with_name(f".{path.name}.bak.{uuid4().hex}")
            path.rename(backup)
        try:
            path.symlink_to(source, target_is_directory=source.is_dir())
        except OSError:
            if backup is not None and not os.path.lexists(path):
                backup.rename(path)
            raise
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
