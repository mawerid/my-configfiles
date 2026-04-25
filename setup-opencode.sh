#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SHARED_DIR="$SCRIPT_DIR/config/shared"
SOURCE_DIR="$SCRIPT_DIR/config/opencode"

SKIP_INSTALL=0
if [[ "${1:-}" == "--skip-install" ]]; then
	SKIP_INSTALL=1
fi

TARGET_USER="${SUDO_USER:-$USER}"
TARGET_HOME="$HOME"

if [[ -n "${SUDO_USER:-}" ]]; then
	TARGET_HOME="$(getent passwd "$SUDO_USER" | cut -d: -f6)"
fi

if [[ -z "$TARGET_HOME" ]]; then
	echo "Error: could not determine home directory for user: $TARGET_USER" >&2
	exit 1
fi

TARGET_CONFIG_DIR="${XDG_CONFIG_HOME:-$TARGET_HOME/.config}"
TARGET_DIR="$TARGET_CONFIG_DIR/opencode"
mkdir -p "$TARGET_CONFIG_DIR"

if [[ "$SKIP_INSTALL" -eq 0 ]]; then
	if command -v opencode >/dev/null 2>&1; then
		echo "OpenCode is already installed"
	else
		if ! command -v curl >/dev/null 2>&1; then
			echo "Error: curl is required to install OpenCode" >&2
			exit 1
		fi
		echo "Installing OpenCode"
		if [[ -n "${SUDO_USER:-}" ]]; then
			sudo -u "$TARGET_USER" -H bash -lc 'curl -fsSL https://opencode.ai/install | bash'
		else
			bash -lc 'curl -fsSL https://opencode.ai/install | bash'
		fi
	fi
else
	echo "Skipping OpenCode install (--skip-install)"
fi

if [[ -e "$TARGET_DIR" ]]; then
	backup_dir="$TARGET_DIR.bak.$(date +%Y%m%d%H%M%S)"
	mv "$TARGET_DIR" "$backup_dir"
	echo "Backed up existing OpenCode config to: $backup_dir"
fi

mkdir -p "$TARGET_DIR"

# tool-specific config (opencode.json, agents/)
cp -R "$SOURCE_DIR/." "$TARGET_DIR/"

# shared rules -> AGENTS.md
cp "$SHARED_DIR/rules.md" "$TARGET_DIR/AGENTS.md"
echo "Installed AGENTS.md"

# shared skills
cp -R "$SHARED_DIR/skills" "$TARGET_DIR/skills"
echo "Installed skills"

# shared agents — translate Claude model IDs to LMStudio IDs
mkdir -p "$TARGET_DIR/agents"
for f in "$SHARED_DIR/agents/"*.md; do
	sed \
		-e 's|^model: sonnet.*|model: lmstudio/nvidia/nemotron-3-nano-4b|' \
		-e 's|^model: opus.*|model: lmstudio/google/gemma-4-e4b|' \
		"$f" > "$TARGET_DIR/agents/$(basename "$f")"
done
echo "Installed shared agents"

if [[ "$EUID" -eq 0 ]]; then
	chown -R "$TARGET_USER":"$TARGET_USER" "$TARGET_DIR"
fi

echo "OpenCode config installed to: $TARGET_DIR"
echo "Done"
echo "Next: run 'opencode'"
