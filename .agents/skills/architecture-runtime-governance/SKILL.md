---
name: architecture-runtime-governance
description: Review architecture governance changes across markers, gates, runtime policy, evidence schemas, and architecture releases.
---

# Architecture Runtime Governance Workflow

## Workflow

1. Read `.agents/roles/architecture-runtime-governance.yaml` and the architecture section of `docs/ai-index.md`.
2. Inspect changed files under `architecture/`, architecture OPA policies, architecture schemas, and architecture releases.
3. Determine whether L1, L2, L3, or GOV behavior changes.
4. Classify policy impact and whether existing released architecture baselines are touched.
5. Escalate release-impacting changes to `release-manager`.

## Validation

Run or request:

```bash
python3 scripts/validate_runtime_governance.py
python3 -m unittest discover -s tests
```

## Output

Report architecture impact, policy impact, release impact, affected evidence, and validation results.
