# Governance Change Request

## Summary

- Add one current-state system architecture for the implemented
  Governance-as-Code platform.
- Connect governance intent, models, releases, consumer execution, evidence
  Trust, append-only intake, portfolio projections, graph, and viewer.
- Make the document available from the official, MkDocs, and AI entrypoints.

## Change ID

```text
GCR-2026-035
```

## Source Document Intake

| Question | Answer |
|---|---|
| Full source-document intake required? | no |
| New or updated source document? | no |
| Reviewed non-source paths | repository implementation, foundation, governance architecture, evidence operations, status operations |
| Register updated? | no |
| Supersedes existing source? | no |
| Possible duplicate or replacement candidate? | no; existing documents are partial views and remain authoritative in their scope |
| Similarity assessment | `not_relevant` |

## Artifact Intake Classification

| Artifact | Type | Target | Impact |
|---|---|---|---|
| Governance-as-Code System Architecture | non-normative governance architecture explanation | `docs/governance/architecture/` | documentation-only |
| Documentation navigation | entrypoint metadata | `mkdocs.yml`, `docs/official-entrypoints.md`, `docs/ai-index.md`, `docs/index.md` | discoverability only |

Owner: Governance Platform Maintainers. Evidence-contract impact is none.
Runtime impact is none. Release impact is none.

## Why This Change Is Needed

The repository has a target reference architecture, operating-model
architecture, runtime addendum, status description, and detailed component
guides. It does not have one as-built architecture that explains their current
technical relationships and deployment boundaries. This makes the complete
system harder to review, present, and evolve safely.

## Impact Analysis

| Area | Impact |
|---|---|
| Policy or directive | none |
| DevSecOps controls | none |
| Platform model | none |
| Architecture governance | explanatory documentation only |
| OPA policies | none |
| Schemas and evidence contracts | none |
| Viewer, status indexes or intake | none |
| Release package or baseline | none |
| Downstream repositories | none |

## Derived Artifacts

- none
- source-document lineage is confirmed unchanged

## Governance Behavior

- [x] No governance behavior change

Invariants:

- existing normative documents and machine-readable models retain authority
- released baseline packages remain unchanged
- report-only and blocking semantics remain unchanged
- generated projections remain read-only views

## Release Decision

- [x] No release required

No downstream contract, model, workflow, schema, policy, or baseline changes.

## Validation Plan

- [x] `python3 scripts/validate_runtime_governance.py`
- [x] `python3 scripts/validate_governance_repo.py`
- [x] `python3 -m unittest discover -s tests`
- [x] `mkdocs build --strict`
- [x] navigation links reviewed

## Reviewer Notes

Review focus: fidelity to the implemented architecture, clear separation of
authoritative sources from projections, accurate Evidence Trust boundaries,
multi-consumer and concurrency semantics, explicit current deployment, and no
accidental normative or release impact.
