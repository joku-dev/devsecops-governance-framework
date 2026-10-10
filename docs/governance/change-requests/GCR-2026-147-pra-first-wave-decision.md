# GCR-2026-147: PRA first-wave requirement and platform decision

## Decision

On 9 October 2026, the Platform Owner accepted the complete recommendation in
`docs/governance/review-packets/PRA-2026-001/recommendation.md`.

The decision covers all 56 proposals from `PRA-STD-REQ-001`:

- 16 requirement classifications and platform-equivalence assessments are
  approved for the first wave;
- 12 partial implementations and six requirements without confirmed
  implementation remain open;
- 12 incomplete, context-dependent, heading or table-header entries are
  rejected in their current form or require a later corrected revision;
- 10 descriptive and traceability rows are rejected as standalone canonical
  requirements while remaining preserved as source evidence.

## Activation scope

The eight approved `new` or `extend` classifications are activated with
`authorized_derivations: [platform]` and `runtime_enforcement: none`.

The eight approved duplicate classifications resolve to existing canonical
DSCB requirements. Their requirement decisions are effective, but their
platform artifact adoption remains withheld because the active target GRQ
revisions do not authorize `platform` derivation. A later versioned canonical
lineage enhancement must preserve the existing revision and source history
before effective RTA entries can be added.

## Artifact decision

Existing platform artifacts assessed equivalent to the eight newly activated
PRA requirements may receive effective adoption entries in the
Requirement-to-Artifact Register. Each entry must pin the exact GRQ revision,
artifact ID, file hash and this decision reference.

Partial, missing, corrected and descriptive entries do not authorize an
effective platform mapping.

## Runtime and release effect

This decision does not change OPA logic, report-only or blocking behavior,
consumer workflows, released baselines or existing release packages. The PRA
source remains `migration_in_progress` while 18 proposals remain open.
