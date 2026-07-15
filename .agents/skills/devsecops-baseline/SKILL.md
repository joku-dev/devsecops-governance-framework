---
name: devsecops-baseline
description: Review DevSecOps control baseline, platform mapping, traceability, and evidence model changes.
---

# DevSecOps Baseline Workflow

## Workflow

1. Read `.agents/roles/devsecops-baseline.yaml` and the DevSecOps governance map in `docs/ai-index.md`.
2. Inspect changed files under `model/controls/`, `model/platform/`, `model/evidence/`, `model/traceability/`, and `pipeline-baseline/`.
3. Determine whether controls, evidence types, platform capabilities, automation classification, or traceability changed.
4. Identify policy-as-code or release-manager escalation needs.
5. Protect released DevSecOps baselines from silent mutation.

## Validation

Run or request:

```bash
python3 scripts/validate_governance_repo.py
python3 -m unittest discover -s tests
```

## Output

Report control impact, evidence impact, traceability impact, release impact, and validation results.
