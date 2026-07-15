# Source Document Intake Review Briefs

Generated: `2026-07-15T11:14:50Z`

## Decision State

- Current state: `decision_support_only`
- Autonomous decisions enabled: `false`
- Runtime governance changed: `false`
- Stricter rules enabled: `false`

## Summary

- Review briefs: `10`
- Human decisions required: `10`

## Focus Counts

| Focus | Count |
|---|---:|
| `lineage maintenance` | `3` |
| `replacement decision` | `1` |
| `similarity and source classification` | `4` |
| `source-of-truth and approval path` | `2` |

## Briefs

### `SDI-REVIEW-DEVSECOPS-POL-SRC-001`

- Prepared by agent: `source-document-intake`
- Agent scope: `decision_support_only`
- Autonomous decision: `false`
- Decision authority: `governance-owners`
- Review focus: `source-of-truth and approval path`
- Source ID: `DEVSECOPS-POL-SRC-001`
- Title: DevSecOps Policy Version 1 draft 3
- Status: `draft`
- Source path: `docs/governance/source-documents/DEVSECOPS-POL-SRC-001.public.md`

Agent observations:

- Current status is draft.
- Review state is draft_source_of_truth_decision_required.
- Operational artifact count is 2.
- Impact release consideration is no_release_by_default.

Required inputs:

- source document owner decision
- change request with documented rationale
- impact classification: documentation-only, model change, policy change, schema change, or release change
- source-of-truth and approval-path decision

Decision options:

- `confirm_as_working_source`: Keep the draft as governed working source material with explicit ownership.
- `keep_draft`: Keep the document visible but do not treat it as approved source material.
- `retire_or_supersede`: Close the draft if another source is authoritative.

Decision template:

- Review decision: `<new_independent_source|possible_duplicate|replacement_candidate|replacement_confirmed|not_relevant|keep_draft>`
- Decision owner: `governance-owners`
- Decision date: `<YYYY-MM-DD>`
- Derived artifacts allowed: `<yes/no>`
- Runtime governance change: `<yes/no>`
- Release decision: `no_release_by_default`

Guardrails:

- The agent must not promote the source document.
- The agent must not update derived controls, policies, schemas, releases, or runtime governance from a candidate.
- A human-owned change request must record the final decision.

### `SDI-REVIEW-DEVSECOPS-DIR-SRC-001`

- Prepared by agent: `source-document-intake`
- Agent scope: `decision_support_only`
- Autonomous decision: `false`
- Decision authority: `governance-owners`
- Review focus: `source-of-truth and approval path`
- Source ID: `DEVSECOPS-DIR-SRC-001`
- Title: DevSecOps Directive Version 0 draft 1
- Status: `draft`
- Source path: `docs/governance/source-documents/DEVSECOPS-DIR-SRC-001.public.md`

Agent observations:

- Current status is draft.
- Review state is draft_source_of_truth_decision_required.
- Operational artifact count is 2.
- Impact release consideration is no_release_by_default.

Required inputs:

- source document owner decision
- change request with documented rationale
- impact classification: documentation-only, model change, policy change, schema change, or release change
- source-of-truth and approval-path decision

Decision options:

- `confirm_as_working_source`: Keep the draft as governed working source material with explicit ownership.
- `keep_draft`: Keep the document visible but do not treat it as approved source material.
- `retire_or_supersede`: Close the draft if another source is authoritative.

Decision template:

- Review decision: `<new_independent_source|possible_duplicate|replacement_candidate|replacement_confirmed|not_relevant|keep_draft>`
- Decision owner: `governance-owners`
- Decision date: `<YYYY-MM-DD>`
- Derived artifacts allowed: `<yes/no>`
- Runtime governance change: `<yes/no>`
- Release decision: `no_release_by_default`

Guardrails:

- The agent must not promote the source document.
- The agent must not update derived controls, policies, schemas, releases, or runtime governance from a candidate.
- A human-owned change request must record the final decision.

### `SDI-REVIEW-ARCH-TPL-SRC-001`

- Prepared by agent: `source-document-intake`
- Agent scope: `decision_support_only`
- Autonomous decision: `false`
- Decision authority: `architecture-owners`
- Review focus: `similarity and source classification`
- Source ID: `ARCH-TPL-SRC-001`
- Title: SDD Architecture Template and Checklists
- Status: `candidate`
- Source path: `docs/governance/source-documents/ARCH-TPL-SRC-001.public.md`

Agent observations:

- Current status is candidate.
- Review state is candidate_similarity_review_required.
- Operational artifact count is 0.
- Impact release consideration is no_release_by_default.

Required inputs:

- source document owner decision
- change request with documented rationale
- impact classification: documentation-only, model change, policy change, schema change, or release change
- architecture owner or enterprise architect review

Decision options:

- `new_independent_source`: Accept the source as a separate intake source after review.
- `possible_duplicate`: Keep the source as a candidate until duplicate analysis is complete.
- `replacement_candidate`: Treat the source as a possible replacement, but require a separate replacement decision.
- `not_relevant_retire`: Close the source for governed derivation.

Decision template:

- Review decision: `<new_independent_source|possible_duplicate|replacement_candidate|replacement_confirmed|not_relevant|keep_draft>`
- Decision owner: `architecture-owners`
- Decision date: `<YYYY-MM-DD>`
- Derived artifacts allowed: `<yes/no>`
- Runtime governance change: `<yes/no>`
- Release decision: `no_release_by_default`

Guardrails:

- The agent must not promote the source document.
- The agent must not update derived controls, policies, schemas, releases, or runtime governance from a candidate.
- A human-owned change request must record the final decision.

### `SDI-REVIEW-ARCH-EA-SRC-001`

- Prepared by agent: `source-document-intake`
- Agent scope: `decision_support_only`
- Autonomous decision: `false`
- Decision authority: `architecture-owners`
- Review focus: `similarity and source classification`
- Source ID: `ARCH-EA-SRC-001`
- Title: SDD Enterprise Architecture Guidelines
- Status: `candidate`
- Source path: `docs/governance/source-documents/ARCH-EA-SRC-001.public.md`

Agent observations:

- Current status is candidate.
- Review state is candidate_similarity_review_required.
- Operational artifact count is 0.
- Impact release consideration is no_release_by_default.

Required inputs:

- source document owner decision
- change request with documented rationale
- impact classification: documentation-only, model change, policy change, schema change, or release change
- architecture owner or enterprise architect review

Decision options:

- `new_independent_source`: Accept the source as a separate intake source after review.
- `possible_duplicate`: Keep the source as a candidate until duplicate analysis is complete.
- `replacement_candidate`: Treat the source as a possible replacement, but require a separate replacement decision.
- `not_relevant_retire`: Close the source for governed derivation.

Decision template:

- Review decision: `<new_independent_source|possible_duplicate|replacement_candidate|replacement_confirmed|not_relevant|keep_draft>`
- Decision owner: `architecture-owners`
- Decision date: `<YYYY-MM-DD>`
- Derived artifacts allowed: `<yes/no>`
- Runtime governance change: `<yes/no>`
- Release decision: `no_release_by_default`

Guardrails:

- The agent must not promote the source document.
- The agent must not update derived controls, policies, schemas, releases, or runtime governance from a candidate.
- A human-owned change request must record the final decision.

### `SDI-REVIEW-ARCH-SA-SRC-001`

- Prepared by agent: `source-document-intake`
- Agent scope: `decision_support_only`
- Autonomous decision: `false`
- Decision authority: `architecture-owners`
- Review focus: `similarity and source classification`
- Source ID: `ARCH-SA-SRC-001`
- Title: SDD Solution Architecture Guidelines
- Status: `candidate`
- Source path: `docs/governance/source-documents/ARCH-SA-SRC-001.public.md`

Agent observations:

- Current status is candidate.
- Review state is candidate_similarity_review_required.
- Operational artifact count is 0.
- Impact release consideration is no_release_by_default.

Required inputs:

- source document owner decision
- change request with documented rationale
- impact classification: documentation-only, model change, policy change, schema change, or release change
- architecture owner or enterprise architect review

Decision options:

- `new_independent_source`: Accept the source as a separate intake source after review.
- `possible_duplicate`: Keep the source as a candidate until duplicate analysis is complete.
- `replacement_candidate`: Treat the source as a possible replacement, but require a separate replacement decision.
- `not_relevant_retire`: Close the source for governed derivation.

Decision template:

- Review decision: `<new_independent_source|possible_duplicate|replacement_candidate|replacement_confirmed|not_relevant|keep_draft>`
- Decision owner: `architecture-owners`
- Decision date: `<YYYY-MM-DD>`
- Derived artifacts allowed: `<yes/no>`
- Runtime governance change: `<yes/no>`
- Release decision: `no_release_by_default`

Guardrails:

- The agent must not promote the source document.
- The agent must not update derived controls, policies, schemas, releases, or runtime governance from a candidate.
- A human-owned change request must record the final decision.

### `SDI-REVIEW-ARCH-PA-SRC-001`

- Prepared by agent: `source-document-intake`
- Agent scope: `decision_support_only`
- Autonomous decision: `false`
- Decision authority: `architecture-owners`
- Review focus: `similarity and source classification`
- Source ID: `ARCH-PA-SRC-001`
- Title: SDD Product Architecture Guidelines
- Status: `candidate`
- Source path: `docs/governance/source-documents/ARCH-PA-SRC-001.public.md`

Agent observations:

- Current status is candidate.
- Review state is candidate_similarity_review_required.
- Operational artifact count is 0.
- Impact release consideration is no_release_by_default.

Required inputs:

- source document owner decision
- change request with documented rationale
- impact classification: documentation-only, model change, policy change, schema change, or release change
- architecture owner or enterprise architect review

Decision options:

- `new_independent_source`: Accept the source as a separate intake source after review.
- `possible_duplicate`: Keep the source as a candidate until duplicate analysis is complete.
- `replacement_candidate`: Treat the source as a possible replacement, but require a separate replacement decision.
- `not_relevant_retire`: Close the source for governed derivation.

Decision template:

- Review decision: `<new_independent_source|possible_duplicate|replacement_candidate|replacement_confirmed|not_relevant|keep_draft>`
- Decision owner: `architecture-owners`
- Decision date: `<YYYY-MM-DD>`
- Derived artifacts allowed: `<yes/no>`
- Runtime governance change: `<yes/no>`
- Release decision: `no_release_by_default`

Guardrails:

- The agent must not promote the source document.
- The agent must not update derived controls, policies, schemas, releases, or runtime governance from a candidate.
- A human-owned change request must record the final decision.

### `SDI-REVIEW-ARCH-GOV-SRC-002`

- Prepared by agent: `source-document-intake`
- Agent scope: `decision_support_only`
- Autonomous decision: `false`
- Decision authority: `architecture-owners`
- Review focus: `replacement decision`
- Source ID: `ARCH-GOV-SRC-002`
- Title: SDD Architecture Governance Framework
- Status: `candidate`
- Source path: `docs/governance/source-documents/ARCH-GOV-SRC-002.public.md`

Agent observations:

- Current status is candidate.
- Review state is candidate_replacement_review_required.
- Operational artifact count is 0.
- Impact release consideration is no_release_by_default.

Required inputs:

- source document owner decision
- change request with documented rationale
- impact classification: documentation-only, model change, policy change, schema change, or release change
- architecture owner or enterprise architect review
- replacement confirmation against the referenced existing source

Decision options:

- `replacement_confirmed`: Accept this source as replacing the referenced source after human review.
- `related_source_keep_candidate`: Keep the source registered as related material, but do not replace the active source.
- `duplicate_or_not_relevant_retire`: Close the source for future derivation while preserving history.

Decision template:

- Review decision: `<new_independent_source|possible_duplicate|replacement_candidate|replacement_confirmed|not_relevant|keep_draft>`
- Decision owner: `architecture-owners`
- Decision date: `<YYYY-MM-DD>`
- Derived artifacts allowed: `<yes/no>`
- Runtime governance change: `<yes/no>`
- Release decision: `no_release_by_default`

Guardrails:

- The agent must not promote the source document.
- The agent must not update derived controls, policies, schemas, releases, or runtime governance from a candidate.
- A human-owned change request must record the final decision.

### `SDI-REVIEW-DEVSECOPS-POL-REQ-001`

- Prepared by agent: `source-document-intake`
- Agent scope: `decision_support_only`
- Autonomous decision: `false`
- Decision authority: `governance-owners`
- Review focus: `lineage maintenance`
- Source ID: `DEVSECOPS-POL-REQ-001`
- Title: DevSecOps Policy Requirements Extract
- Status: `review`
- Source path: `docs/governance/source-documents/DEVSECOPS-POL-SRC-001.requirements.md`

Agent observations:

- Current status is review.
- Review state is active_review_in_progress.
- Operational artifact count is 0.
- Impact release consideration is no_release_by_default.

Required inputs:

- source document owner decision
- change request with documented rationale
- impact classification: documentation-only, model change, policy change, schema change, or release change

Decision options:

- `maintain_current_state`: No decision required beyond normal lineage maintenance.

Decision template:

- Review decision: `<new_independent_source|possible_duplicate|replacement_candidate|replacement_confirmed|not_relevant|keep_draft>`
- Decision owner: `governance-owners`
- Decision date: `<YYYY-MM-DD>`
- Derived artifacts allowed: `<yes/no>`
- Runtime governance change: `<yes/no>`
- Release decision: `no_release_by_default`

Guardrails:

- The agent must not promote the source document.
- The agent must not update derived controls, policies, schemas, releases, or runtime governance from a candidate.
- A human-owned change request must record the final decision.

### `SDI-REVIEW-DEVSECOPS-DIR-REQ-001`

- Prepared by agent: `source-document-intake`
- Agent scope: `decision_support_only`
- Autonomous decision: `false`
- Decision authority: `governance-owners`
- Review focus: `lineage maintenance`
- Source ID: `DEVSECOPS-DIR-REQ-001`
- Title: DevSecOps Directive Requirements Extract
- Status: `review`
- Source path: `docs/governance/source-documents/DEVSECOPS-DIR-SRC-001.requirements.md`

Agent observations:

- Current status is review.
- Review state is active_review_in_progress.
- Operational artifact count is 0.
- Impact release consideration is no_release_by_default.

Required inputs:

- source document owner decision
- change request with documented rationale
- impact classification: documentation-only, model change, policy change, schema change, or release change

Decision options:

- `maintain_current_state`: No decision required beyond normal lineage maintenance.

Decision template:

- Review decision: `<new_independent_source|possible_duplicate|replacement_candidate|replacement_confirmed|not_relevant|keep_draft>`
- Decision owner: `governance-owners`
- Decision date: `<YYYY-MM-DD>`
- Derived artifacts allowed: `<yes/no>`
- Runtime governance change: `<yes/no>`
- Release decision: `no_release_by_default`

Guardrails:

- The agent must not promote the source document.
- The agent must not update derived controls, policies, schemas, releases, or runtime governance from a candidate.
- A human-owned change request must record the final decision.

### `SDI-REVIEW-ARCH-SDD-REQ-001`

- Prepared by agent: `source-document-intake`
- Agent scope: `decision_support_only`
- Autonomous decision: `false`
- Decision authority: `architecture-owners`
- Review focus: `lineage maintenance`
- Source ID: `ARCH-SDD-REQ-001`
- Title: Integrated SDD Architecture Governance Requirements Extract
- Status: `review`
- Source path: `docs/governance/source-documents/ARCH-SDD-SRC-001.requirements.md`

Agent observations:

- Current status is review.
- Review state is active_review_in_progress.
- Operational artifact count is 0.
- Impact release consideration is no_release_by_default.

Required inputs:

- source document owner decision
- change request with documented rationale
- impact classification: documentation-only, model change, policy change, schema change, or release change
- architecture owner or enterprise architect review

Decision options:

- `maintain_current_state`: No decision required beyond normal lineage maintenance.

Decision template:

- Review decision: `<new_independent_source|possible_duplicate|replacement_candidate|replacement_confirmed|not_relevant|keep_draft>`
- Decision owner: `architecture-owners`
- Decision date: `<YYYY-MM-DD>`
- Derived artifacts allowed: `<yes/no>`
- Runtime governance change: `<yes/no>`
- Release decision: `no_release_by_default`

Guardrails:

- The agent must not promote the source document.
- The agent must not update derived controls, policies, schemas, releases, or runtime governance from a candidate.
- A human-owned change request must record the final decision.
