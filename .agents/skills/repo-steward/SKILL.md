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

## Review completion

When a revision-bound review plan is in use, apply `.agents/review-protocol.yaml`
and synthesize all specialist results last. Account for their scope, required
outputs, findings and validation evidence. Identify missing or stale reviews;
never count a selection as execution or a coordinator's role lenses as separate
independent agents. Use the completion check in
`docs/operations/agents/how-to-run-agent-review.md`. Its result is declared review
evidence, not human approval. Small focused changes can retain ordinary review.

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
