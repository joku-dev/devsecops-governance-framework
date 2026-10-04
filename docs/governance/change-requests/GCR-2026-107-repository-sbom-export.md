# GCR-2026-107: Commit-Bound Repository SBOM Export

## Intent

Add a scheduled, report-only export of the repository dependency graph as an
SPDX SBOM. Bind each retained artifact to the default-branch commit verified
before and after generation. This change does not add a required check or
change vulnerability enforcement.

## Artifact Intake Classification

| Field | Decision |
|---|---|
| Artifact | SBOM export workflow, exporter, tests, and operations guidance |
| Type | Workflow, implementation, tests, and security documentation |
| Target | `.github/workflows/repository-sbom.yml`, `scripts/export_repository_sbom.py`, `tests/test_repository_sbom.py`, `docs/operations/security/repository-sbom-and-vulnerability-management.md` |
| Owner | Repository Owner / Governance Platform Lead |
| Source Document Intake required | no; no new governance source is introduced |
| Evidence contract impact | none; this is repository-level inventory, not downstream compliance evidence |
| Runtime governance impact | none; workflow is observational |
| Repository enforcement impact | none; no required merge check or blocking behavior is added |
| Release impact | none; released baselines and tags remain unchanged |
| Validation required | workflow and exporter review, targeted unit tests, repository validators, strict documentation build |

## Design

- Request GitHub's asynchronous repository SBOM export using the read-only
  workflow token.
- Confirm the workflow commit is the current default-branch head before and
  after generation, because the API exports the current repository dependency
  graph.
- Validate the SPDX document, repository identity, and package inventory before
  writing the SBOM and commit metadata.
- Pin the assurance regression fixture that shares the typed-evidence run so CI
  does not select a different measurement based on filesystem glob order.
- Upload both files as a 90-day Actions artifact named for the commit SHA.
- Keep vulnerability handling within the repository's current report-only
  posture.

## Decision Boundary

- [x] Documentation and observational workflow only
- [x] No evidence contract or baseline release change
- [ ] Add a required merge check
- [ ] Introduce blocking vulnerability enforcement

## Validation Plan

- [x] `git diff --check`
- [x] `python3 -m unittest tests.test_repository_sbom` (8 tests passed)
- [x] `python3 scripts/validate_runtime_governance.py`
- [x] `python3 scripts/validate_governance_repo.py`
- [x] `python3 -m unittest discover -s tests` (631 tests passed in hosted PR validation)
- [x] `.venv-docs/bin/mkdocs build --strict`

The hosted PR validation ran 631 regression tests successfully after the
assurance test was pinned to its matching measured run. A separate full test
run in the local prototype worktree reported two unrelated environment or
worktree errors: a signed temporary commit could not be created, and one test
expected the locally deleted counsel ZIP. The SBOM tests passed independently.
A live run of the new SBOM workflow is still needed to verify API access and
artifact publication.

## Review Focus

- Confirm GitHub Actions token access is limited to repository contents read.
- Confirm generated SBOM and metadata are commit-bound and not represented as
  downstream compliance evidence.
- Confirm generated artifact retention and schedule match operational needs.
