---
name: create-mr
description: Push a checked topic branch and create or update its GitLab merge request to the project default branch, reusing an existing MR for that branch.
---

# /create-mr

An explicit user request to publish authorizes pushing the selected topic branch and creating or
updating its MR. `--dry-run` only inspects and drafts. Never merge.
Read [shared mechanics](../create-mr/mr-workflow.md) before remote actions.

1. Resolve origin, numeric project identity and the topic branch. Record
   status and relevant staged/unstaged diffs in an authorized location. Identify unrelated untracked files by path. Preserve unrelated edits. Refuse the project default branch/detached HEAD; use the
   human's selected branch/base. Don't commit unrelated files or rewrite
   history to make the branch clean. Identify all commits in its MR scope.
2. Inspect the branch diff against the project default branch and any existing open MR for the
   exact source/target, following every page. Read the plan if there is one.
   Verify scope, changelog/docs obligations and [review checklist](../review/SKILL.md).
   After committing fixes, use `GitRepo.validation_checkout(head)` from the
   shared helper to run `the project’s documented checks` and appropriate
   acceptance checks in a detached checkout of the exact commit to push; record
   their actual commit, scope and counts. Unrun external integration acceptance stays
   explicit and blocks claims that depend on it.
3. Write a title and description for a reviewer without this conversation:
   problem, resulting behavior and validation with commit/scope/limits.
   Use the existing template when present; retain useful reviewer context
   when updating an MR. Do not claim a remote pipeline from local checks.
4. Prepare the helper's create JSON in an authorized location. Use `create
   --input FILE --publish` only with explicit publication authorization, or add `--dry-run`.
   It verifies origin/head, pushes only that head, then searches again for
   an existing MR before creating or updating. It never force-pushes or
   pushes tags. Recover a partial action by inspecting before retrying.
5. Report MR link/IID, source/target and published head, checks and remaining
   acceptance. For a dry run, show the concrete proposed title/description
   and actions, clearly marked unpushed/unposted. Human merge remains next.
