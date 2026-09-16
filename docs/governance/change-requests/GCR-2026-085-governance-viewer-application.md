# GCR-2026-085: Separate read-only governance viewer application

## Intent

The maintainer approved an independent viewer frontend in this repository,
starting with the overview and ha-CPsWMS repository detail. Reduce navigation
complexity and make actual findings and source context easy to inspect.

## Artifact classification

| Field | Decision |
|---|---|
| Artifact type | Frontend source, presentation generator, generated viewer, tests and operational documentation |
| Target | apps/governance-viewer/, scripts/lib/viewer_app.py, generated/viewer/app/, tests/, docs/operations/guides/ |
| Owner | Repository maintainer |
| Source Document Intake | Not required; presentation of existing evidence, no normative source |
| Evidence contract impact | None; versioned internal presentation format only |
| Runtime governance impact | Read-only, no policy, enforcement or lifecycle changes |
| Release impact | No baseline release, package or tag changes |
| Validation | Official-selection and missing-evidence tests, pinned repository validation, strict MkDocs, desktop/mobile browser acceptance |

## Design and boundaries

Provide four top-level views: overview, repositories, findings and evidence.
Reuse official `latest_result` from the two governance indexes and validated
measured-security snapshots. Keep governance status, scan severity, evidence
quality, source times and commits separate. Missing data and load errors cannot
be promoted to PASS or zero findings. Preserve the old technical viewer and
its deep links. The application data file is an ignored, deterministic build
artifact regenerated for Pages from versioned evidence. The operational intake
allowlist and its personally accepted implementation remain unchanged; application
source changes require the ordinary code PR.

Use local HTML/CSS/JavaScript with no third-party browser assets, a restrictive
Content Security Policy, encoded text, safe constructed source URLs, hash routes,
keyboard navigation, responsive tables, pagination and explicit empty/error states.
The existing Pages build generates and deploys both views. No backend, secrets,
new external service or formal risk acceptance is introduced.

The maintainer's standing technical review exception applies to this PR. Run all
checks before merging and restore the required review count afterward. This is
not an independent human approval or a deployment/risk/lifecycle decision.
