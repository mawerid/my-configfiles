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

The checkout’s `agents/` directory owns global instructions, shared skills and
tool-specific settings and roles. Setup links the managed entries individually.
Keep the checkout in place. Edits through these links also edit the checkout.
Setup moves each existing managed entry to a sibling backup named
`.<name>.bak.<id>` before linking it. Repeat runs skip installed links. Run setup again
after adding a skill or role.

Because the installed settings are links, settings changes the CLIs save
(for example Codex project trust or Claude `/config` changes) land in
`agents/`. Run `git diff agents/` before committing and keep machine-specific
or private entries out of the repository. To restore earlier personal
settings, copy them from the `.<name>.bak.<id>` backup into the managed file.

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

This validates, backs up, installs the repository Docker configuration, and
restarts Docker.

## Validation

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
bash -n setup-claude.sh setup-codex.sh
```
