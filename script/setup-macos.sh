#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

echo "==> Checking Xcode Command Line Tools"
xcode-select -p >/dev/null 2>&1 || xcode-select --install || true

echo "==> Checking Homebrew"
if ! command -v brew >/dev/null 2>&1; then
  echo "Homebrew is not installed. Install it first from https://brew.sh"
  exit 1
fi

echo "==> Installing packages"
brew update
brew install git zsh tmux neovim tree-sitter-cli lazygit ripgrep bat tree
if ! python3 --version >/dev/null 2>&1; then
  brew install python
fi

exec bash "$SCRIPT_DIR/setup-workstation.sh"
