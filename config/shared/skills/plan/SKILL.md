---
name: plan
description: Convert an approved design into a concrete implementation plan with exact file paths, affected symbols, ordered phases, and test strategy.
---

# Plan

Convert an approved design into a concrete, ordered implementation plan. This is the contract for execution — scope is frozen after this step.

## Process

1. **Use the agreed scope** — planning may be part of the initial proposal; no separate design approval is needed to prepare it.
2. **Enumerate files** — list every file that will be created, modified, or deleted.
3. **Per-file changes** — for each file: affected symbols or sections, what changes (interface signatures, logic replaced, added functions).
4. **Order phases** — break work into sequential phases where each phase leaves the code in a working state.
5. **Test strategy** — name the tests that will verify each phase (new tests or existing ones to run).
6. **State invariants** — copy invariants from the design; add any new ones discovered while planning.

## Output format

```
## Phases

### Phase 1: <name>
Files:
  - path/to/file.py  (affected symbol): <what changes>
  - path/to/other.py (new):         <what it contains>
Tests: <test names or commands>

### Phase 2: <name>
...

## Invariants
- <constraint>

## Out of scope
- <thing explicitly not being done>
```

## Rules

- Use exact file paths — never "the config file" or "the handler".
- Run relevant checks for each phase; use the full suite when shared behavior or unresolved risk warrants it.
- Ask before expanding scope; routine implementation choices within an approved plan need no new approval.
- Brevity: small changes ≤ 1 screen, medium ≤ 3 screens.
