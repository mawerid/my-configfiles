#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_FILE="$SCRIPT_DIR/config/docker/daemon.json"
TARGET_FILE="/etc/docker/daemon.json"

if [[ ! -f "$SOURCE_FILE" ]]; then
	echo "Error: source Docker config not found: $SOURCE_FILE" >&2
	exit 1
fi

if [[ "$EUID" -ne 0 ]]; then
	echo "This script must run as root. Re-run with: sudo $0" >&2
	exit 1
fi

mkdir -p "$(dirname "$TARGET_FILE")"

if [[ -f "$TARGET_FILE" ]]; then
	backup_file="$TARGET_FILE.bak.$(date +%Y%m%d%H%M%S)"
	cp "$TARGET_FILE" "$backup_file"
	echo "Backed up existing config to: $backup_file"
fi

cp "$SOURCE_FILE" "$TARGET_FILE"
chmod 644 "$TARGET_FILE"
echo "Updated Docker daemon config: $TARGET_FILE"

if command -v systemctl >/dev/null 2>&1; then
	systemctl daemon-reload || true
	systemctl restart docker
	echo "Docker service restarted via systemctl"
elif command -v service >/dev/null 2>&1; then
	service docker restart
	echo "Docker service restarted via service"
else
	echo "Warning: could not find systemctl or service. Restart Docker manually." >&2
fi
