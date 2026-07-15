# Governance Change Request: Agent Operations Documentation Migration

## Summary

- Move agent operations documentation into `docs/operations/agents/`.
- Update navigation, AI index, official entrypoints, agent instructions, tests and
  generator links to the new paths.
- Keep the change structural and documentation-focused without changing agent
  routing behavior or governance authority.

## Change ID

```text
GCR-2026-009
```

## Source Document Intake

| Question | Answer |
|---|---|
| Full source-document intake required? | no |
| New or updated source document? | no |
| Source document path | not applicable |
| Reviewed non-source path | `docs/operations/agents/` |
| Register updated? | no |
| Supersedes existing source? | no |
| Possible duplicate or replacement candidate? | no |
| Similarity assessment | not_relevant |
| Source status | not applicable |

## Why This Change Is Needed

The operations documentation has grown and now mixes runbooks, evidence
procedures, platform adapters, agent usage, reference runs and general
repository guidance.

Moving agent operations documentation into a dedicated subfolder is the first
low-risk migration package from the documentation structure model. It makes the
agent-related operating surface easier to find while preserving the source
document boundary and release baselines.

## Impact Analysis

| Area | Impact |
|---|---|
| Policy or directive | None |
| DevSecOps controls | None |
| Platform model | None |
| Architecture governance | None |
| OPA policies | None |
| Schemas and evidence contracts | None |
| Viewer, status indexes or intake | Viewer links regenerated for the moved agent usage snapshot path |
| Release package or baseline | None |
| Downstream repositories | Low; documentation paths moved within MkDocs navigation |

## Replacement Review

| Existing source ID | Similarity | Notes |
|---|---|---|
| not applicable | unknown | This is a documentation move, not a source-document replacement. |

Decision:

- [ ] New independent source
- [ ] Possible duplicate, keep as candidate
- [ ] Replacement candidate, review required
- [ ] Replacement confirmed
- [ ] Not relevant, retire candidate
- [x] Not a source-document replacement review item

Replacement notes:

- No files under `docs/governance/source-documents/` are added, moved or
  changed.

## Derived Artifacts

- `docs/operations/agents/agent-harness-usage.md`
- `docs/operations/agents/agent-system-usage.md`
- `docs/operations/agents/agent-usage-snapshot-2026-07-06.md`
- `docs/operations/agents/agent-usage-snapshot-latest.md`
- `docs/operations/agents/agent-usage-tracking.md`
- `docs/operations/agents/how-to-run-agent-review.md`
- `mkdocs.yml`
- `docs/official-entrypoints.md`
- `docs/ai-index.md`
- `AGENTS.md`
- `.agents/providers/mistral/README.md`
- `.agents/providers/mistral/governance-agent-dispatch.prompt.md`
- `.github/codex/prompts/governance-agent-dispatch.md`
- `scripts/generate_status_viewer.py`
- `generated/viewer/status-viewer.html`
- affected tests and cross-references

## Governance Behavior

Choose one:

- [x] Documentation-only
- [ ] Report-only governance behavior
- [ ] Blocking governance behavior
- [ ] Release packaging only

Notes:

- The change does not alter role routing, agent selection logic, provider review
  behavior, enforcement behavior, evidence contracts, schemas or OPA policy.

## Release Decision

Choose one:

- [x] No release required
- [ ] Release candidate required
- [ ] Patch baseline release required
- [ ] Minor baseline release required
- [ ] Major baseline release required

Release notes:

- No baseline release is required because this is a documentation structure
  migration only.

## Validation Plan

Confirm what must pass before merge.

- [x] `python3 scripts/validate_runtime_governance.py`
- [x] `python3 scripts/validate_governance_repo.py`
- [x] `python3 -m unittest discover -s tests`
- [x] Source lineage regenerated or confirmed unchanged
- [x] Viewer regenerated if status or presentation changed
- [ ] Downstream example checked if consumer behavior changed

## Reviewer Notes

- Review whether the moved paths are correctly reflected in MkDocs navigation,
  official entrypoints, AI index, agent prompts and tests.
- Review whether any old external links need follow-up compatibility handling.
- `python3 -m mkdocs build --strict` was attempted but could not run in the
  local environment because the `mkdocs` Python module is not installed.
