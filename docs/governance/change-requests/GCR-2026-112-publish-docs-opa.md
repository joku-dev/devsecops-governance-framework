# GCR-2026-112: Install Pinned OPA For Viewer Publication

## Intent

The post-merge Pages publication failed while regenerating the Governance
Viewer. Its read-only lifecycle projection replays accepted evidence using OPA,
but the `Publish Docs` workflow had not installed the repository's pinned OPA
runtime. The publication job therefore stopped before building or deploying the
Pages artifact.

## Artifact Classification

| Field | Decision |
|---|---|
| Artifact | Pages publishing workflow dependency and viewer-source path filters |
| Type | CI workflow configuration and governance change request |
| Target | `.github/workflows/publish-docs.yml`, `docs/governance/change-requests/` |
| Owner | Repository Owner / Governance Platform Lead |
| Source Document Intake required | no; reproduce the existing validation toolchain in the publisher |
| Evidence contract impact | none |
| Runtime governance impact | none; the projection remains read-only |
| Repository enforcement impact | none |
| Release impact | none |

## Change

Install OPA 1.18.2 with the same pinned setup action used by Governance CI
before viewer generation. Include the viewer experience and consumer lifecycle
projection modules in the `Publish Docs` path filter so future changes to
either generator input trigger a publication run.

This change only supplies a missing publisher dependency and closes the trigger
gap. It does not change OPA policy, evidence acceptance, lifecycle eligibility,
Pages permissions or any released baseline.

## Validation

- [x] `./scripts/validate_all.sh` (642 tests passed)
- [x] `mkdocs build --strict`
- [x] Generate the status viewer with OPA 1.18.2 available
- [ ] Pull-request CI and post-merge Pages deployment

## Release Decision

No baseline release or downstream migration is required.
