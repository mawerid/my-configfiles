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

if [[ -f "$TARGET_FILE" && ! -L "$TARGET_FILE" ]] && cmp -s "$SOURCE_FILE" "$TARGET_FILE"; then
	echo "Docker daemon config is already current."
	exit 0
fi

target_dir="$(dirname "$TARGET_FILE")"
mkdir -p "$target_dir"
stage_dir="$(mktemp -d "$target_dir/.setup-docker.XXXXXXXX")"
staged_file="$stage_dir/daemon.json"
previous_file="$stage_dir/previous.json"
trap 'rm -f -- "$staged_file" "$previous_file"; rmdir -- "$stage_dir"' EXIT

install -m 644 "$SOURCE_FILE" "$staged_file"
dockerd --validate --config-file "$staged_file"

if [[ -e "$TARGET_FILE" || -L "$TARGET_FILE" ]]; then
	if [[ ! -f "$TARGET_FILE" && ! -L "$TARGET_FILE" ]]; then
		echo "Error: expected a Docker config file at $TARGET_FILE" >&2
		exit 1
	fi
	cp -a -- "$TARGET_FILE" "$previous_file"
fi

mv -fT -- "$staged_file" "$TARGET_FILE"
echo "Updated Docker daemon config at $TARGET_FILE"

if command -v systemctl >/dev/null 2>&1; then
	restart=(systemctl restart docker)
elif command -v service >/dev/null 2>&1; then
	restart=(service docker restart)
else
	echo "Warning: could not find systemctl or service. Restart Docker manually." >&2
	exit 0
fi

if "${restart[@]}"; then
	echo "Docker service restarted via ${restart[0]}."
	exit 0
fi

echo "Docker restart failed. Restoring the previous configuration." >&2
if [[ -e "$previous_file" || -L "$previous_file" ]]; then
	mv -fT -- "$previous_file" "$TARGET_FILE"
else
	rm -f -- "$TARGET_FILE"
fi
if ! "${restart[@]}"; then
	echo "Docker could not restart with the previous configuration." >&2
fi
exit 1
