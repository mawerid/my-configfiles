#!/usr/bin/env python3
import argparse
import datetime
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile

if sys.version_info < (3, 11):
    sys.exit("Python 3.11 or newer is required.")

import tomllib


ROOT = Path(__file__).resolve().parents[1]
BEGIN = "<!-- config-repo:begin -->"
END = "<!-- config-repo:end -->"


def merge(existing, managed):
    result = dict(existing)
    for key, value in managed.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = merge(result[key], value)
        elif isinstance(value, list) and isinstance(result.get(key), list):
            result[key] = result[key] + [item for item in value if item not in result[key]]
        else:
            result[key] = value
    return result


def toml_value(value):
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, (int, float)):
        return repr(value)
    if isinstance(value, (datetime.datetime, datetime.date, datetime.time)):
        return value.isoformat()
    if isinstance(value, list):
        return "[" + ", ".join(toml_value(item) for item in value) + "]"
    if isinstance(value, dict):
        return "{ " + ", ".join(f"{json.dumps(k)} = {toml_value(v)}" for k, v in value.items()) + " }"
    raise ValueError(f"Unsupported TOML value: {type(value).__name__}")


def toml_text(data):
    text = "".join(f"{json.dumps(key)} = {toml_value(value)}\n" for key, value in data.items())
    tomllib.loads(text)
    return text


def instructions(existing, managed):
    block = f"{BEGIN}\n{managed.rstrip()}\n{END}\n"
    if BEGIN in existing or END in existing:
        if existing.count(BEGIN) != 1 or existing.count(END) != 1:
            raise ValueError("Invalid repo instruction markers")
        before, rest = existing.split(BEGIN)
        _, after = rest.split(END)
        return before + block.rstrip() + after
    if existing.strip() == managed.strip():
        return block
    return (existing.rstrip() + "\n\n" if existing.strip() else "") + block


def check_path(path):
    for parent in (path, *path.parents):
        if parent.is_symlink():
            raise ValueError(f"Refusing to follow a symlink: {parent}")
    if path.exists() and not path.is_file():
        raise ValueError(f"Expected a file: {path}")


def install(tool, target):
    source = ROOT / "config" / tool
    shared = ROOT / "config/shared"
    name = "config.toml" if tool == "codex" else "settings.json"
    config_path = target / name
    check_path(config_path)
    loader = tomllib.loads if tool == "codex" else json.loads
    existing = loader(config_path.read_text()) if config_path.exists() else {}
    managed = loader((source / name).read_text())
    if tool == "codex":
        policy = existing.get("execpolicy", {})
        if policy.get("user_rules") == ["~/.codex/execpolicy/default.rules"]:
            del policy["user_rules"]
            if not policy:
                existing.pop("execpolicy", None)
        features = existing.get("features", {})
        features.pop("exec_permission_approvals", None)
        if not features:
            existing.pop("features", None)
        old_instructions = existing.get("developer_instructions", "")
        managed["developer_instructions"] = instructions(old_instructions, managed["developer_instructions"])
    data = merge(existing, managed)
    rendered = toml_text(data) if tool == "codex" else json.dumps(data, indent=4) + "\n"
    writes = {config_path: rendered.encode()}
    rules_path = target / ("AGENTS.md" if tool == "codex" else "CLAUDE.md")
    check_path(rules_path)
    old_rules = rules_path.read_text() if rules_path.exists() else ""
    writes[rules_path] = instructions(old_rules, (shared / "rules.md").read_text()).encode()
    for directory in (shared / "skills", source / "agents"):
        files = list(directory.rglob("*"))
        if not files:
            raise ValueError(f"Missing or empty source directory: {directory}")
        for file in files:
            if file.is_file():
                content = file.read_bytes()
                if tool == "codex" and file.suffix == ".toml":
                    agent = tomllib.loads(content.decode())
                    for key in ("name", "description", "developer_instructions"):
                        if not agent.get(key):
                            raise ValueError(f"Missing {key}: {file}")
                writes[target / directory.name / file.relative_to(directory)] = content
    if tool == "codex":
        writes[target / "rules/repo-default.rules"] = (source / "rules/repo-default.rules").read_bytes()
    for path in writes:
        check_path(path)
    # Prepare all content before replacing any installed file.
    changed = {path: content for path, content in writes.items()
               if not path.exists() or path.read_bytes() != content}
    for path, content in changed.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            stamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S%f")
            backup = path.with_name(f"{path.name}.bak.{stamp}")
            shutil.copy2(path, backup)
            print(f"Backed up: {backup}")
        descriptor, temporary = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(content)
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
    print(f"Installed {tool} configuration to {target} ({len(changed)} files changed)")


def main():
    parser = argparse.ArgumentParser(description="Install repo-managed agent configuration; preserve unrelated settings and files.")
    parser.add_argument("tool", choices=("codex", "claude"))
    parser.add_argument("--target-dir", type=Path, help="Override the destination (also useful for testing)")
    args = parser.parse_args()
    if os.geteuid() == 0:
        parser.error("Run as your normal user, without sudo.")
    variable = "CODEX_HOME" if args.tool == "codex" else "CLAUDE_CONFIG_DIR"
    target = args.target_dir or Path(os.environ.get(variable) or Path.home() / f".{args.tool}")
    try:
        install(args.tool, target.absolute())
    except (OSError, ValueError, TypeError) as error:
        sys.exit(f"Installation failed: {error}")


if __name__ == "__main__":
    main()
