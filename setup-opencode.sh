#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_DIR="$SCRIPT_DIR/config/opencode"

SKIP_INSTALL=0
if [[ "${1:-}" == "--skip-install" ]]; then
	SKIP_INSTALL=1
fi

if [[ ! -d "$SOURCE_DIR" ]]; then
	echo "Error: source OpenCode config directory not found: $SOURCE_DIR" >&2
	exit 1
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
cp -R "$SOURCE_DIR/." "$TARGET_DIR/"

if [[ "$EUID" -eq 0 ]]; then
	chown -R "$TARGET_USER":"$TARGET_USER" "$TARGET_DIR"
fi

echo "OpenCode config installed to: $TARGET_DIR"
echo "Done"
echo "Next: run 'opencode'"
