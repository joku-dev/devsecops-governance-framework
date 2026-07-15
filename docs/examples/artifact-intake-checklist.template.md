# Artifact Intake Checklist Template

## Artifact Summary

| Field | Value |
|---|---|
| Artifact name |  |
| Artifact type | source/evidence/example/schema/policy/model/workflow/documentation/generated/release |
| Intended use |  |
| Proposed target path |  |
| Owner |  |
| Related change request | `GCR-YYYY-NNN` |

## Classification

| Question | Answer |
|---|---|
| Is this authoritative source material? | yes/no |
| Is full Source Document Intake required? | yes/no |
| Is this runtime evidence from a downstream repository? | yes/no |
| Is this generated output? | yes/no |
| Is this release package content? | yes/no |
| Is this documentation, publishing material or an example? | yes/no |

## Impact

| Area | Impact |
|---|---|
| Source document register | none/update required |
| Evidence contract | none/additive/breaking |
| Runtime governance behavior | none/report-only/blocking |
| Schemas | none/update required |
| OPA policies or workflow logic | none/update required |
| Viewer or status indexes | none/regenerate required |
| Release package or baseline | none/patch/minor/major |
| Downstream repositories | none/documentation/optional adoption/required migration |

## Required Actions

- [ ] Target folder confirmed.
- [ ] Owning process identified.
- [ ] Governance change request created or updated.
- [ ] Source Document Intake decision recorded.
- [ ] Evidence contract impact recorded.
- [ ] Runtime governance behavior recorded.
- [ ] Release decision recorded.
- [ ] Required validators listed.
- [ ] Generated artifacts refreshed only through scripts when required.
- [ ] Historical records left unchanged unless explicitly in scope.

## Validation

- [ ] `python3 scripts/validate_runtime_governance.py`
- [ ] `python3 scripts/validate_governance_repo.py`
- [ ] `python3 -m unittest discover -s tests`
- [ ] `.venv-docs/bin/mkdocs build --strict`
- [ ] Additional validator:

## Decision

| Decision field | Value |
|---|---|
| Accept artifact into target path? | yes/no |
| Defer for more review? | yes/no |
| Reject or retire candidate? | yes/no |
| Reviewer |  |
| Decision date |  |
