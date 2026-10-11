# Implemented Requirement Migration Process

## Purpose

This process migrates already implemented requirements into the canonical requirement catalog while source documents remain normative during the transition.

## Governed records

| Record | Purpose |
|---|---|
| `model/requirements/lifecycle-cases/` | Requirement classification and activation decisions |
| `model/requirements/governance-requirement-catalog.yaml` | Canonical, revisioned `GRQ-*` requirements |
| `model/requirements/requirement-to-artifact-register.yaml` | Confirmed n:m links from exact GRQ revisions to active artifacts |
| `model/requirements/requirement-authority-ledger.yaml` | Authority and migration coverage per source |
| `generated/reports/implemented-requirement-migration.json` | Deterministic inventory and review suggestions |

## Moderated sequence

1. Regenerate the implementation inventory and candidate mappings.
2. Review a source requirement and record `new`, `duplicate`, `extend`, `change`, `supersede`, or `conflict`.
3. Activate only the approved proposal or explicit batch. The case remains `partially_activated` while proposals are open.
4. Review semantic equivalence between the active GRQ revision and each existing artifact.
5. Add an effective register entry with artifact hash, decision actor, role, reference, enforcement mode, and equivalence evidence.
6. Regenerate the migration report and status viewer.
7. Change the authority ledger to `git_authoritative` only after all proposals are resolved and effective.

Example partial activation:

```bash
python scripts/manage_requirement_lifecycle.py activate \
  --case-id RLC-DSCB-STD-REQ-001-MIGRATION \
  --proposal-id RLC-DSCB-STD-REQ-001-MIGRATION-P0001 \
  --effective-from 2026-10-10 \
  --commit <reviewed-commit>
```

## Gate behavior

- Unknown or inactive GRQ revisions fail validation.
- Artifact types absent from `authorized_derivations` fail validation.
- Artifact content must match the recorded SHA-256 hash.
- A changed existing control, platform model, architecture rule, or OPA policy needs an effective register entry.
- An existing release file cannot be modified in place.
- Conflicts cannot be activated or used as derivation authority.
- Architecture artifacts derived from `ARCH-SDD` cannot be silently reassigned to another source.

The report is advisory. A candidate becomes authoritative only through both recorded human decisions.
