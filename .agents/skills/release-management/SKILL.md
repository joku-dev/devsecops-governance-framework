---
name: release-management
description: Review release impact, released baseline integrity, checksums, reusable workflows, and migration implications.
---

# Release Management Workflow

## Workflow

1. Read `.agents/roles/release-manager.yaml` and `docs/releases/release-and-migration-model.md`.
2. Inspect changed files under `releases/`, `docs/releases/`, reusable baseline workflows, schemas, and policies.
3. Classify impact as no release, release candidate, patch, minor, or major.
4. Verify release metadata, checksums, release docs, and workflow refs move together.
5. Reject silent mutation of existing released baselines.
6. Compare packaged files with the release manifest and checksum records; treat any mismatch in an existing release as a blocking release-integrity finding.

## Validation

Run or request:

```bash
python3 scripts/validate_governance_repo.py
python3 scripts/validate_runtime_governance.py
python3 -m unittest discover -s tests
```

## Output

Report release classification, baseline mutation decision, downstream migration impact, and validation results.
