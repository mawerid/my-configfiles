#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"
CONFIG_DIR="$ROOT_DIR/config"

echo "==> Updating apt"
sudo apt update

echo "==> Installing packages"
sudo apt install -y git zsh tmux neovim ripgrep tree curl
sudo apt install -y bat || sudo apt install -y batcat || true

echo "==> Setting zsh as default shell"
if [ "$SHELL" != "$(which zsh)" ]; then
  chsh -s "$(which zsh)" || true
fi

echo "==> Installing Oh My Zsh"
if [ ! -d "$HOME/.oh-my-zsh" ]; then
  RUNZSH=no CHSH=no KEEP_ZSHRC=yes \
    sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)"
fi

echo "==> Installing Powerlevel10k"
mkdir -p "${ZSH_CUSTOM:-$HOME/.oh-my-zsh/custom}/themes"
if [ ! -d "${ZSH_CUSTOM:-$HOME/.oh-my-zsh/custom}/themes/powerlevel10k" ]; then
  git clone --depth=1 https://github.com/romkatv/powerlevel10k.git \
    "${ZSH_CUSTOM:-$HOME/.oh-my-zsh/custom}/themes/powerlevel10k"
fi

echo "==> Installing zsh plugins"
mkdir -p "${ZSH_CUSTOM:-$HOME/.oh-my-zsh/custom}/plugins"

if [ ! -d "${ZSH_CUSTOM:-$HOME/.oh-my-zsh/custom}/plugins/zsh-autosuggestions" ]; then
  git clone https://github.com/zsh-users/zsh-autosuggestions \
    "${ZSH_CUSTOM:-$HOME/.oh-my-zsh/custom}/plugins/zsh-autosuggestions"
fi

if [ ! -d "${ZSH_CUSTOM:-$HOME/.oh-my-zsh/custom}/plugins/zsh-syntax-highlighting" ]; then
  git clone https://github.com/zsh-users/zsh-syntax-highlighting.git \
    "${ZSH_CUSTOM:-$HOME/.oh-my-zsh/custom}/plugins/zsh-syntax-highlighting"
fi

echo "==> Copying ~/.zshrc"
cp "$CONFIG_DIR/zsh/.zshrc" "$HOME/.zshrc"

echo "==> Installing TPM"
mkdir -p "$HOME/.tmux/plugins"
if [ ! -d "$HOME/.tmux/plugins/tpm" ]; then
  git clone https://github.com/tmux-plugins/tpm "$HOME/.tmux/plugins/tpm"
fi

echo "==> Copying ~/.tmux.conf"
cp "$CONFIG_DIR/tmux/.tmux.conf" "$HOME/.tmux.conf"

echo "==> Installing Neovim config"
mkdir -p "$HOME/.config"

if [ -d "$HOME/.config/nvim" ]; then
  mv "$HOME/.config/nvim" "$HOME/.config/nvim.bak.$(date +%Y%m%d_%H%M%S)"
fi

cp -R "$CONFIG_DIR/nvim" "$HOME/.config/nvim"

echo "==> Done"
echo "Next:"
echo "  exec zsh"
echo "  p10k configure"
echo "  tmux"
echo "  press Ctrl-a then Shift-i"
echo "  nvim"
echo "  run :LazyHealth"