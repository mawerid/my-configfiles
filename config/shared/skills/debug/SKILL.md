---
name: debug
description: Systematic root-cause investigation — reproduce, trace backward, form one hypothesis, test it, fix only after cause is confirmed.
---

# Debug

Systematic root-cause investigation. Find the real cause before touching any code.

## Process

### Phase 1 — Reproduce
- Read the error in full. Do not skim.
- Identify the minimal input or action that triggers the bug.
- Review recent changes: `git log --oneline -10`, `git diff`.
- Add temporary instrumentation (print/log) to trace the actual data flow.

### Phase 2 — Trace backward
- Start from the failure point and trace back through the call chain.
- Find analogous code that works correctly. Enumerate the concrete differences.
- Do not speculate — only list differences you can point to in the code.

### Phase 3 — Hypothesize
- Form one specific causal claim: "X causes Y because Z."
- Design the minimal test that would prove or disprove this claim.
- Test it. If the hypothesis is wrong, return to Phase 2.

### Phase 4 — Fix
- Only proceed after Phases 1–3 confirm the root cause.
- Create a failing test that captures the bug before fixing it.
- Implement the minimal fix.
- Run the full test suite. Remove instrumentation.
- If three fix attempts fail, stop and report findings.

## Rules

- One hypothesis at a time.
- No `sleep` to paper over timing issues — find the actual race condition.
- Do not change multiple variables at once — you will lose the signal.
- Do not push a fix that you cannot explain causally.

## Report format

```
Symptom:    <what fails and how>
Root cause: <the specific code path that causes it, with file:line>
Fix:        <what changed and why that breaks the causal chain>
Test:       <test name that would have caught this>
```
