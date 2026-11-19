---
name: approve-mr
description: Approve a GitLab merge request after independently checking its current head, review evidence, discussions and pipeline state.
---

# /approve-mr

An explicit user request to approve authorizes approval after the checks below. `--dry-run` inspects
and proposes only. Never resolve discussions, post, push, tag or merge.
Read [shared mechanics](../create-mr/mr-workflow.md) and
[the review checklist](../review/SKILL.md).

1. Verify host/project/MR identity, authenticated reviewer and current diff
   refs. The reviewer must differ from the author. Inspect current code in an
   isolated detached worktree using `GitRepo.review_checkout`, preserving
   the caller's dirty files. Review against the plan or MR claims, original
   findings and intervening changes as review-mr specifies; approval needs
   that same evidence, whether produced now or checked from a prior review.
2. Confirm actual evidence identifies this exact head and relevant scope,
   including applicable acceptance. Refresh and rerun stale evidence. No
   blocking findings or unresolved discussions may remain. Do not resolve
   them merely to approve. A draft MR cannot be approved. An existing head
   pipeline must belong to this SHA and have succeeded; no pipeline is
   explicitly absent and requires sufficient independent checks. Publishing
   Publication CI alone cannot verify runtime behavior; unrun mandatory external integration acceptance blocks
   approval of claims that depend on it.
3. Prepare the shared review report and run `approve --input FILE --publish`
   only with explicit publication authorization; add --dry-run when requested. The helper
   checks current refs, evidence, reviewer, threads and pipeline; its approve
   payload includes the exact SHA so a racing push is rejected by GitLab.
   A changed head means repeat review/checks, never just replace the SHA in
   the report. An already present approval is reported without another write.
   After a timeout, inspect approvals before resuming; never blindly retry.
4. Report MR link, approved head and evidence, or the concrete blocker.
   Clearly label dry runs as unapproved. Human merge is the next boundary.
