#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SHARED_DIR="$SCRIPT_DIR/config/shared"
SOURCE_DIR="$SCRIPT_DIR/config/claude"

TARGET_USER="${SUDO_USER:-$USER}"
TARGET_HOME="$HOME"

if [[ -n "${SUDO_USER:-}" ]]; then
    TARGET_HOME="$(getent passwd "$SUDO_USER" | cut -d: -f6)"
fi

if [[ -z "$TARGET_HOME" ]]; then
    echo "Error: could not determine home directory for user: $TARGET_USER" >&2
    exit 1
fi

TARGET_DIR="$TARGET_HOME/.claude"
mkdir -p "$TARGET_DIR"

backup() {
    local path="$1"
    if [[ -e "$path" ]]; then
        mv "$path" "${path}.bak.$(date +%Y%m%d%H%M%S)"
        echo "Backed up: $path"
    fi
}

# shared rules -> CLAUDE.md
backup "$TARGET_DIR/CLAUDE.md"
cp "$SHARED_DIR/rules.md" "$TARGET_DIR/CLAUDE.md"
echo "Installed CLAUDE.md"

# settings
backup "$TARGET_DIR/settings.json"
cp "$SOURCE_DIR/settings.json" "$TARGET_DIR/settings.json"
echo "Installed settings.json"

# shared skills
backup "$TARGET_DIR/skills"
cp -R "$SHARED_DIR/skills" "$TARGET_DIR/skills"
echo "Installed skills"

if [[ "$EUID" -eq 0 ]]; then
    chown -R "$TARGET_USER":"$TARGET_USER" "$TARGET_DIR"
fi

echo "Claude config installed to: $TARGET_DIR"
echo "Done — run 'claude'"
