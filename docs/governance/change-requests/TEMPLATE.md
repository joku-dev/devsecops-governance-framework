# Governance Change Request

## Summary

Provide 2-5 bullets describing the proposed governance change.

- 

## Change ID

```text
GCR-YYYY-NNN
```

## Source Document Intake

If the change adds, moves or starts consuming a new artifact, classify it first
with `docs/operations/processes/new-artifact-intake-process.md`.

Use full Source Document Intake only when this change adds or updates a file
under `docs/governance/source-documents/` or changes the source document
register. For all other changes, answer `no`, record the reviewed non-source
path if useful, and skip Replacement Review.

## Artifact Intake Classification

Use this section when a new artifact is added, moved or consumed.

| Field | Value |
|---|---|
| Artifact name |  |
| Artifact type | source/evidence/example/schema/policy/model/workflow/documentation/generated/release |
| Target path |  |
| Owner |  |
| Source Document Intake required? | yes/no |
| Evidence contract impact | none/additive/breaking |
| Runtime governance impact | none/report-only/blocking |
| Release impact | none/patch/minor/major |
| Validation required |  |

| Question | Answer |
|---|---|
| Full source-document intake required? | yes/no |
| New or updated source document? |  |
| Source document path | `docs/governance/source-documents/...` |
| Reviewed non-source path | `docs/...` or not applicable |
| Register updated? | yes/no |
| Supersedes existing source? | yes/no, source ID |
| Possible duplicate or replacement candidate? | yes/no, source ID |
| Similarity assessment | not_assessed/new_source/possible_duplicate/replacement_candidate/supersedes_existing/not_relevant |
| Source status | candidate/draft/intake/review/approved/superseded/retired |

## Why This Change Is Needed

Explain the governance, platform, audit, architecture or downstream consumer reason.

## Impact Analysis

| Area | Impact |
|---|---|
| Policy or directive |  |
| DevSecOps controls |  |
| Platform model |  |
| Architecture governance |  |
| OPA policies |  |
| Schemas and evidence contracts |  |
| Viewer, status indexes or intake |  |
| Release package or baseline |  |
| Downstream repositories |  |

## Replacement Review

Use this section only when a new or updated source document may match or
replace an existing source document. Skip it for ordinary documentation,
implementation notes, role models, runbooks, adapter templates, generated
reports and other non-source changes.

| Existing source ID | Similarity | Notes |
|---|---|---|
|  | unknown/low/medium/high/near_duplicate |  |

Decision:

- [ ] New independent source
- [ ] Possible duplicate, keep as candidate
- [ ] Replacement candidate, review required
- [ ] Replacement confirmed
- [ ] Not relevant, retire candidate
- [ ] Not a source-document replacement review item

Replacement notes:

-

## Derived Artifacts

List expected or changed derived artifacts.

- 

## Governance Behavior

Choose one:

- [ ] Documentation-only
- [ ] Report-only governance behavior
- [ ] Blocking governance behavior
- [ ] Release packaging only

Notes:

- 

## Release Decision

Choose one:

- [ ] No release required
- [ ] Release candidate required
- [ ] Patch baseline release required
- [ ] Minor baseline release required
- [ ] Major baseline release required

Release notes:

- 

## Validation Plan

Confirm what must pass before merge.

- [ ] `python3 scripts/validate_runtime_governance.py`
- [ ] `python3 scripts/validate_governance_repo.py`
- [ ] `python3 -m unittest discover -s tests`
- [ ] Source lineage regenerated or confirmed unchanged
- [ ] Viewer regenerated if status or presentation changed
- [ ] Downstream example checked if consumer behavior changed

## Reviewer Notes

List open decisions, assumptions or review focus.

- 
