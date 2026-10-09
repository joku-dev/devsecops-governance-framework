# Hybrid Requirement Lifecycle

## Purpose

This process supports the transition from externally supplied normative documents to Git-native requirements. During the transition, the Requirement Authority Ledger states which representation is authoritative. A file location alone never changes authority.

## Normative model

| Artifact | Function |
|---|---|
| `model/requirements/requirement-authority-ledger.yaml` | Declares authority mode and migration coverage per source |
| `model/requirements/lifecycle-cases/` | Preserves analysis, human decisions and activation evidence per requirement |
| `model/requirements/governance-requirement-catalog.yaml` | Canonical Git requirement revisions after activation |
| `docs/governance/requirements/` | Human-readable projection generated during activation |

Authority modes are `external_authoritative`, `migration_in_progress`, `git_authoritative`, and `retired`. During `migration_in_progress`, the approved source document remains normative for unresolved requirements. Git becomes normative only after every proposal has a human decision, activation is complete, and `complete-migration` records a catalog release.

## Use case 1: incoming document

1. Classify and register the document as a candidate through Source Document Intake.
2. Obtain the separate source approval required by the intake process.
3. Run `import-source`; this creates one proposal per extracted requirement and opens ledger coverage.
4. Run `reanalyze-all`; the deterministic review suggests `duplicate`, `new`, or `change` and lists likely matches.
5. A responsible human records one decision per proposal. The complete decision vocabulary is `duplicate`, `new`, `extend`, `change`, `supersede`, and `conflict`.
6. Resolve conflicts. An approved unresolved conflict cannot be activated.
7. Run `activate`; this creates or revises immutable canonical requirement records. Rejected and duplicate proposals retain their decisions but create no new requirement.
8. Review and update authorized derived artifacts. `report_only` may be selected; blocking needs a separate enforcement authorization.
9. Run `complete-migration` only after complete coverage. This changes the ledger to `git_authoritative`.

## Use case 2: Git-native requirement

Create a small source Markdown file under `docs/governance/requirements/native-sources/`, then run `start-native`. Analysis, human decision, activation, derivation and PR validation follow the same steps. A Git-native proposal does not need a source-document register entry or a ledger migration.

## Commands

```bash
python3 scripts/manage_requirement_lifecycle.py import-source --case-id RLC-EXAMPLE-MIGRATION --source-id EXAMPLE-REQ-001
python3 scripts/manage_requirement_lifecycle.py reanalyze-all
python3 scripts/manage_requirement_lifecycle.py report
python3 scripts/manage_requirement_lifecycle.py decide --case-id RLC-EXAMPLE-MIGRATION --proposal-id RLC-EXAMPLE-MIGRATION-P0001 --disposition approve --classification new --decided-by jane.doe --decision-role governance-owner --rationale "Approved as a new requirement" --authorized-derivation documentation
python3 scripts/manage_requirement_lifecycle.py activate --case-id RLC-EXAMPLE-MIGRATION --effective-from 2026-10-09 --commit <commit>
python3 scripts/manage_requirement_lifecycle.py complete-migration --case-id RLC-EXAMPLE-MIGRATION --catalog-release requirement-catalog-v1 --effective-from 2026-10-09 --decision-ref docs/governance/change-requests/GCR-....md
python3 scripts/validate_requirement_lifecycle.py
```

## Review rules

- Analysis is advisory. A human decision is mandatory for every proposal.
- Decisions and activated revisions are append-only evidence.
- `change` and `supersede` create a new revision and close the prior revision.
- `extend` creates a separate requirement linked to its target.
- `duplicate` and rejected proposals remain traceable and do not create catalog entries.
- Conflict resolution, derived behavior, releases, and blocking enforcement require their applicable owners and review paths.

## Initial migration

The first six cases cover DSCB, PRA, ARCH-TPL, ARCH-EA, ARCH-SA, and ARCH-PA in that order. They contain 867 analyzed proposals. They remain `migration_in_progress`; no bulk approval or authority switch is implied.
