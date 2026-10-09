# GCR-2026-137: Post-Merge Documentation Refresh

## Purpose

Prepare a consistent, reviewable documentation update after an implementation
change is merged to `main`. The workflow proposes updates to the README,
functional catalog and technical inventory, and records formal documentation
checks for the merged change.

## Scope

- Trigger after a merged PR to `main`; skip documentation-only changes to avoid
  creating a follow-up PR loop.
- Derive the proposal from the merged PR's `Summary` bullets and changed paths.
- Run a local Markdown target check and `mkdocs build --strict`.
- Create a draft documentation PR on a separate branch and dispatch the
  repository's required validation workflows.
- Keep semantic interpretation, broader impact mapping and final approval with
  human reviewers.

## Decision boundaries

- The workflow does not write to `main` or merge a PR.
- It does not execute a semantic Document Consistency Review or infer
  requirements from code.
- A generated catalog entry is a proposal. A maintainer must map the change to
  the right functional area, document inputs, processing, outputs and limits,
  and update any affected governance, release, consumer or demo documentation.
- Build and link results are evidence of formal checks only; they do not claim
  semantic documentation completeness.

## Governance impact

- No source document, control, policy, architecture marker, schema, evidence
  contract, released baseline or consumer enforcement behavior changes.
- The workflow adds a controlled documentation-maintenance path. Its output
  remains subject to normal branch protection, independent review and merge.
- No release update or downstream consumer migration is required.

## Validation

Validate the generator and workflow, run the repository's complete validation
sequence, and confirm that a documentation-only merge is skipped while an
implementation merge produces a draft PR on a separate branch.
