---
name: release
description: Prepare a versioned release MR and verify the landed commit, tag and publication after human merge.
---

Read the project's release policy and the create-mr skill's mr-workflow.md. Resolve default branch, previous tag, version source, changelog, artifact names, publication job and registry. Reconcile unreleased changes with the project's versioning rules and confirm breaking changes. Check any outstanding plan and external acceptance.
Prepare the release on a topic branch, preserving local edits. Update the version and dated changelog, check the build and required artifacts and record commands, actual results, checked head and tree. Use create-mr with explicit publication authorization. Retain the release record. Reuse an existing branch and MR on resume.
After human merge, verify identity, exact landed changes, successful required checks and target ancestry. The bundled GitLab helper supports fast-forward SemVer releases with static pyproject metadata, a dated CHANGELOG.md and GitLab PyPI artifacts. For other project formats follow the project's release procedure with the same evidence checks. Run the helper in draft mode first. Publish an annotated tag only when explicitly requested. Match an existing tag by object, commit and message. Recheck after an uncertain write.
Report the MR, landed SHA, tag, actual pipeline, upload job and registry artifacts. Inspect partial publication before any retry.

For a SemVer project, classify incompatible public changes as major, backward-compatible features as minor, and fixes as patch. Reconcile the proposed bump with the changelog and actual public contracts. Follow project policy for pre-releases and version zero. Include migration notes for breaking changes and use the project's actual previous tag for compare links.
