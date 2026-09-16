# GCR-2026-083: Measured L1 consumer evidence

## Intent

The maintainer requested actual tests and tools for the L1 baseline. Implement
consumer evidence collection against all 16 existing L1 requirements, identify
which parts are measured, and keep missing authorization/operational evidence
visible. Consumer implementation: `joku-dev/ha-CPsWMS` PR #16.

## Artifact classification

| Field | Decision |
|---|---|
| Artifact type | Consumer tests/workflow/evidence and central operational documentation |
| Target | Consumer `quality_tests/`, `scripts/l1/`, `quality/`, workflow; central `docs/operations/evidence/` |
| Owner | Repository maintainer |
| Source Document Intake | Not required; no new normative source or control derivation |
| Evidence contract impact | Separate additive consumer coverage report; no promotion under existing compliance schema |
| Runtime governance impact | New report-only evidence coverage, no new required check or production deployment |
| Release impact | No baseline release; protect existing packages and tags |
| Validation | Consumer unit/negative/runtime tests and actual image scans; central pinned full validation and strict MkDocs |

## Scope and boundary

Actual source tests, Bandit/Ruff reports, five runtime-image SBOMs and CVE scans,
artifact digests, a seeded real Neo4j/query API integration with outage/recovery,
and direct GitHub metadata reads. The report maps all 16 requirements without
turning API failures, missing records or author declarations into positive facts.
Technical requirement/test links do not assert complete approved system coverage.
No deployment authorization, risk acceptance, production security-event record or
independent review is manufactured. Existing blocking and accepted lifecycle
contracts remain unchanged. The separate demo-consumer progress request is not
captured or invalidated by this work.

## Publication

Follow the standing maintainer authorization to validate, commit, push and merge
with the scoped technical review exception. Preserve ordinary protection settings.
Publish consumer evidence results separately from the historical official L1
result. Technical checks do not grant human deployment or finding acceptance.
