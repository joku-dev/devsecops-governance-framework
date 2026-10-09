# GCR-2026-144: Implemented requirements first

## Decision

Introduce the first migration wave from approved source documents into canonical Git requirements. The wave starts with requirements for which an active normative or executable artifact can be identified. Generated reports are review evidence and do not count as implementation.

## Scope

- allow explicit partial activation of lifecycle proposals;
- maintain a versioned many-to-many requirement-to-artifact register;
- inventory controls, platform models, architecture rules, OPA policies, schemas, workflows, and releases;
- generate deterministic mapping suggestions for all 867 source requirements;
- require a separate human requirement decision and artifact equivalence decision;
- enforce exact active `GRQ-*` revisions, authorized artifact types, and artifact hashes;
- show migrated, partially migrated, and open scope in the status viewer.

DSCB and PRA receive direct lineage-based candidate matching. Architecture artifacts retain their existing `ARCH-SDD` lineage; suggestions for ARCH-TPL, ARCH-EA, ARCH-SA, and ARCH-PA are explicitly marked as requiring lineage confirmation.

## Safety constraints

- The initial register contains no effective adoption decisions.
- OPA logic and current enforcement modes do not change.
- Existing released baseline packages are not modified.
- Approved source documents remain authoritative while their ledger state is `migration_in_progress`.
- A source may become `git_authoritative` only after complete migration coverage.

## Acceptance

Each adopted implementation must resolve from an exact effective `GRQ-*` revision to an artifact path and hash, with an approved equivalence decision and a valid decision reference. Candidate count is not treated as migrated count.
