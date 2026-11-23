#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

echo "==> Updating apt"
sudo apt update

echo "==> Installing packages"
sudo apt install -y git zsh tmux ripgrep tree curl build-essential unzip python3
sudo apt install -y bat || sudo apt install -y batcat || true

export PATH="$HOME/.local/bin:$PATH"
if ! command -v lazygit >/dev/null 2>&1 && apt-cache show lazygit >/dev/null 2>&1; then
  sudo apt install -y lazygit
fi
bash "$SCRIPT_DIR/install-ubuntu-editor.sh"

exec bash "$SCRIPT_DIR/setup-workstation.sh"
