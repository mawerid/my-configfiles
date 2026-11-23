#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
zsh_path="$(command -v zsh)"
zsh_custom="${ZSH_CUSTOM:-$HOME/.oh-my-zsh/custom}"

echo "==> Setting zsh as default shell"
if [[ "${SHELL:-}" != "$zsh_path" ]]; then
  chsh -s "$zsh_path" || true
fi

echo "==> Installing Oh My Zsh"
if [[ ! -d "$HOME/.oh-my-zsh" ]]; then
  installer="$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)"
  RUNZSH=no CHSH=no KEEP_ZSHRC=yes sh -c "$installer"
fi

install_repo() {
  local repo="$1" destination="$2"
  if [[ ! -d "$destination" ]]; then
    mkdir -p -- "$(dirname -- "$destination")"
    git clone --depth=1 "https://github.com/$repo.git" "$destination"
  fi
}

echo "==> Installing Zsh theme, plugins, and TPM"
install_repo romkatv/powerlevel10k "$zsh_custom/themes/powerlevel10k"
install_repo zsh-users/zsh-autosuggestions "$zsh_custom/plugins/zsh-autosuggestions"
install_repo zsh-users/zsh-syntax-highlighting "$zsh_custom/plugins/zsh-syntax-highlighting"
install_repo tmux-plugins/tpm "$HOME/.tmux/plugins/tpm"

python3 "$SCRIPT_DIR/install-editor-configs.py" "$HOME/.tmux.conf" "$HOME/.zshrc"

echo "==> Done"
echo "Next:"
echo "  exec zsh"
echo "  p10k configure"
echo "  tmux"
echo "  press Ctrl-a then Shift-i"
echo "  nvim"
echo "  run :LazyHealth"
