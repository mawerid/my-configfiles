#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

echo "==> Updating apt"
sudo apt update

echo "==> Installing packages"
sudo apt install -y git zsh tmux ripgrep tree curl build-essential unzip python3 gh glab
sudo apt install -y bat || sudo apt install -y batcat || true

export PATH="$HOME/.local/bin:$PATH"
if ! command -v lazygit >/dev/null 2>&1 && apt-cache show lazygit >/dev/null 2>&1; then
  sudo apt install -y lazygit
fi
bash "$SCRIPT_DIR/install-ubuntu-editor.sh"

# Installs or upgrades a GitHub release binary into ~/.local/bin after checking its sha256.
# Usage: install_github_release <repo> <installed version> <asset> <checksum file> <binary>...
# {version} in the asset and {asset} in the checksum file name are filled in.
install_github_release() (
  local repo="$1" installed="$2" asset="$3" sums="$4" tag version tmp base binary
  shift 4
  tag="$(curl -fsSLI -o /dev/null -w '%{url_effective}' "https://github.com/$repo/releases/latest")"
  tag="${tag##*/}"
  version="${tag#v}"
  if [[ "$installed" == "$version" ]]; then
    echo "$repo $version is current"
    return
  fi
  asset="${asset//\{version\}/$version}"
  sums="${sums//\{asset\}/$asset}"
  tmp="$(mktemp -d)"
  trap 'rm -rf "$tmp"' EXIT
  base="https://github.com/$repo/releases/download/$tag"
  curl -fsSL -o "$tmp/$asset" "$base/$asset"
  curl -fsSL -o "$tmp/sums" "$base/$sums"
  (cd "$tmp" && awk -v a="$asset" '$2 == a || $2 == "*" a' sums | sha256sum --check --strict -)
  tar -xzf "$tmp/$asset" -C "$tmp"
  mkdir -p "$HOME/.local/bin"
  for binary in "$@"; do
    install -m 755 "$(find "$tmp" -type f -name "$binary" -print -quit)" "$HOME/.local/bin/$binary"
  done
  echo "Installed $repo $version"
)

case "$(uname -m)" in
  x86_64) lazydocker_arch=x86_64 uv_arch=x86_64 ;;
  aarch64 | arm64) lazydocker_arch=arm64 uv_arch=aarch64 ;;
  *) echo "Unsupported CPU: $(uname -m)" >&2; exit 1 ;;
esac
echo "==> Installing lazydocker and uv"
install_github_release jesseduffield/lazydocker \
  "$(lazydocker --version 2>/dev/null | sed -n 's/^Version: //p')" \
  "lazydocker_{version}_Linux_$lazydocker_arch.tar.gz" checksums.txt lazydocker
install_github_release astral-sh/uv \
  "$(uv --version 2>/dev/null | cut -d' ' -f2)" \
  "uv-$uv_arch-unknown-linux-gnu.tar.gz" "{asset}.sha256" uv uvx

exec bash "$SCRIPT_DIR/setup-workstation.sh"
