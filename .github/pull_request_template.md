## Summary

Describe the governance change in 2-5 bullets.

- 

## Change Type

Mark all that apply.

- [ ] Source document intake or update
- [ ] Governance change request
- [ ] Policy update
- [ ] Directive update
- [ ] Control catalog update
- [ ] Architecture governance update
- [ ] Traceability update
- [ ] Evidence contract update
- [ ] Policy-as-code or workflow update
- [ ] Release package update
- [ ] New artifact intake or relocation
- [ ] Documentation-only change

## Why This Change Is Needed

Explain the governance, platform, audit, or consumer reason for the change.

## Affected Areas

List the main files or folders changed.

- 

## Source Document And Change Governance

Choose all that apply and explain briefly.

- [ ] New artifact classified with `docs/operations/processes/new-artifact-intake-process.md`
- [ ] No source document impact
- [ ] Source document added or replaced under `docs/governance/source-documents/`
- [ ] `model/documents/source-document-register.yaml` updated
- [ ] Governance Change Request added under `docs/governance/change-requests/`
- [ ] Source lineage regenerated or confirmed unchanged

Governance change notes:

-

## Governance Behavior

Choose one and explain briefly.

- [ ] Documentation-only
- [ ] Report-only behavior
- [ ] Blocking behavior
- [ ] Release packaging only

Behavior notes:

-

## Downstream Impact

Choose one and explain briefly.

- [ ] No downstream impact
- [ ] Downstream documentation impact only
- [ ] Downstream optional adoption improvement
- [ ] Downstream required migration

Downstream notes:

- 

## Evidence Contract Impact

Choose one and explain briefly.

- [ ] No evidence contract impact
- [ ] Additive optional evidence change
- [ ] Breaking evidence contract change

Contract notes:

- 

## Release Impact

Choose one and explain briefly.

- [ ] No release update needed
- [ ] Patch release candidate
- [ ] Minor release candidate
- [ ] Major release candidate

Release notes:

- 

## Validation

Confirm what was run.

- [ ] `python3 scripts/validate_runtime_governance.py`
- [ ] `python3 scripts/validate_governance_repo.py`
- [ ] `python3 -m unittest discover -s tests`
- [ ] Viewer or generated artifacts refreshed if needed
- [ ] Consumer-facing example checked if needed

## Reviewer Checklist

- [ ] Source document register and lineage are complete
- [ ] Governance Change Request or impact explanation is sufficient
- [ ] Policy/Directive intent is clear
- [ ] Control and traceability impact is clear
- [ ] Architecture governance impact is clear
- [ ] Downstream impact is clear
- [ ] Release documentation is sufficient
