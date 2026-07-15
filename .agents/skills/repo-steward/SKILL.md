---
name: repo-steward
description: Review repository hygiene, scope control, validation evidence, generated-output noise, and commit readiness.
---

# Repo Steward Workflow

## Workflow

1. Read `.agents/roles/repo-steward.yaml`, `AGENTS.md`, and `docs/operations/ai-working-rules.md`.
2. Inspect `git status --short`, `git diff --stat`, and changed file scope.
3. Reject local artifacts such as `.DS_Store` and accidental `__pycache__` files.
4. Identify generated timestamp-only noise and keep it out of commits unless intentional.
5. Verify validation commands were run or clearly explain why they were not.

## Validation

Run or request:

```bash
git status --short
git diff --check
python3 scripts/validate_runtime_governance.py
python3 scripts/validate_governance_repo.py
python3 -m unittest discover -s tests
```

## Output

Report scope, hygiene findings, validation summary, residual risk, and commit readiness.
