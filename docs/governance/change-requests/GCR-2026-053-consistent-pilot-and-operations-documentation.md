# Governance Change Request

## Change ID

`GCR-2026-053`

## Request And Classification

On 9 September 2026 the maintainer requested consistent documentation:
"bitte erzeuge mir eine widerspruchsfreie Dokmentation."

| Field | Value |
|---|---|
| Artifact | Current onboarding and operations guides, navigation, mutable adoption template and regression coverage |
| Type | Practical operating guides, recovery process and consumer onboarding example correction |
| Owner | Governance Platform Lead; access and protections Repository Owner |
| Source Document Intake required | no; no new normative source or candidate derivation |
| Evidence contracts, schemas, policies, viewer behavior | unchanged |
| Release classification | no baseline release; frozen packages, tags and wrapper contracts unchanged |
| Consumer migration | New copies explicitly select report-only; existing consumers require their own reviewed configuration change |

## Reconciliation

The current adoption template and copyable onboarding examples explicitly select
report-only for PR, main push and manual runs. This fixes the conflict with the
pilot runbook while retaining the released DevSecOps wrapper's default blocking
contract. Historical release-tag copies do not acquire this template correction;
record the current reviewed template revision separately from the baseline pin.
No existing consumer or registered legacy enforcement mode is changed.

Current instructions use protected-main PR publication and the active single
Pages workflow. The central handbook connects daily triage, pilot acceptance,
credential maintenance and backup/recovery. Status pages distinguish implemented
capabilities from pending operational setup and dated demonstration evidence.
Readiness and accountable approval remain necessary before new blocking.

The new practical guides/process are classified under the new-artifact intake
process. They document existing controls and proposed pilot procedures, not a
claim that named staffing, off-site backups, credential inventory or recovery
objectives have already been commissioned. Historical records remain intact.

## Validation And Publication

Run pinned bootstrap/full validation and a strict MkDocs build. Regression
coverage checks that the mutable adoption template explicitly selects report-only
while preserving tests of the released blocking default. Review current examples,
relative links and live protection settings, and rehearse Git recovery in an
isolated local destination. Record the scope of that drill without claiming a
production disaster-recovery exercise.

Publish through a normal reviewed PR with required checks. This request does not
extend PR #61's one-off review exception or authorize changes to main protection.
