---
name: design
description: Think before coding — surface assumptions, propose approaches with tradeoffs, and get approval before any implementation begins.
---

# Design

Think before coding. Transform a request into a validated design before any implementation begins.

## Process

1. **Explore context** — read the relevant files, understand the existing architecture.
2. **Surface assumptions** — identify assumptions that could change the approach. Ask only when the answer matters.
3. **Clarify before proposing** — ask up to 3 focused questions if scope is ambiguous. Wait for answers.
4. **Compare meaningful alternatives** — when alternatives affect the decision, state: what it does, why it fits, and its tradeoffs (complexity, risk, reversibility).
5. **Flag risks** — backwards-compatibility breaks, security implications, performance concerns.
6. **State invariants** — constraints that must hold regardless of which approach is chosen.
7. **Recommend** — pick one approach and say why.
8. **Confirm scope before editing** — existing approval covers the agreed work; do not request it again.

## Output format

```
## Assumptions
- <assumption>

## Approaches
### A: <name>
<what, why, tradeoffs>

### B: <name>
<what, why, tradeoffs>

## Risks
- <risk>

## Invariants
- <constraint that must hold>

## Recommendation
<approach + one-sentence rationale>
```

## Rules

- Get approval for the affected files and approach before editing; reuse approval already given for that scope.
- For small changes, a short affected-file list, approach, and verification step are enough; skip a separate design document.
- Simpler is better — prefer the approach with less new surface area.
