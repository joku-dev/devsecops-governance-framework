---
name: demo-readiness
description: Review demo runbooks, viewer state, current-main artifacts, and ha-CPsWMS story consistency.
---

# Demo Readiness Workflow

## Workflow

1. Read `.agents/roles/demo-readiness.yaml`, `docs/demos/demo-end-to-end-governance.md`, and `docs/demos/demo-ha-cpswms-runtime-governance.md`.
2. Inspect demo docs, sample inputs, current-main generated reports, viewer output, and status indexes.
3. Verify ha-CPsWMS DevSecOps and architecture status, baselines, and run identifiers where docs claim current state.
4. Preserve demo artifacts versus current-main artifacts.
5. Confirm report-only and blocking semantics remain clear.

## Validation

Run or request:

```bash
python3 scripts/validate_runtime_governance.py
python3 scripts/validate_governance_repo.py
python3 scripts/run_demo.py
python3 -m unittest discover -s tests
```

## Output

Report demo consistency, viewer consistency, current-main impact, and validation results.
