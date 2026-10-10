# Source Document Intake Review Briefs

Generated: `2026-10-09T16:54:53Z`

## Decision State

- Current state: `decision_support_only`
- Autonomous decisions enabled: `false`
- Runtime governance changed: `false`
- Stricter rules enabled: `false`

## Summary

- Review briefs: `9`
- Human decisions required: `9`

## Focus Counts

| Focus | Count |
|---|---:|
| `coexistence and derivation scope` | `4` |
| `lineage maintenance` | `3` |
| `replacement decision` | `2` |

## Briefs

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
- Operational artifact count is 2.
- Impact release consideration is no_release_by_default.

Required inputs:

- source document owner decision
- change request with documented rationale
- impact classification: documentation-only, model change, policy change, schema change, or release change

Decision options:

- `maintain_current_state`: No decision required beyond normal lineage maintenance.

Decision template:

- Review decision: `<new_independent_source|related_source_confirmed|keep_related_candidate|possible_duplicate|replacement_candidate|replacement_confirmed|not_relevant|keep_draft>`
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
- Operational artifact count is 2.
- Impact release consideration is no_release_by_default.

Required inputs:

- source document owner decision
- change request with documented rationale
- impact classification: documentation-only, model change, policy change, schema change, or release change

Decision options:

- `maintain_current_state`: No decision required beyond normal lineage maintenance.

Decision template:

- Review decision: `<new_independent_source|related_source_confirmed|keep_related_candidate|possible_duplicate|replacement_candidate|replacement_confirmed|not_relevant|keep_draft>`
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
- Operational artifact count is 20.
- Impact release consideration is baseline_release_review.

Required inputs:

- source document owner decision
- change request with documented rationale
- impact classification: documentation-only, model change, policy change, schema change, or release change
- architecture owner or enterprise architect review

Decision options:

- `maintain_current_state`: No decision required beyond normal lineage maintenance.

Decision template:

- Review decision: `<new_independent_source|related_source_confirmed|keep_related_candidate|possible_duplicate|replacement_candidate|replacement_confirmed|not_relevant|keep_draft>`
- Decision owner: `architecture-owners`
- Decision date: `<YYYY-MM-DD>`
- Derived artifacts allowed: `<yes/no>`
- Runtime governance change: `<yes/no>`
- Release decision: `baseline_release_review`

Guardrails:

- The agent must not promote the source document.
- The agent must not update derived controls, policies, schemas, releases, or runtime governance from a candidate.
- A human-owned change request must record the final decision.

### `SDI-REVIEW-ARCH-GOV-REQ-001`

- Prepared by agent: `source-document-intake`
- Agent scope: `decision_support_only`
- Autonomous decision: `false`
- Decision authority: `architecture-owners`
- Review focus: `replacement decision`
- Source ID: `ARCH-GOV-REQ-001`
- Title: Architecture Governance Framework Requirements Extract
- Status: `candidate`
- Source path: `docs/governance/source-documents/ARCH-GOV-SRC-002.requirements.md`

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

- Review decision: `<new_independent_source|related_source_confirmed|keep_related_candidate|possible_duplicate|replacement_candidate|replacement_confirmed|not_relevant|keep_draft>`
- Decision owner: `architecture-owners`
- Decision date: `<YYYY-MM-DD>`
- Derived artifacts allowed: `<yes/no>`
- Runtime governance change: `<yes/no>`
- Release decision: `no_release_by_default`

Guardrails:

- The agent must not promote the source document.
- The agent must not update derived controls, policies, schemas, releases, or runtime governance from a candidate.
- A human-owned change request must record the final decision.

### `SDI-REVIEW-CISO-REQ-SRC-001`

- Prepared by agent: `source-document-intake`
- Agent scope: `decision_support_only`
- Autonomous decision: `false`
- Decision authority: `governance-owners`
- Review focus: `coexistence and derivation scope`
- Source ID: `CISO-REQ-SRC-001`
- Title: CISO Standards Requirements Catalog Candidate
- Status: `candidate`
- Source path: `docs/governance/source-documents/CISO-REQ-SRC-001.candidate-intake.md`

Agent observations:

- Current status is candidate.
- Review state is candidate_related_source_review_required.
- Operational artifact count is 0.
- Impact release consideration is no_release_by_default.

Required inputs:

- source document owner decision
- change request with documented rationale
- impact classification: documentation-only, model change, policy change, schema change, or release change
- architecture owner or enterprise architect review

Decision options:

- `related_source_confirmed`: Accept the source as related material with explicit scope and coexistence boundaries.
- `keep_related_candidate`: Keep the related source visible for analysis without authorizing derivation.
- `not_relevant_retire`: Close the source for future derivation while preserving the review history.

Decision template:

- Review decision: `<new_independent_source|related_source_confirmed|keep_related_candidate|possible_duplicate|replacement_candidate|replacement_confirmed|not_relevant|keep_draft>`
- Decision owner: `governance-owners`
- Decision date: `<YYYY-MM-DD>`
- Derived artifacts allowed: `<yes/no>`
- Runtime governance change: `<yes/no>`
- Release decision: `no_release_by_default`

Guardrails:

- The agent must not promote the source document.
- The agent must not update derived controls, policies, schemas, releases, or runtime governance from a candidate.
- A human-owned change request must record the final decision.

### `SDI-REVIEW-DEVSECOPS-POL-CAND-002`

- Prepared by agent: `source-document-intake`
- Agent scope: `decision_support_only`
- Autonomous decision: `false`
- Decision authority: `governance-owners`
- Review focus: `replacement decision`
- Source ID: `DEVSECOPS-POL-CAND-002`
- Title: DevSecOps Policy Integrated v2 Change-Marked Candidate
- Status: `candidate`
- Source path: `docs/governance/source-documents/DevSecOps_Policy_Review_Integrated_v2_CHANGE_MARKED.md`

Agent observations:

- Current status is candidate.
- Review state is candidate_replacement_review_required.
- Operational artifact count is 0.
- Impact release consideration is no_release_by_default.

Required inputs:

- source document owner decision
- change request with documented rationale
- impact classification: documentation-only, model change, policy change, schema change, or release change
- replacement confirmation against the referenced existing source

Decision options:

- `replacement_confirmed`: Accept this source as replacing the referenced source after human review.
- `related_source_keep_candidate`: Keep the source registered as related material, but do not replace the active source.
- `duplicate_or_not_relevant_retire`: Close the source for future derivation while preserving history.

Decision template:

- Review decision: `<new_independent_source|related_source_confirmed|keep_related_candidate|possible_duplicate|replacement_candidate|replacement_confirmed|not_relevant|keep_draft>`
- Decision owner: `governance-owners`
- Decision date: `<YYYY-MM-DD>`
- Derived artifacts allowed: `<yes/no>`
- Runtime governance change: `<yes/no>`
- Release decision: `no_release_by_default`

Guardrails:

- The agent must not promote the source document.
- The agent must not update derived controls, policies, schemas, releases, or runtime governance from a candidate.
- A human-owned change request must record the final decision.

### `SDI-REVIEW-TOOLCHAIN-ARCH-CAND-001`

- Prepared by agent: `source-document-intake`
- Agent scope: `decision_support_only`
- Autonomous decision: `false`
- Decision authority: `platform-owners`
- Review focus: `coexistence and derivation scope`
- Source ID: `TOOLCHAIN-ARCH-CAND-001`
- Title: Enterprise SDLC Toolchain Reference Architecture v0.3
- Status: `candidate`
- Source path: `docs/governance/source-documents/Enterprise_SDLC_Toolchain_Reference_Architecture_v0.3.md`

Agent observations:

- Current status is candidate.
- Review state is candidate_related_source_review_required.
- Operational artifact count is 0.
- Impact release consideration is no_release_by_default.

Required inputs:

- source document owner decision
- change request with documented rationale
- impact classification: documentation-only, model change, policy change, schema change, or release change
- architecture owner or enterprise architect review

Decision options:

- `related_source_confirmed`: Accept the source as related material with explicit scope and coexistence boundaries.
- `keep_related_candidate`: Keep the related source visible for analysis without authorizing derivation.
- `not_relevant_retire`: Close the source for future derivation while preserving the review history.

Decision template:

- Review decision: `<new_independent_source|related_source_confirmed|keep_related_candidate|possible_duplicate|replacement_candidate|replacement_confirmed|not_relevant|keep_draft>`
- Decision owner: `platform-owners`
- Decision date: `<YYYY-MM-DD>`
- Derived artifacts allowed: `<yes/no>`
- Runtime governance change: `<yes/no>`
- Release decision: `no_release_by_default`

Guardrails:

- The agent must not promote the source document.
- The agent must not update derived controls, policies, schemas, releases, or runtime governance from a candidate.
- A human-owned change request must record the final decision.

### `SDI-REVIEW-SDLC-PROC-CAND-001`

- Prepared by agent: `source-document-intake`
- Agent scope: `decision_support_only`
- Autonomous decision: `false`
- Decision authority: `governance-owners`
- Review focus: `coexistence and derivation scope`
- Source ID: `SDLC-PROC-CAND-001`
- Title: Software Development Process DevSecOps V5 Activity RACI and Artifacts
- Status: `candidate`
- Source path: `docs/governance/source-documents/Software_Development_Process_DevSecOps_V5_Activity_RACI_Artifacts.md`

Agent observations:

- Current status is candidate.
- Review state is candidate_related_source_review_required.
- Operational artifact count is 0.
- Impact release consideration is no_release_by_default.

Required inputs:

- source document owner decision
- change request with documented rationale
- impact classification: documentation-only, model change, policy change, schema change, or release change

Decision options:

- `related_source_confirmed`: Accept the source as related material with explicit scope and coexistence boundaries.
- `keep_related_candidate`: Keep the related source visible for analysis without authorizing derivation.
- `not_relevant_retire`: Close the source for future derivation while preserving the review history.

Decision template:

- Review decision: `<new_independent_source|related_source_confirmed|keep_related_candidate|possible_duplicate|replacement_candidate|replacement_confirmed|not_relevant|keep_draft>`
- Decision owner: `governance-owners`
- Decision date: `<YYYY-MM-DD>`
- Derived artifacts allowed: `<yes/no>`
- Runtime governance change: `<yes/no>`
- Release decision: `no_release_by_default`

Guardrails:

- The agent must not promote the source document.
- The agent must not update derived controls, policies, schemas, releases, or runtime governance from a candidate.
- A human-owned change request must record the final decision.

### `SDI-REVIEW-SW-INDUSTRIALISATION-OM-CAND-001`

- Prepared by agent: `source-document-intake`
- Agent scope: `decision_support_only`
- Autonomous decision: `false`
- Decision authority: `governance-owners`
- Review focus: `coexistence and derivation scope`
- Source ID: `SW-INDUSTRIALISATION-OM-CAND-001`
- Title: Software Industrialisation Enterprise Operating Model Proposal
- Status: `candidate`
- Source path: `docs/governance/source-documents/Software_Industrialisation_Enterprise_Operating_Model_revised_extended_scope_polished.md`

Agent observations:

- Current status is candidate.
- Review state is candidate_related_source_review_required.
- Operational artifact count is 0.
- Impact release consideration is no_release_by_default.

Required inputs:

- source document owner decision
- change request with documented rationale
- impact classification: documentation-only, model change, policy change, schema change, or release change
- architecture owner or enterprise architect review

Decision options:

- `related_source_confirmed`: Accept the source as related material with explicit scope and coexistence boundaries.
- `keep_related_candidate`: Keep the related source visible for analysis without authorizing derivation.
- `not_relevant_retire`: Close the source for future derivation while preserving the review history.

Decision template:

- Review decision: `<new_independent_source|related_source_confirmed|keep_related_candidate|possible_duplicate|replacement_candidate|replacement_confirmed|not_relevant|keep_draft>`
- Decision owner: `governance-owners`
- Decision date: `<YYYY-MM-DD>`
- Derived artifacts allowed: `<yes/no>`
- Runtime governance change: `<yes/no>`
- Release decision: `no_release_by_default`

Guardrails:

- The agent must not promote the source document.
- The agent must not update derived controls, policies, schemas, releases, or runtime governance from a candidate.
- A human-owned change request must record the final decision.
