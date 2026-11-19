---
name: refactor-review
description: Measure structural debt, verify hotspots and propose behavior-preserving milestones.
---

Start from the previous review and its unresolved findings or from the last release. From the project root run the adjacent scripts/sizes.sh BASE for tracked code sizes and churn. For Python run fn_lengths.py, duplicates.py and rule_patterns.py in scripts/ against the source tree (set REVIEW_ROOT to narrow it). Use project-native analysis for other languages.
Read each candidate in context. Distinguish measurements from verified duplication and intentional similarities. Recheck past findings, including those already fixed. Name related tests and public invariants. Where behavior may already differ, propose a regression test before consolidation.
Produce one idea with the reviewed commit, evidence, files and symbols, findings grouped into milestones, intentional exceptions, possible orderings, and an acceptance check per milestone. Use idea to resolve choices before implementation.
