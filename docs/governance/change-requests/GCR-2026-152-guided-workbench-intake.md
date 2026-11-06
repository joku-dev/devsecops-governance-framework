# GCR-2026-152 — Guided Workbench document preparation

## Intent and authority

On 6 November 2026 the maintainer requested a more usable Workbench, prioritizing
clear steps and language, and fewer up-front document-intake inputs.

## Artifact intake classification

- Type: local Workbench presentation and interaction, regression tests, operations documentation.
- Paths: `scripts/workbench/`, `tests/`, `docs/operations/guides/` and this change record.
- Owner: repository maintainer / source-intake reviewers.
- Full Source Document Intake: not required; source documents and register are unchanged.
- Evidence contracts, OPA enforcement, released baselines and acceptance fingerprints: unchanged.

## Resulting behavior

Start with a task or continue a local draft. Prepare a document through three
steps: choose the file, classify the document, then confirm the metadata.
The filename can suggest a title and explicit version; a free document ID is
suggested separately from requirement IDs. All suggestions remain editable.
Missing fields are explained beside the form. Back navigation preserves the
chosen file and entered metadata in memory; logout clears this state.

Only the final preparation action submits the file to the existing local API.
After preparation, direct next-step buttons lead to comparisons, notes and
review-package download. Technical process and package details remain available
in expandable sections. Required publication confirmation remains in place.

The backend, explicit-only requirement extraction, candidate status,
proposal-only notes, hash binding, human decisions and publication boundary
keep their existing semantics. No browser storage, new provider call or new
repository mutation capability is introduced.

## Validation

Run pinned bootstrap and complete validation. Exercise ID uniqueness, editable
metadata, required fields, format/size limits, version-replacement selection,
HTML escaping and the guided flow with synthetic data. Record the observed
browser result and any local tool limitations before commit.

Observed validation: pinned bootstrap and `validate_all.sh` passed all 803
tests, including Node-CLI and HTTP tests. `node --check` and the dedicated
client-logic regressions passed. A synthetic jsdom flow additionally checked
back/section navigation, editable metadata, final-only upload, next actions
and logout reset; an isolated real HTTP run verified candidate creation,
explicit-only extraction and byte-identical ZIP content. Safari login, start
and first-step validation were observed; native file-picker automation was
unreliable, so no complete native-browser acceptance is claimed.

During PR integration, Requirement Lifecycle CI detected an outdated advisory
artifact inventory. Regenerate `implemented-requirement-migration.json` and
`.md` with the existing generator against the current integration branch.
This refresh records current artifact paths and hashes; it preserves historical
requirement cases, mappings and decisions. The catalog and PRA review packet
remain reproducible without changes.

## Release decision

No baseline release or enforcement change.
