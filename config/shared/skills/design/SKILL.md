---
name: design
description: Think before coding — surface assumptions, propose approaches with tradeoffs, and get approval before any implementation begins.
---

# Design

Think before coding. Transform a request into a validated design before any implementation begins.

## Process

1. **Explore context** — read the relevant files, understand the existing architecture.
2. **Surface assumptions** — list every assumption the request depends on. If any are unclear, ask now.
3. **Clarify before proposing** — ask up to 3 focused questions if scope is ambiguous. Wait for answers.
4. **Propose 2–3 approaches** — for each, state: what it does, why it fits, and its tradeoffs (complexity, risk, reversibility).
5. **Flag risks** — backwards-compatibility breaks, security implications, performance concerns.
6. **State invariants** — constraints that must hold regardless of which approach is chosen.
7. **Recommend** — pick one approach and say why.
8. **Wait for approval** — do not write implementation code until the design is accepted.

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

- No implementation code until the design is explicitly approved.
- If the request is trivial (one-liner fix), say so and propose skipping to execute.
- Simpler is better — prefer the approach with less new surface area.
