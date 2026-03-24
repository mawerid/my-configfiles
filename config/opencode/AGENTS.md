# Global operating rules

## Scope and privacy

- Work only inside the current project directory unless I explicitly approve otherwise.
- Treat files outside the current repo/worktree as off-limits.
- Never inspect secrets, `.env` files, key material, certificate files, local databases, or OS/user config unless I explicitly ask.

## Default behavior

- Default to explanation, analysis, planning, and review.
- Before editing, say which files you want to change and why.
- Prefer minimal, targeted patches over broad rewrites.
- Do not commit, push, publish, upload, sync, or share unless I explicitly ask.

## Tool use

- Prefer read-only investigation first.
- Keep shell usage minimal and relevant.
- Avoid network access unless it is clearly required and approved.
- Do not spawn subagents unless the chosen agent is specifically designed to do so.

## Quality

- Preserve the existing architecture unless there is a strong reason to change it.
- Avoid adding dependencies unless necessary and approved.
- Prefer deterministic, maintainable solutions over clever ones.
- When suggesting validation, propose the smallest safe check that proves the change.

## Model-specific guidance

- For Qwen3.5 9B: use it for main chat, planning, reviews, and guarded implementation.
- For Nemotron 3 Nano 4B: use it for lightweight repo exploration, summaries, and low-risk read-only lookup.
- Do not use the small model for risky edits, broad refactors, or security-sensitive judgment when the main model is available.