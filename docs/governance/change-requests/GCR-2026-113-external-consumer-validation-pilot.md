# GCR 2026 113 External Consumer Validation Pilot

## Intent

Prepare a bounded external-consumer pilot and retain its first local
observations. Select cJSON/go-httpbin first, with Marked/Gson as a second wave.
Use existing integration and evidence processes without changing governance
logic or released baselines.

## Artifact intake classification

| Field | Decision |
|---|---|
| Artifacts | Pilot plan, dated preflight observation and navigation |
| Type | Onboarding/planning and diagnostic observation documentation |
| Targets | `docs/onboarding/external-consumer-validation-pilot.md`, `docs/operations/evidence/external-consumer-preflight-2026-10-04.md`, `docs/onboarding/pilot-runbook.md`, `mkdocs.yml` |
| Owner | Governance framework maintainer |
| Source Document Intake required | no; operational documents, not normative source material |
| Evidence contract impact | none; existing limits recorded |
| Runtime governance impact | none; no consumer admission or official-state mutation |
| Release impact | none |
| Validation | Existing pinned full validation, strict MkDocs build and documentation review |

## Why this change is needed

The existing portfolio and isolated capacity simulation do not establish
transferability to independent source structures or usability by another
engineer. A selected pinned portfolio gives the next stage concrete inputs,
expected outcomes and measurement boundaries.

The local preflight identifies why the older demonstration collector cannot
serve as independent measured producer evidence. The observation also records
the existing intake artifact contract before hosted setup and admission.

## Decisions

1. Start with two real external projects and add two different profiles later.
2. Preserve upstream, consumer, toolchain, template and baseline identities.
3. Keep hosted calls report-only and replace demonstration claims with facts.
4. Distinguish pipeline-only entry coverage from full L1 evaluation.
5. Use disposable governance storage for diagnostic intake/index tests; a
   `test` name is not an index exclusion mechanism.
6. Document collector limitations without changing helpers, schemas or policy.
7. Preserve existing human risk, waiver, release and lifecycle authorities.

## Impact analysis

| Area | Impact |
|---|---|
| Policy, directive, controls and architecture models | none |
| OPA, schemas and evidence contracts | none |
| Released packages or tags | none |
| Registry, accepted results, lifecycle and viewer data | none |
| Downstream repositories | proposed consumers; no hosted setup in this documentation change |
| Documentation | pilot plan, measured observation and navigation |

## Validation record

- Local collector/OPA diagnostic completed for both pinned snapshots, three
  identical semantic evaluations per snapshot.
- Separately identified synthetic two-file probe demonstrated the older
  collector's approved-default behavior; it is not consumer evidence.
- Local unchanged-source builds completed: cJSON 22/22 CTest cases; go-httpbin
  83 top-level tests passed and one optional integration test skipped, with
  race testing, vet and binary build successful. These are separate local
  preflight observations, not accepted governance evidence.
- `./scripts/bootstrap_validation_env.sh` completed with the pinned validation
  environment, including OPA 1.18.2.
- `./scripts/validate_all.sh` passed on base commit
  `701d7d0d20a461df43ae6667c3947188eb3a3bde` with these documentation changes:
  runtime/schema/traceability and evidence-agent provenance checks passed;
  all 650 tests passed.
- Strict MkDocs build passed using `requirements-docs.lock`.
- Independent documentation review found no outstanding corrections.
- No source-lineage or generated-status changes are included.

## Release decision

No release is required. These records define proposed pilot execution and
retain local observations. They do not authorize blocking, production use or
additional lifecycle scope.

## Reviewer focus

Verify completed actions against observations; distinguish source selection,
local execution, hosted CI and accepted evidence. Confirm proposed consumer
names when hosted setup occurs. Resolve limitations through scoped changes
when needed, without replacing unknown facts with positive defaults.
