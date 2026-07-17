# Governance Change Request

## Summary

- Add a deterministic, schema-valid Multi-Consumer Readiness report.
- Validate registry coverage, consumer-specific storage, latest indexes,
  portfolio membership, intake concurrency, telemetry identity, and Intake
  Health dimensions.
- Make readiness part of repository validation without changing consumer or
  enforcement behavior.

## Change ID

```text
GCR-2026-040
```

## Source Document Intake

| Question | Answer |
|---|---|
| Full source-document intake required? | no |
| New or updated source document? | no |
| Reviewed non-source paths | integration registry, result indexes and paths, portfolio report, central intake workflows, telemetry, health projection, schemas, scripts, tests, status documentation |
| Register updated? | no |
| Supersedes existing source? | no |
| Possible duplicate or replacement candidate? | no; this is a derived validation report |
| Similarity assessment | `not_relevant` |

## Artifact Intake Classification

| Artifact | Type | Target | Impact |
|---|---|---|---|
| Readiness schema | internal report schema | `schemas/multi-consumer-readiness.schema.json` | additive |
| Readiness generator | deterministic validation | `scripts/generate_multi_consumer_readiness.py` | report-only |
| Readiness reports | generated projection | `generated/reports/multi-consumer-readiness.*` | recomputable |
| Repository validator integration | validation behavior | `scripts/validate_governance_repo.py` | fails inconsistent central state |
| Operations and management docs | explanatory documentation | `docs/operations/status/`, `docs/governance/` | explanatory |

Owner: Governance Platform Maintainers. Producer evidence contracts and schemas
are unchanged. Central validation impact is additive. Runtime enforcement and
release impact are none.

## Why This Change Is Needed

Separate repository directories and scoped workflows suggest multi-consumer
support, but structural readiness should be reproducible rather than inferred.
The repository needs one report that jointly verifies the registry, latest
projections, storage isolation, portfolio membership, concurrency, and
telemetry identities.

## Current Evidence

- three registered consumers
- three isolated DevSecOps latest-state projections
- two Architecture projections
- one Typed Evidence projection
- one telemetry-producing consumer after instrumentation
- nine readiness checks pass and none fail

Optional domain coverage is reported rather than treated as missing fabricated
evidence.

## Impact Analysis

| Area | Impact |
|---|---|
| Policy or directive | none |
| DevSecOps controls | none |
| Platform model | none |
| Architecture governance | architecture document records isolation validation |
| OPA policies | none |
| Schemas and evidence contracts | additive internal report schema |
| Viewer, status indexes or intake | artifact link added; index and intake semantics unchanged |
| Release package or baseline | none |
| Downstream repositories | none; validation uses existing central data only |

## Governance Behavior

- [x] Report-only readiness projection

Invariants:

- every registered consumer must have an isolated DevSecOps latest projection
- Architecture and Typed Evidence remain optional capabilities
- cross-consumer paths, unregistered projections, duplicate event IDs, and
  globally cancelling intake concurrency fail repository validation
- report failure never rewrites historical evidence
- readiness does not promote portfolio adoption state or enforcement mode
- released baseline packages remain unchanged

## Release Decision

- [x] No release required

The change validates central repository structure and does not modify a
released consumer workflow or baseline package.

## Validation Plan

- [x] targeted passing and negative isolation tests
- [x] current report generation with nine passing checks
- [x] schema validation of the generated report
- [x] `python3 scripts/validate_runtime_governance.py`
- [x] `python3 scripts/validate_governance_repo.py`
- [x] `python3 -m unittest discover -s tests`
- [x] `mkdocs build --strict`

## Reviewer Notes

Review focus: exact registry coverage, repository-path isolation, optional
domain semantics, concurrency scoping, telemetry identity, deterministic
reporting, validation failure behavior, and absence of consumer or release
mutation.
