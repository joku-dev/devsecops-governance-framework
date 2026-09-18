# GCR-2026-099: Real Staging Deployment Evidence

## Change Summary

Record the first authorized ha-CPsWMS deployment on the isolated staging VM and
project its result, Trust, test outcome and L1 contribution in the Governance
Workspace.

| Field | Value |
|---|---|
| Artifact name | ha-CPsWMS staging deployment result |
| Artifact type | downstream runtime evidence, schema, intake, viewer projection and operations documentation |
| Target path | `status/staging-deployment-results/`, `schemas/`, `scripts/`, `apps/governance-viewer/`, `docs/` |
| Owner | Operations Owner / Evidence And Intake |
| Source Document Intake required? | no; this is observed runtime evidence under existing approved L1 controls |
| Evidence contract impact | additive |
| Runtime governance impact | report-only |
| Release impact | none; released baseline packages remain unchanged |

## Observed Subject

- repository: `joku-dev/ha-CPsWMS`
- deployed commit: `5d5772d989b0080ae041969315742c8fbbca6dfe`
- source evidence run: `35351493542`, attempt 1
- target: `ha-cpswms-stg-01`, environment `staging`
- result: 19 passed, 0 failed
- runtime: query-api and Neo4j healthy

The maintainer explicitly approved this staging deployment after acknowledging
the current critical and high scanner findings. The decision is limited to the
isolated staging environment. It is neither a production approval nor a general
risk acceptance.

## Control Projection

The immutable earlier measured-L1 snapshot remains unchanged. The new runtime
snapshot adds a separate later observation:

- `DSCB-L1-REQ-013`: measured for the exact staging deployment approval;
- `DSCB-L1-REQ-014`: measured for the exact locally loaded runtime image IDs;
- `DSCB-L1-REQ-016`: partial because deployed versions and events are retained,
  while durable monitoring, incident ownership, backup/restore and retention
  remain open for production use.

## Trust Boundary

The central intake verifies every file against the bundle SHA-256 manifest,
checks the receipt-internal hashes, binds the subject to the admitted mainline
measured run, validates the evidence-repository commit and applies a seven-day
freshness window. The effective level is `integrity_verified`. No independent
deployment attestation or production authority is inferred.

## Validation

```bash
./scripts/bootstrap_validation_env.sh
./scripts/validate_all.sh
.venv-docs/bin/mkdocs build --strict
```
