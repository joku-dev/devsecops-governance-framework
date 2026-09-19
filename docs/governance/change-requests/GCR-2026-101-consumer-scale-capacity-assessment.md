# GCR-2026-101: Consumer Scale Capacity Assessment

## Intent

Record a reproducible capacity assessment for 300 and 1,500 consumer
repositories and define the target operating architecture without changing
governance policy, released baselines, result contracts or enforcement.

## Artifact Classification

| Field | Decision |
|---|---|
| Artifact | Consumer scale simulation, capacity assessment and navigation updates |
| Type | Planning documentation, diagnostic script and tests |
| Target | `docs/operations/planning/`, `scripts/simulate_consumer_scale.py`, `tests/` and documentation indexes |
| Owner | Governance Platform Lead |
| Source Document Intake required | no; the assessment observes the implemented repository |
| Evidence contract impact | none |
| Runtime governance impact | none; isolated diagnostic only |
| Release impact | none |

## Decisions

1. Consumer capacity is assessed across evaluation, intake, storage,
   publication and viewer delivery rather than by repository count alone.
2. The simulation uses current accepted result shapes and temporary storage. It
   must not add synthetic consumers to official status indexes.
3. The present per-result workflow and PR model is not declared production-ready
   for 300 or 1,500 consumers.
4. The target architecture retains one logical control plane and scales the
   evidence plane through queueing, batching, immutable external storage,
   partitioned viewer data and intake shards.
5. Separate complete governance instances require an isolation reason and a
   federation contract that prevents silent baseline drift.

## Impact Analysis

| Area | Impact |
|---|---|
| Policy or directive | none |
| DevSecOps controls | none |
| Architecture governance | target operating architecture documented; no marker or gate change |
| OPA policies | none |
| Schemas and evidence contracts | none |
| Viewer, status indexes or intake | limitations and future refactoring documented; current behavior unchanged |
| Release package or baseline | none |
| Downstream repositories | no workflow or enforcement change |

## Validation Plan

- [x] scale simulation for 300 and 1,500 consumers completes without official-state changes
- [x] focused scale-simulation unit tests pass
- [x] `./scripts/bootstrap_validation_env.sh`
- [x] `./scripts/validate_all.sh` (`617` tests passed)
- [x] `.venv-docs/bin/mkdocs build --strict`
- [x] repository hygiene and documentation links reviewed

## Release Decision

No baseline release is required. The change adds diagnostic and planning
material only.
