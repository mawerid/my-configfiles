---
name: review
description: Independent code review — validate implementation against requirements and invariants, confidence-filtered findings, Critical/Important tiers.
---

# Review

Independent code review. Validate the implementation against requirements without rationalizing the author's choices.

## Process

1. **Read the requirements** — the original request, design output, and plan (if they exist).
2. **Read the diff** — only what changed.
3. **Check plan adherence** — does the diff match what was planned? Flag any undeclared changes.
4. **Check correctness** — does the implementation actually do what the requirement says?
5. **Check invariants** — are all stated invariants preserved?
6. **Filter by confidence** — only report findings you are ≥80% confident are real issues.

## Findings format

Each finding must include:
- **Tier**: `Critical` (breaks correctness or security) or `Important` (degrades quality, maintainability, or safety)
- **Location**: `file:line`
- **Confidence**: percentage
- **Issue**: one sentence describing what is wrong
- **Fix**: the smallest change that resolves it

## Output format

```
## Plan adherence
<1–3 lines: does the diff match the plan? Any undeclared changes?>

## Findings
[Critical] file.py:42 (95%) — <issue>. Fix: <fix>
[Important] other.py:17 (85%) — <issue>. Fix: <fix>

## Verdict
<one sentence: approved / approved with required fixes / needs rework>
```

## Rules

- Do not report style preferences as findings.
- Do not report speculative future problems unless they are high-confidence and high-impact.
- If there are no findings, say so explicitly — do not invent issues to seem thorough.
