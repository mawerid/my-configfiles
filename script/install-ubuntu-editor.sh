#!/usr/bin/env bash
set -euo pipefail

data_dir="${1:-${XDG_DATA_HOME:-$HOME/.local/share}/config-bootstrap/editor}"
bin_dir="${2:-$HOME/.local/bin}"

case "$(uname -m)" in
  x86_64) nvim_arch=x86_64; tree_sitter_arch=x64 ;;
  aarch64|arm64) nvim_arch=arm64; tree_sitter_arch=arm64 ;;
  *) echo "Neovim nightly is available for Ubuntu x86-64 and ARM64." >&2; exit 1 ;;
esac

mkdir -p -- "$data_dir" "$bin_dir"
stage="$(mktemp -d "$data_dir/.download.XXXXXXXX")"
trap 'rm -rf -- "$stage" "${links:-}"' EXIT
links="$(mktemp -d "$bin_dir/.editor-links.XXXXXXXX")"

publish_binary() {
  local name="$1" binary="$2" target="$bin_dir/$1" backup current=""
  if [[ -L "$target" ]]; then
    current="$(readlink -- "$target")"
  fi
  if [[ "$current" == "$binary" ]]; then
    return
  fi
  if [[ -e "$target" || -L "$target" ]] && [[ "$current" != "$data_dir/"* ]]; then
    if [[ ! -f "$target" && ! -L "$target" ]]; then
      echo "Invalid binary destination: $target" >&2
      return 1
    fi
    backup="$(mktemp -d "$target.bak.XXXXXXXX")"
    cp -a -- "$target" "$backup/"
    printf 'Backed up %s to %s/%s\n' "$target" "$backup" "$name"
  fi
  ln -s -- "$binary" "$links/$name"
  mv -Tf -- "$links/$name" "$target"
}

echo "==> Checking Neovim nightly"
nvim_release="nvim-linux-$nvim_arch"
current_nvim="$(readlink -- "$bin_dir/nvim" 2>/dev/null || true)"
etag="$stage/no-etag"
if [[ "$current_nvim" == "$data_dir"/nvim-*/bin/nvim && -x "$current_nvim" ]]; then
  etag="${current_nvim%/bin/nvim}/download.etag"
fi
status="$(curl --fail --silent --show-error --location --retry 3 \
  --etag-compare "$etag" --etag-save "$stage/nvim.etag" --write-out '%{http_code}' \
  "https://github.com/neovim/neovim/releases/download/nightly/$nvim_release.tar.gz" \
  --output "$stage/nvim.tar.gz")"
if [[ "$status" == 304 && -s "$etag" && -x "$current_nvim" ]]; then
  nvim_binary="$current_nvim"
elif [[ "$status" == 200 ]]; then
  digest="$(sha256sum "$stage/nvim.tar.gz" | cut -d ' ' -f 1)"
  install_dir="$data_dir/nvim-$digest"
  if [[ ! -x "$install_dir/bin/nvim" ]]; then
    tar -xzf "$stage/nvim.tar.gz" -C "$stage"
    "$stage/$nvim_release/bin/nvim" --headless -u NONE -i NONE \
      '+lua if vim.fn.has("nvim-0.11.2") ~= 1 or not jit then vim.cmd.cquit() end' +qa
    mv -nT -- "$stage/$nvim_release" "$install_dir"
  fi
  if [[ -s "$stage/nvim.etag" ]]; then
    mv -fT -- "$stage/nvim.etag" "$install_dir/download.etag"
  fi
  nvim_binary="$install_dir/bin/nvim"
  if [[ ! -x "$nvim_binary" ]]; then
    echo "Neovim archive could not be installed into $install_dir." >&2
    exit 1
  fi
else
  echo "Unexpected HTTP status for Neovim nightly: $status" >&2
  exit 1
fi

export PATH="$bin_dir:$PATH"
tree_sitter_version="$(tree-sitter --version 2>/dev/null || true)"
if ! [[ "$tree_sitter_version" =~ ^tree-sitter[[:space:]]+([0-9]+\.[0-9]+\.[0-9]+) ]] ||
   ! dpkg --compare-versions "${BASH_REMATCH[1]}" ge 0.26.1; then
  echo "==> Downloading Tree-sitter CLI nightly"
  curl --fail --silent --show-error --location --retry 3 \
    "https://github.com/tree-sitter/tree-sitter/releases/download/nightly/tree-sitter-cli-linux-$tree_sitter_arch.zip" \
    --output "$stage/tree-sitter.zip"
  mkdir -- "$stage/cli"
  unzip -q "$stage/tree-sitter.zip" -d "$stage/cli"
  chmod +x "$stage/cli/tree-sitter"
  "$stage/cli/tree-sitter" --version
  digest="$(sha256sum "$stage/tree-sitter.zip" | cut -d ' ' -f 1)"
  install_dir="$data_dir/tree-sitter-$digest"
  mv -nT -- "$stage/cli" "$install_dir"
  publish_binary tree-sitter "$install_dir/tree-sitter"
fi

publish_binary nvim "$nvim_binary"

if ! command -v lazygit >/dev/null 2>&1; then
  lazygit_version=0.66.3
  case "$nvim_arch" in
    x86_64) lazygit_digest=0a23f429a95f0d09db298b3c291536d818de066aa5a85c255806f0490ff6656b ;;
    arm64) lazygit_digest=ac0b48237f3d0283813e7154ec063237e519532feb0470c0881a1793ee78fd42 ;;
  esac
  install_dir="$data_dir/lazygit-$lazygit_version"
  if [[ ! -x "$install_dir/lazygit" ]]; then
    echo "==> Downloading Lazygit $lazygit_version"
    archive="lazygit_${lazygit_version}_linux_${nvim_arch}.tar.gz"
    curl --fail --silent --show-error --location --retry 3 \
      "https://github.com/jesseduffield/lazygit/releases/download/v$lazygit_version/$archive" \
      --output "$stage/$archive"
    if ! printf '%s  %s\n' "$lazygit_digest" "$stage/$archive" | sha256sum --check --status; then
      echo "Checksum verification failed for $archive." >&2
      exit 1
    fi
    tar -xzf "$stage/$archive" -C "$stage" lazygit
    "$stage/lazygit" --version
    mkdir -p -- "$install_dir"
    mv -Tf -- "$stage/lazygit" "$install_dir/lazygit"
  fi
  publish_binary lazygit "$install_dir/lazygit"
fi
