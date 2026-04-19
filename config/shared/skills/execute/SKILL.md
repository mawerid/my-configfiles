---
name: execute
description: Implement an approved plan phase precisely — surgical changes only, match existing style, report status on completion.
---

# Execute

Implement an approved plan precisely. Surgical changes only — touch nothing outside the plan.

## Pre-flight

Before writing any code:
- Confirm which phase you are executing.
- Read every file listed in that phase.
- Check for anything in the current code that contradicts the plan. If found, pause and report — do not silently adapt.

## Behavior

- Implement exactly what the plan specifies. No additions, no cleanup of unrelated code.
- Match the existing code style — indentation, naming conventions, comment density.
- Do not remove imports, variables, or functions your changes did not make unnecessary.
- Do not refactor code you are not directly changing.
- After each phase: run the tests specified in the plan and report actual output.

## Status codes

End every phase with one of:

- `DONE` — phase complete, all tests passing.
- `DONE_WITH_CONCERNS` — phase complete, tests passing, but something unexpected was found (describe it).
- `BLOCKED` — cannot proceed without a decision. State exactly what is blocking and what options exist.
- `NEEDS_CONTEXT` — missing information to complete the phase. State exactly what is needed.

## Rules

- Never push to remote.
- Never commit unrelated work.
- Never silently handle an error — if something fails unexpectedly, report it with the actual error output.
- If the plan turns out to be wrong, stop and report — do not improvise a different approach.
