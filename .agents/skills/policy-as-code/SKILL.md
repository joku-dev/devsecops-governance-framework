---
name: policy-as-code
description: Review OPA policy behavior, representative inputs, and report-only versus blocking enforcement semantics.
---

# Policy-as-Code Workflow

## Workflow

1. Read `.agents/roles/policy-as-code.yaml` and the report-only versus blocking rules in `AGENTS.md`.
2. Inspect changed files under `policies/opa/`, policy inputs, workflow enforcement, and report generators.
3. Classify whether behavior is report-only, blocking, or unchanged.
4. Check that findings are actionable and traceable to expected evidence.
5. Escalate downstream behavior changes to `release-manager`.

## Validation

Use the repository-pinned OPA version `1.18.2`. Run or request:

```bash
opa version
opa check policies/opa
python3 scripts/validate_governance_repo.py
python3 scripts/validate_runtime_governance.py
python3 -m unittest discover -s tests
```

## Output

Report policy behavior, enforcement classification, affected run contexts, release impact, and validation results.
