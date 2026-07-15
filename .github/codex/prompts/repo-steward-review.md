# Repo Steward Review

Use this prompt for a focused hygiene and commit-readiness review.

## Source Of Truth

Read:

```text
.agents/roles/repo-steward.yaml
.agents/skills/repo-steward/SKILL.md
AGENTS.md
docs/operations/ai-working-rules.md
```

## Review Procedure

1. Inspect `git status --short`.
2. Inspect `git diff --stat`.
3. Inspect `git diff --check`.
4. Check for local artifacts such as `.DS_Store`, `__pycache__`, editor files, and unrelated generated timestamp-only noise.
5. Verify validation commands were run or document why they were not.
6. Confirm the commit scope is coherent and does not mix unrelated governance concerns.

## Output Format

```text
Scope:
- focused|mixed

Hygiene:
- pass|fail
- notes

Validation:
- <command>: run|not run|not applicable

Commit readiness:
- ready|not ready
- reason
```
