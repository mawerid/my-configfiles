# My Config Files

Personal dotfiles and setup scripts for Linux (Ubuntu) and macOS.

This repo helps bootstrap a terminal-focused environment with:

- Zsh + Oh My Zsh + Powerlevel10k
- tmux + TPM
- Neovim config
- Docker daemon registry settings
- OpenCode CLI and config

## Repository Layout

```text
.
├── install.sh
├── setup-docker.sh
├── setup-opencode.sh
├── script/
│   ├── setup-macos.sh
│   └── setup-ubuntu.sh
└── config/
  ├── docker/daemon.json
  ├── nvim/
  ├── opencode/
  ├── tmux/.tmux.conf
  └── zsh/.zshrc
```

## Quick Start

1. Clone the repo.
2. Run the OS bootstrap script through `install.sh`.

```bash
git clone <your-repo-url> ~/config
cd ~/config
bash install.sh
```

`install.sh` detects your OS and runs:

- `script/setup-macos.sh` on macOS
- `script/setup-ubuntu.sh` on Ubuntu

## What `install.sh` Sets Up

On supported platforms, it will:

1. Install base packages (`git`, `zsh`, `tmux`, `neovim`, `ripgrep`, etc.).
2. Install and configure Oh My Zsh.
3. Install Powerlevel10k theme.
4. Install zsh plugins:

- `zsh-autosuggestions`
- `zsh-syntax-highlighting`

5. Copy shell config:

- `config/zsh/.zshrc` -> `~/.zshrc`

6. Install tmux plugin manager (TPM) and copy:

- `config/tmux/.tmux.conf` -> `~/.tmux.conf`

7. Install Neovim config:

- `config/nvim` -> `~/.config/nvim`
- existing `~/.config/nvim` is backed up to a timestamped folder

After completion, the scripts print next steps for zsh/tmux/nvim.

## Docker Daemon Setup

Use this when you want to apply the repo Docker daemon settings to `/etc/docker/daemon.json`.

```bash
cd ~/config
sudo bash setup-docker.sh
```

Behavior:

1. Validates source file exists: `config/docker/daemon.json`.
2. Requires root privileges.
3. Backs up existing `/etc/docker/daemon.json` to a timestamped `.bak` file.
4. Writes the new daemon config.
5. Restarts Docker (`systemctl` or `service`).

Current daemon config includes these insecure registry CIDRs:

- `10.8.0.0/16`
- `172.16.0.0/16`
- `10.10.0.0/16`
- `192.168.0.0/16`

## OpenCode Setup

Use this script to install OpenCode (optional) and copy repo-managed OpenCode config.

```bash
cd ~/config
bash setup-opencode.sh
```

Optional flag:

```bash
bash setup-opencode.sh --skip-install
```

Behavior:

1. Uses source config from `config/opencode`.
2. Installs OpenCode via `curl -fsSL https://opencode.ai/install | bash` if missing.
3. Resolves target user/home correctly when run with `sudo`.
4. Backs up existing OpenCode config directory to a timestamped `.bak` directory.
5. Copies config to `${XDG_CONFIG_HOME:-$HOME/.config}/opencode`.
6. Fixes ownership when run as root.

## Prerequisites

- `bash`
- `git`
- `curl`
- `sudo` access for system package installs and Docker setup

Notes:

- On macOS, Homebrew must already be installed.
- On Ubuntu, scripts use `apt`.

## Safety and Backups

These scripts are designed to overwrite active config files. Before writing, they back up existing configs with timestamped names where applicable.

Recommended: review scripts before running in production or shared environments.

## Troubleshooting

- `Unsupported Linux distro`: current auto installer supports Ubuntu only.
- `Homebrew is not installed`: install Homebrew first, then rerun on macOS.
- `This script must run as root`: rerun Docker setup with `sudo`.
- `OpenCode config directory not found`: ensure repo structure is intact and run from this repo.

## License

This repository currently does not define a top-level license.
