---
name: evidence-and-intake
description: Review result intake, evidence context, status indexes, and governance status viewer changes.
---

# Evidence And Intake Workflow

## Workflow

1. Read `.agents/roles/evidence-and-intake.yaml` and `docs/operations/evidence/governance-result-intake-and-viewer-usage.md`.
2. Inspect changed files under `status/`, intake scripts, result index generators, and `generated/viewer/`.
3. Classify evidence context as `mainline`, `branch`, `pull_request`, or `manual`.
4. Verify that only appropriate contexts update official latest state.
5. Check viewer impact and demo-readiness escalation needs.

## Validation

Run or request:

```bash
python3 scripts/generate_repository_results_index.py
python3 scripts/generate_architecture_results_index.py
python3 scripts/generate_typed_evidence_results_index.py
python3 scripts/generate_status_viewer.py
python3 scripts/validate_governance_repo.py
python3 -m unittest discover -s tests
```

## Output

Report evidence context, latest-state decision, viewer impact, affected repositories, and validation results.
