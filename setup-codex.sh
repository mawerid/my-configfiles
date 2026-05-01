#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SHARED_DIR="$SCRIPT_DIR/config/shared"
SOURCE_DIR="$SCRIPT_DIR/config/codex"

CODEX_SONNET_MODEL="${CODEX_SONNET_MODEL:-gpt-5.4}"
CODEX_OPUS_MODEL="${CODEX_OPUS_MODEL:-gpt-5.5}"

TARGET_USER="${SUDO_USER:-$USER}"
TARGET_HOME="$HOME"

if [[ -n "${SUDO_USER:-}" ]]; then
    TARGET_HOME="$(getent passwd "$SUDO_USER" | cut -d: -f6)"
fi

if [[ -z "$TARGET_HOME" ]]; then
    echo "Error: could not determine home directory for user: $TARGET_USER" >&2
    exit 1
fi

TARGET_DIR="$TARGET_HOME/.codex"
mkdir -p "$TARGET_DIR"

backup() {
    local path="$1"
    if [[ -e "$path" ]]; then
        mv "$path" "${path}.bak.$(date +%Y%m%d%H%M%S)"
        echo "Backed up: $path"
    fi
}

rewrite_codex_models() {
    local path="$1"
    local tmp

    tmp="$(mktemp)"
    sed \
        -e "s|^model: sonnet.*|model: $CODEX_SONNET_MODEL|" \
        -e "s|^model: opus.*|model: $CODEX_OPUS_MODEL|" \
        "$path" > "$tmp"
    mv "$tmp" "$path"
}

rewrite_codex_models_in_dir() {
    local dir="$1"

    while IFS= read -r -d '' f; do
        rewrite_codex_models "$f"
    done < <(find "$dir" -type f -name "*.md" -print0)
}

# shared rules -> AGENTS.md
backup "$TARGET_DIR/AGENTS.md"
cp "$SHARED_DIR/rules.md" "$TARGET_DIR/AGENTS.md"
echo "Installed AGENTS.md"

# config
backup "$TARGET_DIR/config.toml"
cp "$SOURCE_DIR/config.toml" "$TARGET_DIR/config.toml"
echo "Installed config.toml"

# command policy rules
backup "$TARGET_DIR/execpolicy"
cp -R "$SOURCE_DIR/execpolicy" "$TARGET_DIR/execpolicy"
echo "Installed execpolicy"

# shared skills
backup "$TARGET_DIR/skills"
cp -R "$SHARED_DIR/skills" "$TARGET_DIR/skills"
rewrite_codex_models_in_dir "$TARGET_DIR/skills"
echo "Installed skills"

# shared agents
backup "$TARGET_DIR/agents"
cp -R "$SHARED_DIR/agents" "$TARGET_DIR/agents"
rewrite_codex_models_in_dir "$TARGET_DIR/agents"
echo "Installed agents"

if [[ "$EUID" -eq 0 ]]; then
    chown -R "$TARGET_USER":"$TARGET_USER" "$TARGET_DIR"
fi

echo "Codex config installed to: $TARGET_DIR"
echo "Models:"
echo "  sonnet -> $CODEX_SONNET_MODEL"
echo "  opus   -> $CODEX_OPUS_MODEL"
echo "Done — run 'codex'"
