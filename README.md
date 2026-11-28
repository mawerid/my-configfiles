# My Config Files

Bootstrap scripts and configurations for Ubuntu and macOS: Zsh, tmux, Neovim,
Docker, Claude Code, Codex, and Herdr.

## Install

```bash
git clone <your-repo-url> ~/config
cd ~/config
bash install.sh
```

`install.sh` selects the macOS or Ubuntu bootstrap. Each run also installs or
upgrades `gh`, `glab`, `lazydocker` and `uv` (apt and checksum-verified GitHub
releases on Ubuntu, Homebrew on macOS) and, through `uv tool`, `ruff`,
`pre-commit` and `euporie`. Configure the agents as your normal user:

```bash
bash setup-claude.sh
bash setup-codex.sh
```

The checkout’s `agents/` directory owns global instructions, shared skills and
tool-specific settings and roles. Setup links the managed entries individually.
Keep the checkout in place. Edits through these links also edit the checkout.
Repeat runs skip installed links. Run setup again after adding a skill or role.

Because the installed settings are links, settings changes the CLIs save
(for example Codex project trust or Claude `/config` changes) land in
`agents/`. Run `git diff agents/` before committing and keep machine-specific
or private entries out of the repository. To restore earlier personal
settings, copy them from that run's backup into the managed file.

## tmux and Neovim

On Ubuntu x86-64 and ARM64, the bootstrap installs the official Neovim nightly
and installs the Tree-sitter CLI nightly if the available CLI is older than
0.26.1 or missing. The binaries are linked into `~/.local/bin`. macOS uses
Homebrew for Neovim and the Tree-sitter CLI.

The macOS bootstrap also installs JetBrainsMono Nerd Font. To install the font
by itself, run `brew install --cask font-jetbrains-mono-nerd-font`. Select
**JetBrainsMono Nerd Font Mono** in your terminal profile to display Neovim icons.

The bootstrap installs Lazygit with Homebrew on macOS or apt on Ubuntu. On
Ubuntu releases without an apt package, it installs the official binary into
`~/.local/bin`. In Neovim, `Space g g` opens Lazygit at the Git root, and
`Space g G` opens it in the current directory.

Setup uses the active Neovim config path, including `XDG_CONFIG_HOME` and
`NVIM_APPNAME`. It updates individual repo-managed files in that profile.
Neovim's existing plugin lockfile and enabled LazyVim extras carry over on
reinstall.

Mason installs Pyright when Node.js and npm are available, and gopls when Go
is available. Neovim can also use an existing language server on `PATH`.

### Install the Nerd Font on Ubuntu

Run these commands on the Ubuntu desktop where you open your terminal.

```bash
sudo apt update
sudo apt install -y curl xz-utils fontconfig

(
  set -eu
  font_dir="${XDG_DATA_HOME:-$HOME/.local/share}/fonts/JetBrainsMonoNerdFontMono"
  archive="$(mktemp)"
  trap 'rm -f "$archive"' EXIT

  curl -fsSL \
    https://github.com/ryanoasis/nerd-fonts/releases/download/v3.5.1/JetBrainsMono.tar.xz \
    -o "$archive"

  printf '%s  %s\n' \
    04d5e8f903693f9dd13e16f867e994834e681eb3c72c0d337a770dcda09010cf \
    "$archive" | sha256sum --check

  mkdir -p "$font_dir"
  tar -xJf "$archive" -C "$font_dir" \
    JetBrainsMonoNerdFontMono-{Regular,Bold,Italic,BoldItalic}.ttf
  fc-cache -f "$font_dir"
)
```

Select **JetBrainsMono Nerd Font Mono** in your terminal profile, then open a
new terminal window and start Neovim. For SSH sessions, select the font on the
machine displaying the terminal. [Nerd Fonts release](https://github.com/ryanoasis/nerd-fonts/releases/tag/v3.5.1)

## Herdr desktop app

Install and open the Herdr desktop app once to initialize its layouts. Then run
the setup command. [Herdr installation](https://github.com/herdrdev/herdr-app#install)

```bash
bash setup-herdr.sh
```

Setup copies settings to `~/.config/herdr-app` and installs the checked-in
keyboard shortcuts: Herdr's defaults for the platform plus tmux mode. Set `HERDR_APP_HOME` or pass `--target-dir` to use
a different app home. Setup derives Files Preview from the installed main
layout. Each run also installs the newest
[Material Icon Theme](https://github.com/material-extensions/vscode-material-icon-theme)
icons (MIT) from npm after checking the published SHA-512; without network it
keeps the installed icons. Changes made in Herdr stay in the app home until you copy them back
into `config/herdr-app/`.

`Ctrl+A` starts the tmux-style Herdr mode on macOS and Linux. Press it twice to send a
literal `Ctrl+A` to the terminal, including when you run tmux inside Herdr.

| After `Ctrl+A` | Action |
| --- | --- |
| `c`, `1` through `9`, `n` / `p` | New tab, select a tab, next / previous tab |
| `\|` / `-` | Split right / down |
| `h` / `j` / `k` / `l` | Focus left / down / up / right |
| `H` / `J` / `K` / `L` | Resize in that direction by 5 pixels, repeat within 300 ms |
| `[` | Copy mode. Move with `h/j/k/l`, start a selection with `v`, copy with `y`, or exit with `Esc` |
| `z` | Toggle pane zoom |
| `f` / `g` | Show **Files** / **Changes**, or hide the panel when that view already shows |

Keyboard resizing requires Herdr's `pane.resize` command. Herdr reloads its
config files automatically when they change.

Files and Changes take the keyboard when you move focus to them (`Ctrl+A` `l`,
or Herdr's pane-focus keys). In **Files**, arrows or `h/j/k/l` walk the tree,
`Enter` or `Space` opens a folder or previews a file, and `Esc`, `←` or
`Backspace` leaves a preview. In **Changes**, `↑` / `↓` or `j` / `k` step through
the changed files and show each diff, `Enter` toggles the diff, and `i` jumps to
the commit message. `Esc` in either panel returns focus to the terminal.

### Files Preview, HTML and PDF

After setup, switch to the preview layout.

```bash
herdr-app do layout.switch --name files-preview
```

Open **Files** and select a Markdown file to switch between **Rendered** and
**Raw**. The same controls work for local and remote spaces. Files and folders
show Material icons; git-ignored entries are dimmed.

Click an HTML file in a remote space to open it in your browser. The mod
starts a small server for the Files folder on that machine (it needs
`python3` there) and an SSH tunnel to it. Both close after 5 minutes without
use and start again on the next click. The Herdr machine name must be
something `ssh` can reach, such as a Host from `~/.ssh/config`. Select
**View source** to load the HTML in Herdr. Local HTML opens
as source. A PDF shows an **Open in browser** button in a remote space, through
the same tunnel, and **Open** locally for your default PDF app. The layout and panel build on
Herdr's defaults. [Upstream files](https://github.com/herdrdev/herdr-app/tree/master/defaults) · [Apache-2.0 license](config/herdr-app/LICENSE-files-preview)

## Global workflows

Codex discovers user skills in `~/.agents/skills`. Claude discovers them in
its configuration directory’s `skills/` and lists the managed skills by
default. Start a fresh session after setup. Use `$idea` in Codex or `/idea`
in Claude for a decision-by-decision design discussion. Follow with `plan`,
`work`, `retire-plan` and `close-cycle`. Use `next`, `handoff`, `wait-what`,
`retro` and `refactor-review` as needed. For GitLab use `create-mr`,
`review-mr`, `respond-mr`, `approve-mr` and `release`. Remote actions still
require user authorization and applicable tool permissions. Run helper scripts
from the project using their installed paths. The GitLab helper uses authenticated
`glab`; release publication checks support the GitLab PyPI registry.

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

On Linux, setup validates and installs a changed daemon configuration, then
restarts Docker. If the restart fails, setup restores the previous state and
attempts another restart.

## Install backups

| Setup | Backed up | Skipped or kept in place |
| --- | --- | --- |
| Zsh | A replaced `~/.zshrc` entry goes in `~/.zshrc.bak.*/.zshrc`. | Matching regular files and existing Oh My Zsh, theme, plugin, and TPM directories are reused. |
| tmux and Neovim | None. | Managed config files are replaced in place. Unrelated Neovim files, plugin locks, and LazyVim extras stay in the active profile. |
| Ubuntu editor binaries | An existing entry in `~/.local/bin` is saved under `<name>.bak.*/` before it is replaced, if it points outside this bootstrap’s managed builds or is a regular file. | Previous managed releases remain under the editor data directory. Package-manager binaries stay in their package locations. |
| Codex and Claude | Replaced settings, instructions, roles, skills, or rules and eligible legacy entries go under `.setup-backups/<UTC timestamp>/` in the corresponding config directory. | Current links, unrelated entries, and legacy symlinks are skipped. |
| Herdr | Replaced settings, macOS keys, managed mod files, and the generated preview layout go under `.setup-backups/<UTC timestamp>-*/` in the app home. | Matching files are skipped. The shipped layout and your `html-forwards.json` are left in place. |
| Docker | None. | Setup keeps the previous config temporarily for rollback and removes it on exit. An identical file skips validation and restart. |
| OpenShell | None. | Gateway and research session state use their existing runtime directories and volumes. |

First installs create no backup for paths with no existing entry.

## Validation

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
for script in install.sh setup-*.sh script/*.sh; do bash -n "$script" || exit; done
```
