# Governance Change Request

## Summary

- Make append-only result intake compatible with legacy evidence identities
  that lack only `artifact_digest`.
- Preserve strict conflict quarantine when both identities contain different
  artifact digests.
- Record the three-path intake telemetry smoke-test evidence.

## Change ID

```text
GCR-2026-037
```

## Source Document Intake

| Question | Answer |
|---|---|
| Full source-document intake required? | no |
| New or updated source document? | no |
| Reviewed non-source paths | result ledger, intake tests, evidence operations, architecture and management documentation |
| Register updated? | no |
| Supersedes existing source? | no |
| Possible duplicate or replacement candidate? | no; this closes an implementation compatibility gap |
| Similarity assessment | `not_relevant` |

## Artifact Intake Classification

| Artifact | Type | Target | Impact |
|---|---|---|---|
| Identity compatibility rule | runtime implementation | `scripts/lib/result_ledger.py` | idempotent legacy enrichment |
| Regression tests | validation evidence | `tests/test_result_ledger.py` | additive |
| Smoke-test record | operations documentation | `docs/operations/evidence/` | explanatory |
| Architecture and management updates | governance documentation | `docs/governance/` | explanatory |

Owner: Governance Platform Maintainers. Evidence-contract and schema impact are
none. Runtime impact is limited to append-only identity matching and remains
report-only. Release impact is none.

## Why This Change Is Needed

The first telemetry smoke test re-intook a valid historical DevSecOps result.
The stored identity predated artifact-digest capture, while the new verifier
added `artifact_digest`. Core run context and subject digests were identical,
but exact dictionary equality quarantined the enrichment as a conflict.

The existing replay assessment already recognizes that legacy enrichment as
compatible. Append-only storage must apply the same boundary without modifying
the historical snapshot or accepting genuinely different evidence.

## Impact Analysis

| Area | Impact |
|---|---|
| Policy or directive | none |
| DevSecOps controls | none |
| Platform model | none |
| Architecture governance | documents the ledger compatibility boundary |
| OPA policies | none |
| Schemas and evidence contracts | none |
| Viewer, status indexes or intake | legacy re-intake is idempotent; existing conflict history is preserved |
| Release package or baseline | none |
| Downstream repositories | none |

## Governance Behavior

- [x] Report-only operational behavior

Invariants:

- core replay context and all subject digests must match
- a missing artifact digest on the older stored identity may be enriched by
  the incoming identity, but an incoming identity may not remove it
- equal present artifact digests remain idempotent
- different present artifact digests remain a quarantined conflict
- the original snapshot is never rewritten
- the existing smoke-test conflict record is never deleted
- governance outcomes, Evidence Trust, latest-state selection, policies, and
  released baselines remain unchanged

## Release Decision

- [x] No release required

The change hardens central runtime intake and does not modify a released
consumer workflow or baseline package.

## Validation Plan

- [x] targeted legacy-enrichment idempotency test
- [x] targeted different-present-digest conflict test
- [x] `python3 scripts/validate_runtime_governance.py`
- [x] `python3 scripts/validate_governance_repo.py`
- [x] `python3 -m unittest discover -s tests`
- [x] `mkdocs build --strict`

## Reviewer Notes

Review focus: exact core-context and subject matching, asymmetric legacy
compatibility, unchanged strict behavior for two different present artifact
digests, immutable conflict history, and absence of schema, release, or
blocking impact.
