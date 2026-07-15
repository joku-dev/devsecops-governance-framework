---
name: governance-analysis
description: Analyze governance intent and map it to affected requirements, controls, architecture markers, evidence, and release decisions.
---

# Governance Analysis Workflow

## Workflow

1. Read `docs/governance/governance-roles-and-agent-profiles.md` and `.agents/roles/governance-analyst.yaml`.
2. Identify whether the change is normative, explanatory, evidence-related, release-impacting, or demo-only.
3. Map affected artifacts across `docs/governance/`, `model/`, `architecture/`, and generated impact reports.
4. Separate intended derived changes from artifacts that must remain unchanged until review.
5. Record assumptions and unresolved decisions for the change request or PR note.

## Validation

Run or request:

```bash
python3 scripts/validate_governance_repo.py
python3 scripts/validate_runtime_governance.py
```

## Output

Report governance intent, affected artifacts, open decisions, required reviewers, and validation results.
