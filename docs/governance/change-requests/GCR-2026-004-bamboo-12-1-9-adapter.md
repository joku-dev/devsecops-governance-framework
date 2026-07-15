# Governance Change Request

## Summary

- Add Bamboo Data Center 12.1.9 YAML Specs templates for DevSecOps and architecture governance.
- Document the Bitbucket/Bamboo adapter path using repository-stored `bamboo-specs/bamboo.yaml`.
- Keep the change documentation/template-only with no changes to controls, schemas, OPA policies, releases or source-document registration.

## Change ID

```text
GCR-2026-004
```

## Source Document Intake

| Question | Answer |
|---|---|
| Full source-document intake required? | no |
| New or updated source document? | no |
| Source document path | not applicable |
| Reviewed non-source path | `docs/operations/bitbucket-bamboo-governance-adapter.md` and `pipeline-baseline/templates/bamboo/bamboo-specs/*.yaml` |
| Intake classification | technical implementation documentation and adapter templates |
| Register updated? | no |
| Supersedes existing source? | no |
| Possible duplicate or replacement candidate? | no |
| Similarity assessment | not_relevant |
| Source status | not applicable |

## Non-Source Change Classification

This change is outside full Source Document Intake because it does not add or
update a file under `docs/governance/source-documents/` and does not update the
source document register.

Classification decision:

- The change is accepted as technical implementation documentation and adapter
  template material.
- The change is not a governance document.
- The change is not a normative source document.
- The change does not belong under `docs/governance/source-documents/`.
- The source document register remains unchanged.
- The implementation describes how Bamboo can execute the existing central
  governance baseline; it does not define new governance requirements by
  itself.
- No controls, architecture markers, policies, schemas, evidence contracts,
  workflows, releases or baselines may be derived from this implementation
  description without a separate approved governance change request.
- Runtime governance behavior remains unchanged in this repository.

Classification record references:

- `docs/operations/bitbucket-bamboo-governance-adapter.md`
- `pipeline-baseline/templates/bamboo/bamboo-specs/bamboo.yaml`
- `pipeline-baseline/templates/bamboo/bamboo-specs/architecture-governance.yaml`
- `docs/governance/change-requests/GCR-2026-004-bamboo-12-1-9-adapter.md`
- `docs/operations/source-document-intake-process.md`
- `model/documents/source-document-register.yaml`

Human review decision:

- Accept the change as a Bamboo 12.1.9 adapter implementation description.
- Keep source-document registration unchanged.
- Keep release decision as `No release required`.
- Keep governance behavior as `Documentation-only`.
- Validate Bamboo YAML Specs in a real Bamboo 12.1.9 environment before using
  the templates operationally.

## Why This Change Is Needed

The company target platform uses Bitbucket and Bamboo, and the confirmed Bamboo target version is Bamboo Data Center 12.1.9. The repository already contained early Bamboo sketches, but it did not yet provide a concrete Bamboo 12.1.9 adoption path using the canonical repository-stored YAML Specs location.

This change adds a safer first integration path based on Bamboo YAML Specs and shell tasks instead of a custom Bamboo plugin. The governance repository remains the owner of controls, evidence contracts, schemas and reports.

## Impact Analysis

| Area | Impact |
|---|---|
| Policy or directive | None. |
| DevSecOps controls | None. |
| Platform model | Template and documentation only. |
| Architecture governance | Template and documentation only. |
| OPA policies | None. |
| Schemas and evidence contracts | None. |
| Viewer, status indexes or intake | None. |
| Release package or baseline | None. |
| Downstream repositories | Provides a Bamboo 12.1.9 starter template; no consuming repository is changed by this commit. |

## Replacement Review

Skipped because this change does not add or update a source document.

| Existing source ID | Similarity | Notes |
|---|---|---|
| not applicable | unknown | This is not a source-document replacement. |

Decision:

- [ ] New independent source
- [ ] Possible duplicate, keep as candidate
- [ ] Replacement candidate, review required
- [ ] Replacement confirmed
- [ ] Not relevant, retire candidate
- [x] Not a source-document replacement review item

Replacement notes:

- Existing early Bamboo sketch files are retained. New adoption should prefer the nested `bamboo-specs/*.yaml` templates.
- No candidate source exists and no retirement action is required.

## Derived Artifacts

- `pipeline-baseline/templates/bamboo/bamboo-specs/bamboo.yaml`
- `pipeline-baseline/templates/bamboo/bamboo-specs/architecture-governance.yaml`
- `docs/operations/bitbucket-bamboo-governance-adapter.md`
- Updates to Bamboo adapter README and operations navigation.

## Governance Behavior

Choose one:

- [x] Documentation-only
- [ ] Report-only governance behavior
- [ ] Blocking governance behavior
- [ ] Release packaging only

Notes:

- The templates show report-only and optional blocking modes, but this repository change does not change active governance behavior.

## Release Decision

Choose one:

- [x] No release required
- [ ] Release candidate required
- [ ] Patch baseline release required
- [ ] Minor baseline release required
- [ ] Major baseline release required

Release notes:

- No baseline release is required because the change adds adapter templates and documentation only.

## Validation Plan

Confirm what must pass before merge.

- [x] `python3 scripts/validate_runtime_governance.py`
- [x] `python3 scripts/validate_governance_repo.py`
- [x] `python3 -m unittest discover -s tests`
- [ ] Source lineage regenerated or confirmed unchanged
- [ ] Viewer regenerated if status or presentation changed
- [ ] Downstream example checked if consumer behavior changed

For this documentation/template-only change, repository validation is sufficient unless reviewers request the full suite. Bamboo YAML Specs must still be validated in a Bamboo 12.1.9 environment because local repository validation cannot prove linked repository and agent configuration.

Local YAML parse validation was also run for both new Bamboo Specs templates.

MkDocs build validation was attempted with `python3 -m mkdocs build --strict`, but the local environment does not have the `mkdocs` module installed.

## Reviewer Notes

- Confirm the template paths match the Bamboo repository-stored YAML Specs convention.
- Confirm that the adapter does not fork governance logic into Bamboo.
- Confirm report-only is the recommended initial rollout mode.
