# Global operating rules

## Scope and privacy

- Work only inside the current project directory unless explicitly approved otherwise.
- Treat files outside the current repo/worktree as off-limits.
- Never read secrets, `.env` files, key material, certificate files, local databases, or OS/user config unless explicitly asked.

## Default behavior

- Default to explanation, analysis, planning, and review before acting.
- Before making changes, identify the smallest affected file set and confirm the approach.
- Prefer minimal, targeted patches over broad rewrites.
- Do not commit, push, publish, upload, or share unless explicitly asked.
- When fixing a bug, fix only that bug — do not refactor surrounding code.

## Shell usage

- Prefer read-only investigation first.
- Keep shell commands minimal and scoped to the task.
- Never skip hooks (--no-verify) or bypass safety checks.
- For destructive or hard-to-reverse operations, always confirm before proceeding.

## Code quality

- Preserve the existing architecture unless there is a clear reason to change it.
- Avoid adding dependencies unless necessary.
- Prefer deterministic, maintainable solutions over clever ones.
- Do not add speculative abstractions, helpers, or error handling for cases that cannot occur.
- Do not add comments, docstrings, or type annotations to code you did not change.
- Do not add features beyond what was asked.
