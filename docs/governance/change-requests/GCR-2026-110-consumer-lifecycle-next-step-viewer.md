# GCR-2026-110: Consumer Lifecycle Next-Step Guidance in the Governance Workspace

## Intent

The maintainer asked to reduce operational friction in the completed consumer
closed loop. The current official Consumer Lifecycle index shows the finding
state and aggregate counts, while accepted observations and personal actions
remain in separate immutable ledgers. Operators therefore have to inspect
several records and the operating guide to determine the next permitted step.

## Artifact Classification

| Field | Decision |
|---|---|
| Artifact | Read-only Consumer Lifecycle next-step projection and Workspace view |
| Type | Viewer behavior, presentation projection, tests, and documentation |
| Target | `scripts/lib/consumer_lifecycle_next_step.py`, `scripts/lib/viewer_app.py`, `apps/governance-viewer/app.js`, `tests/`, `docs/` |
| Owner | Repository Owner / Governance Platform Lead |
| Source Document Intake required | no; display of the existing versioned lifecycle index and validated ledgers |
| Evidence contract impact | none; additive internal viewer data only |
| Runtime governance impact | report-only guidance; it does not change lifecycle eligibility |
| Repository enforcement impact | none |
| Release impact | none |

## Design And Boundaries

Add **Operations → Lifecycle Next Step** to the read-only Governance Workspace.
The build checks that the published `status/governance-consumer-lifecycle.json`
matches the projection recomputed from accepted consumer receipts and actions.
The presentation derives one recommendation from the current finding,
operating acceptance, role state, quarantine count, active decision, progress,
closure and receipt order. It links directly to the relevant consumer run,
central transaction record, consent discussion PR, operating guide and
workflow.

The recommendation never authorizes or executes an action. Existing intake
continues to enforce personal consent, named roles, evidence provenance,
revision binding, ordering and freshness. A closed finding is presented as
having no pending action; the report-only pilot does not claim continuous
monitoring. A new eligible failure can reopen the case under the existing
contract.

This is additive presentation code outside both the GRS-002 and Consumer
Lifecycle operating-acceptance implementation manifests. It does not change
either accepted implementation, status index, evidence ledger, schema, policy,
baseline, workflow permission, or enforcement mode.

## Validation Plan

- [x] Unit coverage for closed/no-action, open decision, completed-without-new-PASS, and quarantined-evidence states
- [x] Viewer generation validates the index against its accepted ledger projection
- [x] `./scripts/validate_all.sh` (639 tests passed)
- [x] Strict MkDocs build and focused lifecycle browser smoke, including a mobile viewport
- [ ] Pull-request CI on the current mainline base

The broader pre-existing `tests/browser/check_viewer_app.py` currently stops
before the lifecycle route at outdated fixed overview metrics. The focused
browser smoke exercised the new route, its evidence and consent links, and
mobile overflow directly.

## Release Decision

No DevSecOps or architecture baseline release is required. This change adds a
read-only pointer to the next governed operation and its source evidence.
