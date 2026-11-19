---
name: work
description: Run one step, a range, or the remaining batches of an approved plan and verify the handoff.
---

Read the plan, project instructions and tiers.md beside this skill. An explicit step or range limits the run. A whole-plan request continues through all remaining batches and retirement.
1. Record branch, HEAD, status and relevant staged/unstaged changes. Assign ownership of the selected files. Preserve pre-existing work. Resolve routine decisions locally and record material plan corrections.
2. Group up to three adjacent tier 1/2 steps when dependencies permit. Isolate tier 3 work and end a batch at external acceptance gates. Run batches sequentially in a shared checkout. When delegation is authorized and supported, give each fresh worker the plan, assigned steps, baseline, constraints and acceptance checks.
3. Implement and verify each step with execute. Investigate persistent failures with debug. Inspect the actual diff against the step, run the project's checks and record observed results. Tick only verified steps. Make one commit per step when authorized. Otherwise keep an explicit record of completed changes.
4. Verify each worker's diff, evidence and handback before continuing. On a miss, narrow the task and retry once. Report unresolved discrepancies or a human-only check with the exact action and expected result. Resume from verified state.
5. Report remaining steps for a bounded run. For a whole-plan run, use retire-plan after final acceptance.

Follow the project's git policy. For a trunk-based project, start authorized changes on a topic branch from the verified default branch, scope each commit to a checked step, and land via the project's review process. Keep publication and merge decisions separate. Use the project's commit format and record user-visible changes in the changelog when applicable.
