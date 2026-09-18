# GCR-2026-100: L1 Evidence Closure Packages 1–4

## Change Summary

Close four measured-evidence gaps for the ha-CPsWMS pilot: main-branch rules,
staging consolidation, source-code findings and reproducible Python dependencies.

| Field | Value |
|---|---|
| Artifact name | ha-CPsWMS measured L1 profile v2 and consolidated L1 assessment |
| Artifact type | consumer CI, evidence contract, intake, derived assessment, viewer and documentation |
| Target path | ha-CPsWMS workflow/code/locks; `scripts/`, `schemas/`, `status/`, viewer and evidence docs |
| Owner | Platform Owner / Evidence And Intake / Security Engineering |
| Source Document Intake required? | no; implementation and evidence strengthening under existing approved controls |
| Evidence contract impact | additive profile version and new derived result type |
| Runtime governance impact | report-only |
| Release impact | none; `l1-baseline-v1.1.3` remains unchanged |

## Implemented Scope

1. An active main ruleset is captured and centrally checked for pull-request
   enforcement, five required checks, force-push/deletion protection and an
   empty bypass list.
2. A staging result supplements controls 013, 014 and 016 only when repository,
   baseline, commit, producer run and attempt exactly match a measured L1 result.
   The combined snapshot is append-only and source-bound.
3. Bandit and Ruff findings in the consumer are resolved. Zero findings are
   reported as a completed technical measurement while secure-design review
   remains a development-process responsibility.
4. Service, application and CI/tool dependencies are locked for Python 3.12
   with SHA-256 hashes. CI and Docker install with `--require-hashes`.
   Application and CI/tool CycloneDX SBOMs plus `pip-audit` output become sealed
   raw evidence and are independently checked by central intake.

## Decision Boundary

All results remain report-only. The consolidated result does not rewrite its
measured or staging sources, replace the released baseline, authorize production
or accept vulnerability risk. A staging result for a different commit or run is
kept visible in the Staging history but cannot improve the current L1 assessment.

## Validation

```bash
./scripts/bootstrap_validation_env.sh
./scripts/validate_all.sh
```
