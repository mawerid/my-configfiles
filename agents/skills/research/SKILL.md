---
name: research
description: Deep investigation of external questions — decompose into sub-questions, gather evidence from primary sources, synthesize with citations.
---

# Research

Deep investigation for questions that go beyond the current codebase. Produce evidence-based answers with citations.

## Process

1. **Decompose** — break the question into 2–5 atomic sub-questions.
2. **Investigate each** — consult official docs, GitHub issues, the codebase, and CLI output. Prefer primary sources.
3. **Triangulate** — if two sources conflict, surface the conflict and note which is more authoritative.
4. **Synthesize** — produce a direct answer, not a list of links.

## Output format

For each sub-question:

```
Question: <the atomic question>
Answer:   <direct answer>
Evidence: <source — URL, file:line, or command + output>
Caveats:  <version constraints, known exceptions, conflicting info>
```

End with a **Summary** — one paragraph that directly answers the original question.

## Rules

- Cite every non-trivial claim.
- Flag uncertainty explicitly — do not fill gaps with plausible guesses.
- Do not propose implementation until research is complete and summarized.
- If the answer requires trying something in the codebase, do a read-only investigation first.
