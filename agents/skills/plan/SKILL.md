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

For each phase, state observable acceptance criteria and identify any documentation affected. Use the project’s existing plan location when a written plan is requested.

For a persistent plan, follow the project's template, or use docs/plans/<slug>.md when a plan file is requested and no convention exists. Link the originating idea, accepted decisions, design deltas and non-goals. Split large work into independently verifiable milestones. Write ordered checkbox steps with dependencies, affected files and a concrete acceptance command or observation. Grade each step using the work skill’s tiers.md. Name the decision owner and deadline for open questions. Record required external checks, docs to update and final acceptance. End with the steps ready for review.
