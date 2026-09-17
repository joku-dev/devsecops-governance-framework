# GCR-2026-095: Repository Security im Governance Workspace

## Intent

Der Maintainer hat beauftragt, den Security-Status des zentralen Governance-
Repositories als eigenen Abschnitt in den Governance Workspace aufzunehmen.
Die Ansicht soll den vorhandenen Self-Security-Bericht verständlich darstellen,
ohne eine zweite Bewertung oder Live-Abfrage einzuführen.

## Artifact Classification

| Field | Decision |
|---|---|
| Artifact | Repository-Security-Projektion, Viewer-Navigation, Tests und Betriebsdokumentation |
| Type | frontend source, presentation projection, generated viewer, test and documentation |
| Target | `apps/governance-viewer/`, `scripts/lib/viewer_app.py`, `generated/viewer/app/`, `tests/`, `docs/` |
| Owner | Repository Owner / Governance Platform Lead |
| Source Document Intake required | no; presentation of an existing validated report |
| Evidence contract impact | none; additive internal viewer field only |
| Runtime governance impact | report-only presentation |
| Repository enforcement impact | none |
| Release impact | none |

## Design And Boundaries

Add the top-level route `#repository-security`. The build validates
`generated/reports/governance-repository-security.json` against
`schemas/governance-repository-security-report.schema.json` and projects only
the fields needed for presentation. The view shows the observation time,
profile, enforcement boundary, summary, all criteria, evidence references and
documented next steps. Missing or invalid source data cannot become a green
status; invalid input fails the build.

The Self-Security evaluator remains the single owner of the assessment. The
viewer performs no GitHub API call, does not recalculate criteria, does not
change repository settings and does not convert the report-only result into a
merge or release decision. The generated application data remains an ignored,
deterministic build artifact.

## Validation Plan

- [x] Viewer projection and invalid-report unit tests (`12` viewer tests passed)
- [x] Viewer generator and generated-source comparison
- [x] Desktop and mobile browser acceptance for `#repository-security`; technical viewer acceptance also passed
- [x] `./scripts/bootstrap_validation_env.sh`
- [x] `./scripts/validate_all.sh` (`581` tests passed)
- [x] Strict MkDocs build
- [x] Pull-request checks on GitHub: CodeQL/Analyze Python `35275789732`, Dependency Review `35275789745`, Self-Security `35275789728`, Governance CI `35275789746` and Lifecycle Guard `35275789730` passed

## Release Decision

No DevSecOps or architecture baseline release is required. The change adds a
read-only presentation of the existing governance-repository Self-Security
assessment.
