---
name: test
description: TDD workflow — write failing tests first, implement minimally to pass, refactor, repeat. Behavior-focused, no mocks for internal code.
---

# Test

TDD workflow. Write tests first, make them pass, then refactor. Applied to deterministic functions where regressions matter.

## Cycle

### Red
- Write a test for one specific behavior before writing the implementation.
- Run the test — confirm it fails for the right reason (not a syntax error or import failure).
- Test name should describe the behavior: `test_returns_empty_list_when_input_is_none`, not `test_foo`.

### Green
- Write the minimal code that makes the test pass.
- Do not add logic the test does not require.

### Refactor
- Clean up only what you just wrote.
- Re-run the full test suite — all tests must still pass.
- Repeat for the next behavior.

## Test rules

- Test behaviors, not implementations. Tests should not break when internal logic is reorganized.
- No mocks for internal code. Mock only at system boundaries: external APIs, filesystem, clock.
- One logical assertion per test.
- Tests must be deterministic — no random data, no time-dependent assertions without a fixed clock.

## Output format

After each cycle, report:
```
RED:    <test name> — fails: <actual failure message>
GREEN:  <test name> — passes
SUITE:  <number> passed, <number> failed
```

## When to apply

Use TDD when:
- The function has multiple callers and regressions are costly.
- The behavior is complex enough that getting it right on the first try is unlikely.

Skip TDD for: one-off scripts, UI glue code, trivial wrappers.
