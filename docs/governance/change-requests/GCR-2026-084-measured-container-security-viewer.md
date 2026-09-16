# GCR-2026-084: Measured container security in the viewer

## Intent

The maintainer requested actual scan findings in the central viewer: severities,
affected images, before/after comparison, technical assessment and evidence links.

## Artifact classification

| Field | Decision |
|---|---|
| Artifact type | Evidence contract, collector, append-only downstream snapshots, generated viewer and operational docs |
| Target | schemas/, scripts/, status/measured-security-results/, generated/viewer/, docs/operations/evidence/ |
| Owner | Repository maintainer |
| Source Document Intake | Not required; operational evidence, no normative source |
| Evidence contract impact | Additive measured-container-security snapshot, scoped to the ha-CPsWMS pilot |
| Runtime governance impact | Report-only display, no new required gate or lifecycle admission |
| Release impact | No baseline release or released-package/tag changes |
| Validation | Negative intake/schema tests, HTML safety/selection tests, full pinned validation, strict MkDocs and browser check |

## Semantics and safeguards

Admit only completed successful push/main runs of the measured-evidence workflow.
Capture initial runs 35128325507 (13 critical/373 high records) and 35131185085
(1 critical/332 high records). Verify selected artifact member bytes against
producer manifests and bind the scan image to the run's coverage report. Do not
claim whole-archive digest verification, independent attestation, vulnerability
absence, deployment approval or risk acceptance. Raw high/critical findings stay
visible; low/medium findings remain aggregate counts. Main snapshots remain
separate from official compliance results, typed Evidence Trust and accepted
lifecycle observations. Manual refresh is explicit in both UI and runbook.

Technical review exception is authorized by the maintainer in this session.
Validate, commit, push and merge under that scope; restore ordinary branch
protection after the merge. This does not manufacture independent human review.
