# Governance Change Request: Evidence Trust Model v1

## Summary

- Add a machine-readable Evidence Trust Model with explicit dimensions,
  verification checks, monotone trust levels, decision rules, migration gaps,
  phases, and open decisions.
- Add a schema and repository validation for the internal model.
- Document the current DevSecOps and architecture trust gaps without changing
  existing snapshots, intake behavior, viewer state, or enforcement.

## Change ID

```text
GCR-2026-026
```

## Artifact Intake Classification

| Field | Value |
|---|---|
| Artifact name | Evidence Trust Model v1 |
| Artifact type | evidence contract model and documentation |
| Target path | `model/evidence/evidence-trust-model.yaml` |
| Owner | governance maintainers |
| Source Document Intake required? | no |
| Evidence contract impact | additive internal model; no downstream schema change |
| Runtime governance impact | report-only |
| Release impact | none |
| Validation required | Model schema, lineage, runtime validation, repo validation, unit tests, MkDocs strict build |

## Source Document Intake

| Question | Answer |
|---|---|
| Full source-document intake required? | no |
| New or updated source document? | no |
| Source document path | `docs/governance/source-documents/DSCB-STD-SRC-001.public.md` |
| Reviewed non-source paths | model, schema, evidence operations documentation, tests |
| Register updated? | no; `model/evidence` is already a DSCB derived-artifact area |
| Supersedes existing source? | no |
| Possible duplicate or replacement candidate? | no |
| Similarity assessment | complements the evidence type catalog; does not replace it |
| Source status | existing registered intake source |

## Why This Change Is Needed

The repository records governance outcomes, run identity, commits, baselines,
artifact metadata, and selected hashes. It does not yet distinguish evidence
presence from verified integrity, provenance, authenticity, freshness, replay
resistance, or chain of custody.

Without an explicit model, a green governance result can be mistaken for
trusted evidence even when verification was not performed. The model separates
those decisions and provides a controlled migration path.

## Impact Analysis

| Area | Impact |
|---|---|
| Policy or directive | None |
| DevSecOps controls | No control text or enforcement change |
| Evidence model | Additive trust vocabulary and migration plan |
| Architecture governance | Gap documented; no gate or collector change |
| OPA policies | None |
| Schemas | New internal model schema only |
| Viewer, indexes or intake | Current behavior unchanged |
| Release package or baseline | None |
| Downstream repositories | None in Phase 1 |

## Derived Artifacts

- `model/evidence/evidence-trust-model.yaml`
- `schemas/evidence-trust-model.schema.json`
- `docs/operations/evidence/evidence-trust-model.md`
- `tests/test_evidence_trust_model.py`
- `scripts/validate_governance_repo.py`
- `scripts/generate_source_lineage_report.py`
- generated source-lineage and governance-impact reports
- documentation navigation and entrypoints

## Governance Behavior

Choose one:

- [ ] Documentation-only
- [x] Report-only governance behavior
- [ ] Blocking governance behavior
- [ ] Release packaging only

Notes:

- Existing evidence defaults to `unverified` only as a model interpretation;
  stored snapshots are not rewritten and current latest-result logic is not
  changed.
- Trust-based blocking is explicitly deferred to a later release decision.

## Release Decision

Choose one:

- [x] No release required
- [ ] Release candidate required
- [ ] Patch baseline release required
- [ ] Minor baseline release required
- [ ] Major baseline release required

Release notes:

- Phase 1 adds an internal report-only model and does not change downstream
  schemas, workflows, evidence fields, or enforcement.

## Open Decisions

- trusted issuer and trust-root registry
- evidence-type freshness windows
- initial attestation format and predicate
- future trust requirements for protected mainline and release decisions

Required reviewers for later phases:

- Governance
- Security
- Platform
- Architecture
- Operations and control owners for freshness policy
- Release Manager before contract or enforcement changes

## Validation Plan

- [x] `./scripts/validate_all.sh`
- [x] `mkdocs build --strict`
- [x] Evidence Trust Model schema validation
- [x] Trust-level monotonicity and reference tests
- [x] Source lineage regenerated with no missing artifacts
- [x] Viewer regeneration not required; no viewer behavior changed
- [x] Downstream intake not required; no consumer contract changed

## Reviewer Notes

- Confirm that trust remains independent from governance outcome.
- Confirm that current DevSecOps and architecture gaps are represented fairly.
- Confirm that Phase 2 remains additive and report-only.
- Do not approve trust-based blocking through this change request.
