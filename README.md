# My Config Files

Personal dotfiles and setup scripts for Linux (Ubuntu) and macOS.

This repo helps bootstrap a terminal-focused environment with:

- Zsh + Oh My Zsh + Powerlevel10k
- tmux + TPM
- Neovim config
- Docker daemon registry settings
- Claude Code config
- Codex config

## Repository Layout

```text
.
├── install.sh
├── setup-claude.sh
├── setup-codex.sh
├── setup-docker.sh
├── script/
│   ├── setup-agents.py
│   ├── setup-macos.sh
│   └── setup-ubuntu.sh
└── config/
    ├── claude/
    │   ├── agents/
    │   └── settings.json
    ├── codex/
    │   ├── config.toml
    │   ├── agents/
    │   └── rules/
    ├── docker/daemon.json
    ├── nvim/
    ├── shared/
    │   ├── rules.md
    │   └── skills/
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

Agent configuration is installed separately with `setup-claude.sh` and `setup-codex.sh`.

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

## Agent Setup

Requires Python 3.11+ and a current Codex or Claude Code installation. Run these scripts as your normal user, **without sudo**, on macOS or Linux:

```bash
bash setup-claude.sh
bash setup-codex.sh
```

The scripts configure the tools; they do not install the CLIs. `install.sh` does not run these scripts.

| Source | Claude destination | Codex destination |
| --- | --- | --- |
| `config/shared/rules.md` | `~/.claude/CLAUDE.md` | `~/.codex/AGENTS.md` |
| `config/shared/skills/` | `~/.claude/skills/` | `~/.codex/skills/` |
| `config/claude/agents/*.md` | `~/.claude/agents/` | — |
| `config/codex/agents/*.toml` | — | `~/.codex/agents/` |
| Tool settings | `~/.claude/settings.json` | `~/.codex/config.toml` |
| `config/codex/rules/repo-default.rules` | — | `~/.codex/rules/repo-default.rules` |

`CLAUDE_CONFIG_DIR` and `CODEX_HOME` override the default directories. Both scripts also accept `--target-dir PATH` for an explicit destination.

Installation behavior:

- Merge settings recursively. Repo values win for managed scalar keys; lists retain existing entries and add missing repo entries, except for tracked Claude permissions described below. Unrelated settings, hooks, MCP servers, skills, agents, and command rules remain in place.
- Track Claude `allow`, `ask`, and `deny` entries added by the installer in `repo-managed-permissions.json`. Later installs remove obsolete tracked entries and preserve personal entries. Entries already present when tracking begins remain personal, even if they match repo defaults. Keep the manifest with the installed settings; malformed or symlinked manifests stop installation before writes.
- Preserve personal instructions around a marked repo-managed block in `CLAUDE.md`/`AGENTS.md` and Codex developer instructions.
- Replace only individual repo-managed files that changed, with timestamped `.bak` copies. Identical repeat installs make no changes.
- Validate source content and existing settings before writing. Malformed settings and symlinked destinations stop installation.
- Rewrite TOML formatting and comments when merging; the backup retains the original text.

Agent model defaults are configured in each tool’s native agent files:

| Agent | Codex model | Codex reasoning | Claude model |
| --- | --- | --- | --- |
| Explorer | `gpt-5.6-terra` | `medium` | `sonnet` |
| Planner | `gpt-5.6-sol` | `high` | `opus` |
| Implementer | `gpt-5.6-sol` | `medium` | `sonnet` |
| Tester | `gpt-5.6-sol` | `medium` | `sonnet` |
| Reviewer | `gpt-5.6-sol` | `high` | `opus` |
| Researcher | `gpt-6-astra` | `high` | `opus` |

Change the native agent files to adjust these defaults. The old `CODEX_SONNET_MODEL` and `CODEX_OPUS_MODEL` translation is no longer used. Shared skills use the model of the agent invoking them.

Read-only Claude agents receive `Read`, `Glob`, and `Grep`; the researcher also receives web tools. The parent supplies shell-derived evidence such as a diff when needed. Codex read-only agents request the `read-only` sandbox; active parent permission overrides can take precedence.

This is the everyday strict configuration. Confirm the initial scope before editing, then continue within that approval; ask again only when scope, externally visible behavior, or risk materially changes.

Both tools hard-block the configured `git push`, `rm`, `ssh`, and `scp` commands. Conversational approval does not lift those bans. Perform these operations manually outside the agent. These are command restrictions, not comprehensive controls over every way to publish, delete, or access a remote system; the shared instructions also prohibit bypassing safety checks.

Claude settings block sensitive-file reads through supported file tools and recognized shell file commands, but do not constrain arbitrary subprocesses that open files indirectly. This repo does not enable Claude's OS-level sandbox. Codex uses `workspace-write`, `on-request` approvals reviewed by the user, and disabled sandbox network access. The model decides when to request approval; the instruction to ask before non-trusted commands is not an automatic command gate. Its sensitive-file and project-only read restrictions are also instructions, not a filesystem read allowlist. Neither setup should be treated as complete secret isolation. A configured deny remains a deny even after conversational approval.

Privacy controls:

- Codex disables client analytics, feedback submission, and OpenTelemetry log, metric, and trace exporters, with prompt logging disabled. These are client controls, not model-training or server-retention settings. See the [Codex configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference).
- Claude disables telemetry, error reporting, feedback uploads, feedback surveys, and opt-in OpenTelemetry collection through its settings environment. Automatic updates and WebFetch's hostname safety check remain enabled. See [Claude data usage](https://code.claude.com/docs/en/data-usage) and [environment variables](https://code.claude.com/docs/en/env-vars).
- Shared instructions require minimal file reads and sanitized external research queries. Private source, logs, and project details must not be sent to external tools or services without approval. These instructions are not an egress firewall. Existing personal hooks, plugins, MCP servers, and higher-priority settings are preserved and have not been audited.
- Hosted inference sends prompts and relevant file/tool content to the provider. Turning off telemetry does not stop this or delete previously transmitted data. Account training preferences and server retention must be verified separately for the account used to sign in. OpenAI API retention controls are described in [Your data](https://developers.openai.com/api/docs/guides/your-data); Claude's qualified Enterprise accounts require separate [ZDR enablement](https://code.claude.com/docs/en/zero-data-retention), with documented exceptions.
- If no content may leave the machine, use a fully local model and enforce offline operation. Neither these settings nor a future OpenShell sandbox makes hosted inference local. Local session histories are retained; this change targets optional external reporting.

For personal subscriptions, complete these account controls separately; the installer cannot set or verify them:

1. In ChatGPT, open Settings → Data Controls and turn off **Improve the model for everyone**. This account preference also applies to Codex. See [ChatGPT data controls](https://help.openai.com/en/articles/7730893-data-controls-faq) and [Codex with a ChatGPT plan](https://help.openai.com/en/articles/11369540-using-codex-with-your-chatgpt-plan).
2. In Claude, open [Privacy settings](https://claude.ai/settings/data-privacy-controls) and turn off model improvement. This applies to Claude Code on personal plans. Anthropic documents 30-day retention for consumer Claude Code users who opt out, so this does not provide zero retention. See [Claude data usage](https://code.claude.com/docs/en/data-usage).

These opt-outs do not provide a guarantee that data is never stored outside your machine. Do not treat this configuration as satisfying a zero-external-storage requirement while using hosted personal subscriptions.

Migration notes:

- The first install with permission tracking preserves all pre-existing Claude permission entries because their ownership is unknown. Review obsolete entries manually; later updates can remove entries recorded as installer-owned. An identical personal copy of an owned entry cannot be distinguished; remove that entry from the manifest if you deliberately take ownership of it.
- Codex installs now select `on-request` with `approvals_reviewer = "user"`, replacing the unsupported `untrusted` policy. Sandbox limits and hard command bans remain in place; ordinary in-sandbox commands are not automatically gated by a trusted-command list.
- The installer removes the old Codex `execpolicy.user_rules` entry when it matches this repo's former value, and removes `features.exec_permission_approvals`.
- Legacy `execpolicy/` files and old Markdown files in Codex's `agents/` directory are left untouched; the current loader uses the new rules path and TOML agents.
- Existing unmarked instruction text is preserved, so a first migration may retain a duplicate of the old shared rules. Review that text if old instructions conflict with the new block.

Validation, without modifying your installed setup:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
bash -n setup-claude.sh setup-codex.sh
```

The tests create and remove temporary destinations inside this repo. Native formats follow the [Codex subagent documentation](https://learn.chatgpt.com/docs/agent-configuration/subagents), [Codex rules documentation](https://learn.chatgpt.com/docs/agent-configuration/rules), and [Claude subagent documentation](https://code.claude.com/docs/en/sub-agents). Sensitive-file restrictions follow [Claude permissions](https://code.claude.com/docs/en/permissions).

Native compatibility tests load the installed Codex configuration and check allowed and forbidden command decisions with `codex execpolicy check`; the commands being checked are not executed. These tests use a temporary `CODEX_HOME` inside the repo and skip when Codex is absent from PATH. Validated with Codex CLI 0.153.0. They do not establish agent model availability or end-to-end sandbox enforcement. Claude Code runtime loading has not been validated here because its CLI is unavailable on PATH.

## Prerequisites

- `bash`
- `git`
- `curl`
- Python 3.11+ for agent setup
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
- `Python 3.11 or newer is required`: ensure `python3` selects a supported interpreter.
- `Run as your normal user, without sudo`: agent settings belong to your user account.
- `Installation failed`: fix the reported malformed file or destination before retrying; settings contents are never printed by the installer.

## License

This repository currently does not define a top-level license.
