# GCR-2026-087: Evaluate measured L1 evidence in Governance Workspace

## Intent and classification

The maintainer authorizes implementation of a separate report-only evaluation
of real ha-CPsWMS tests, scans and platform evidence against the existing 16 L1
control references, with per-control explanations in the new viewer.

| Field | Decision |
|---|---|
| Artifact types | Additive evidence contract, assessment adapter, downstream snapshots, frontend and documentation |
| Target | schemas/, scripts/lib/, status/measured-l1-results/, apps/governance-viewer/, docs/operations/evidence/ |
| Owner | Repository maintainer |
| Source Document Intake | Not required: existing approved L1 controls and runtime evidence; no new normative source |
| Evidence impact | New optional measured-l1-assessment contract, independently verified selected raw files |
| Governance impact | Report-only assessment of evidence coverage; no compliance PASS or approval inferred |
| Release impact | No baseline release; released packages, policies and consumer pins remain unchanged |
| Validation | Pinned complete validation, schema and adversarial intake tests, strict docs, desktop/mobile browser acceptance |

## Boundaries

Use producer run/attempt/commit metadata, manifest-bound raw reports and image
identities. Recompute coverage centrally; a producer's optimistic status cannot
promote absent approvals, inaccessible protection settings or deployment gaps.
Retain explicit scope limitations and raw-file hashes, not credentials or signed
artifact download URLs. Complete archive hashes and independent attestation are
not claimed. Historical snapshots are append-only. Official baseline, Trust and
Replay remain separate and unchanged; historical Replay failures are not cleared
by this additive report. No timestamp or random salt is added to evade replay.

The consumer already supplies run-bound evidence. No new application run or VM is
needed for this initial assessment. CLI intake and reviewed publication are
repeatable. Automatic intake remains a separate operating capability.

The standing maintainer exception applies to technical review/merge, not personal
release approval or risk acceptance. Preserve the accepted lifecycle manifest and
restore normal review requirements after merge.
