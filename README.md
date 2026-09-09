# My Config Files

Bootstrap scripts and configurations for Ubuntu and macOS: Zsh, tmux, Neovim,
Docker, Claude Code, and Codex.

## Install

```bash
git clone <your-repo-url> ~/config
cd ~/config
bash install.sh
```

`install.sh` selects the macOS or Ubuntu bootstrap. Configure the agents as your
normal user:

```bash
bash setup-claude.sh
bash setup-codex.sh
```

These scripts merge managed settings, preserve personal settings, and create
timestamped backups. They do not install the agent CLIs.

## OpenShell deep research

See [the deep research README](config/openshell/deep-research/README.md). It is
separate from everyday strict agent settings and supports Ubuntu NVIDIA and
macOS M4 hosts.

## Privacy

Everyday settings disable optional telemetry, feedback, and OpenTelemetry
export. Shared instructions keep private code and credentials out of external
searches and uploads unless authorized. Hosted inference still sends prompts and
tool content to the provider; account training and retention controls are
separate.

## Docker daemon

```bash
sudo bash setup-docker.sh
```

This validates, backs up, installs the repository Docker configuration, and
restarts Docker.

## Validation

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
bash -n setup-claude.sh setup-codex.sh
```
