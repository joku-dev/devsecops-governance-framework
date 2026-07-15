# Control Coverage Report

## Summary

- Total controls: `46`
- Automated: `32`
- Manual: `3`
- Planned: `11`
- Not applicable: `0`

## Prioritized Planned Controls

### `DSCB-L3-REQ-001`

- Level: `L3`
- Priority: `high`
- Verification method: `hybrid`
- Policy candidate: `false`
- Rationale: Reproducible-build verification is not yet machine-implemented in the current repository evaluator.
- Next action: Add structured rebuild-verification evidence and implement evaluator logic for deterministic builds.

### `DSCB-L3-REQ-002`

- Level: `L3`
- Priority: `high`
- Verification method: `hybrid`
- Policy candidate: `false`
- Rationale: Version-controlled build-configuration evidence is not yet machine-implemented for L3 evaluation.
- Next action: Add explicit build-configuration metadata and evaluator support for version-control assertions.

### `DSCB-L3-REQ-003`

- Level: `L3`
- Priority: `high`
- Verification method: `automated`
- Policy candidate: `true`
- Rationale: Isolated build-environment checking is marked as automated but not yet implemented in the evaluator.
- Next action: Add explicit isolated-environment evidence fields and implement pass-fail logic.

### `DSCB-L3-REQ-004`

- Level: `L3`
- Priority: `high`
- Verification method: `automated`
- Policy candidate: `true`
- Rationale: Recreated-per-run build-environment checking is marked as automated but not yet evaluator-backed.
- Next action: Add recreatable-environment evidence and implement evaluator support.

### `DSCB-L3-REQ-007`

- Level: `L3`
- Priority: `high`
- Verification method: `automated`
- Policy candidate: `true`
- Rationale: Enterprise signing-infrastructure usage is marked as automated but not yet evaluator-backed.
- Next action: Add enterprise-signing evidence fields and implement evaluator logic for trusted signing.

### `DSCB-L3-REQ-008`

- Level: `L3`
- Priority: `high`
- Verification method: `automated`
- Policy candidate: `true`
- Rationale: Central signing-key management is marked as automated but not yet evaluator-backed for L3.
- Next action: Add centralized key-management evidence and evaluator support.

### `DSCB-L3-REQ-010`

- Level: `L3`
- Priority: `high`
- Verification method: `automated`
- Policy candidate: `true`
- Rationale: Runtime integrity verification is marked as automated but not yet implemented in the evaluator.
- Next action: Add runtime-integrity evidence fields and implement automated evaluation logic.

### `DSCB-L3-REQ-005`

- Level: `L3`
- Priority: `medium`
- Verification method: `hybrid`
- Policy candidate: `false`
- Rationale: Dependency provenance evidence exists conceptually but is not yet evaluated in machine-readable form.
- Next action: Extend the evidence contract with provenance fields and add evaluator logic.

### `DSCB-L3-REQ-006`

- Level: `L3`
- Priority: `medium`
- Verification method: `hybrid`
- Policy candidate: `false`
- Rationale: Build-time provenance recording is not yet implemented in the current evaluator.
- Next action: Add provenance-capture evidence and build-process evaluation logic.

### `DSCB-L3-REQ-009`

- Level: `L3`
- Priority: `medium`
- Verification method: `hybrid`
- Policy candidate: `false`
- Rationale: End-to-end lifecycle traceability beyond current L1 traceability coverage is not yet machine-implemented.
- Next action: Extend the evidence contract for deployment and lifecycle linkage and implement evaluator logic.

### `DSCB-L3-REQ-011`

- Level: `L3`
- Priority: `medium`
- Verification method: `automated`
- Policy candidate: `true`
- Rationale: Continuous lifecycle compliance evidence is marked as automated but not yet evaluator-backed.
- Next action: Extend lifecycle evidence generation and add evaluator logic for L3 compliance evidence.

## Full Control Status Table

| Control | Level | Status | Priority | Verification | Policy Candidate |
| --- | --- | --- | --- | --- | --- |
| `DSCB-GOV-REQ-001` | `GOV` | `manual` | `low` | `hybrid` | `false` |
| `DSCB-GOV-REQ-002` | `GOV` | `manual` | `low` | `hybrid` | `false` |
| `DSCB-GOV-REQ-003` | `GOV` | `automated` | `low` | `hybrid` | `true` |
| `DSCB-GOV-REQ-004` | `GOV` | `manual` | `low` | `hybrid` | `false` |
| `DSCB-GOV-REQ-005` | `GOV` | `automated` | `low` | `hybrid` | `true` |
| `DSCB-L1-REQ-001` | `L1` | `automated` | `low` | `hybrid` | `false` |
| `DSCB-L1-REQ-002` | `L1` | `automated` | `low` | `automated` | `true` |
| `DSCB-L1-REQ-003` | `L1` | `automated` | `low` | `automated` | `true` |
| `DSCB-L1-REQ-004` | `L1` | `automated` | `low` | `hybrid` | `false` |
| `DSCB-L1-REQ-005` | `L1` | `automated` | `low` | `automated` | `true` |
| `DSCB-L1-REQ-006` | `L1` | `automated` | `low` | `automated` | `true` |
| `DSCB-L1-REQ-007` | `L1` | `automated` | `low` | `automated` | `true` |
| `DSCB-L1-REQ-008` | `L1` | `automated` | `low` | `automated` | `true` |
| `DSCB-L1-REQ-009` | `L1` | `automated` | `low` | `automated` | `true` |
| `DSCB-L1-REQ-010` | `L1` | `automated` | `low` | `automated` | `true` |
| `DSCB-L1-REQ-011` | `L1` | `automated` | `low` | `automated` | `true` |
| `DSCB-L1-REQ-012` | `L1` | `automated` | `low` | `automated` | `true` |
| `DSCB-L1-REQ-013` | `L1` | `automated` | `low` | `hybrid` | `false` |
| `DSCB-L1-REQ-014` | `L1` | `automated` | `low` | `hybrid` | `false` |
| `DSCB-L1-REQ-015` | `L1` | `automated` | `low` | `automated` | `true` |
| `DSCB-L1-REQ-016` | `L1` | `automated` | `low` | `hybrid` | `false` |
| `DSCB-L2-REQ-001` | `L2` | `automated` | `low` | `hybrid` | `false` |
| `DSCB-L2-REQ-002` | `L2` | `automated` | `low` | `hybrid` | `false` |
| `DSCB-L2-REQ-003` | `L2` | `automated` | `low` | `automated` | `true` |
| `DSCB-L2-REQ-004` | `L2` | `automated` | `low` | `automated` | `true` |
| `DSCB-L2-REQ-005` | `L2` | `automated` | `low` | `automated` | `true` |
| `DSCB-L2-REQ-006` | `L2` | `automated` | `low` | `automated` | `true` |
| `DSCB-L2-REQ-007` | `L2` | `automated` | `low` | `automated` | `true` |
| `DSCB-L2-REQ-008` | `L2` | `automated` | `low` | `automated` | `true` |
| `DSCB-L2-REQ-009` | `L2` | `automated` | `low` | `hybrid` | `true` |
| `DSCB-L2-REQ-010` | `L2` | `automated` | `low` | `hybrid` | `true` |
| `DSCB-L2-REQ-011` | `L2` | `automated` | `low` | `automated` | `true` |
| `DSCB-L2-REQ-012` | `L2` | `automated` | `low` | `automated` | `true` |
| `DSCB-L2-REQ-013` | `L2` | `automated` | `low` | `automated` | `true` |
| `DSCB-L2-REQ-014` | `L2` | `automated` | `low` | `automated` | `true` |
| `DSCB-L3-REQ-001` | `L3` | `planned` | `high` | `hybrid` | `false` |
| `DSCB-L3-REQ-002` | `L3` | `planned` | `high` | `hybrid` | `false` |
| `DSCB-L3-REQ-003` | `L3` | `planned` | `high` | `automated` | `true` |
| `DSCB-L3-REQ-004` | `L3` | `planned` | `high` | `automated` | `true` |
| `DSCB-L3-REQ-005` | `L3` | `planned` | `medium` | `hybrid` | `false` |
| `DSCB-L3-REQ-006` | `L3` | `planned` | `medium` | `hybrid` | `false` |
| `DSCB-L3-REQ-007` | `L3` | `planned` | `high` | `automated` | `true` |
| `DSCB-L3-REQ-008` | `L3` | `planned` | `high` | `automated` | `true` |
| `DSCB-L3-REQ-009` | `L3` | `planned` | `medium` | `hybrid` | `false` |
| `DSCB-L3-REQ-010` | `L3` | `planned` | `high` | `automated` | `true` |
| `DSCB-L3-REQ-011` | `L3` | `planned` | `medium` | `automated` | `true` |
