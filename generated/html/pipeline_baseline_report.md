# CI/CD Pipeline Control Baseline Report

## Summary

- Control placements: 46
- Stages used: 8

## Controls by Stage

| Stage | Controls |
|---|---:|
| `plan` | 2 |
| `code` | 8 |
| `build` | 8 |
| `test` | 2 |
| `package` | 10 |
| `release` | 10 |
| `deploy` | 2 |
| `operate` | 4 |

## Controls by Gate Type

| Gate Type | Controls |
|---|---:|
| `blocking_gate` | 15 |
| `warning_gate` | 0 |
| `evidence_check` | 30 |
| `review_check` | 1 |

## Controls by Check Type

| Check Type | Controls |
|---|---:|
| `presence` | 10 |
| `linkage` | 8 |
| `threshold` | 2 |
| `configuration` | 14 |
| `approval` | 4 |
| `review` | 1 |
| `integrity` | 5 |
| `provenance` | 2 |

## Control Placement Detail

| Control | Stage | Gate Type | Check Type | Failure Result | Maturity |
|---|---|---|---|---|---|
| `DSCB-GOV-REQ-001` | `plan` | `evidence_check` | `presence` | `waiver_required` | `immediate` |
| `DSCB-GOV-REQ-002` | `release` | `review_check` | `review` | `manual_review_required` | `tool_integration_required` |
| `DSCB-GOV-REQ-003` | `release` | `blocking_gate` | `approval` | `fail` | `immediate` |
| `DSCB-GOV-REQ-004` | `release` | `evidence_check` | `linkage` | `waiver_required` | `immediate` |
| `DSCB-GOV-REQ-005` | `release` | `blocking_gate` | `approval` | `fail` | `immediate` |
| `DSCB-L1-REQ-001` | `plan` | `evidence_check` | `linkage` | `waiver_required` | `tool_integration_required` |
| `DSCB-L1-REQ-002` | `code` | `evidence_check` | `configuration` | `waiver_required` | `immediate` |
| `DSCB-L1-REQ-003` | `code` | `blocking_gate` | `configuration` | `fail` | `immediate` |
| `DSCB-L1-REQ-004` | `code` | `evidence_check` | `presence` | `waiver_required` | `tool_integration_required` |
| `DSCB-L1-REQ-005` | `package` | `evidence_check` | `presence` | `waiver_required` | `immediate` |
| `DSCB-L1-REQ-006` | `package` | `blocking_gate` | `linkage` | `fail` | `immediate` |
| `DSCB-L1-REQ-007` | `build` | `evidence_check` | `presence` | `waiver_required` | `immediate` |
| `DSCB-L1-REQ-008` | `build` | `evidence_check` | `presence` | `waiver_required` | `immediate` |
| `DSCB-L1-REQ-009` | `test` | `blocking_gate` | `presence` | `fail` | `immediate` |
| `DSCB-L1-REQ-010` | `release` | `blocking_gate` | `threshold` | `fail` | `tool_integration_required` |
| `DSCB-L1-REQ-011` | `package` | `blocking_gate` | `integrity` | `fail` | `immediate` |
| `DSCB-L1-REQ-012` | `package` | `evidence_check` | `presence` | `waiver_required` | `immediate` |
| `DSCB-L1-REQ-013` | `release` | `evidence_check` | `approval` | `waiver_required` | `tool_integration_required` |
| `DSCB-L1-REQ-014` | `deploy` | `blocking_gate` | `approval` | `fail` | `tool_integration_required` |
| `DSCB-L1-REQ-015` | `release` | `evidence_check` | `presence` | `waiver_required` | `immediate` |
| `DSCB-L1-REQ-016` | `operate` | `evidence_check` | `linkage` | `waiver_required` | `tool_integration_required` |
| `DSCB-L2-REQ-001` | `code` | `evidence_check` | `configuration` | `waiver_required` | `tool_integration_required` |
| `DSCB-L2-REQ-002` | `code` | `evidence_check` | `configuration` | `waiver_required` | `tool_integration_required` |
| `DSCB-L2-REQ-003` | `code` | `evidence_check` | `configuration` | `waiver_required` | `tool_integration_required` |
| `DSCB-L2-REQ-004` | `code` | `blocking_gate` | `configuration` | `fail` | `tool_integration_required` |
| `DSCB-L2-REQ-005` | `package` | `blocking_gate` | `configuration` | `fail` | `tool_integration_required` |
| `DSCB-L2-REQ-006` | `build` | `blocking_gate` | `configuration` | `fail` | `immediate` |
| `DSCB-L2-REQ-007` | `package` | `blocking_gate` | `integrity` | `fail` | `tool_integration_required` |
| `DSCB-L2-REQ-008` | `package` | `evidence_check` | `configuration` | `waiver_required` | `tool_integration_required` |
| `DSCB-L2-REQ-009` | `deploy` | `evidence_check` | `linkage` | `waiver_required` | `tool_integration_required` |
| `DSCB-L2-REQ-010` | `code` | `evidence_check` | `configuration` | `waiver_required` | `immediate` |
| `DSCB-L2-REQ-011` | `test` | `blocking_gate` | `presence` | `fail` | `immediate` |
| `DSCB-L2-REQ-012` | `release` | `blocking_gate` | `threshold` | `fail` | `immediate` |
| `DSCB-L2-REQ-013` | `operate` | `evidence_check` | `presence` | `waiver_required` | `tool_integration_required` |
| `DSCB-L2-REQ-014` | `operate` | `evidence_check` | `configuration` | `waiver_required` | `tool_integration_required` |
| `DSCB-L3-REQ-001` | `build` | `evidence_check` | `integrity` | `waiver_required` | `future` |
| `DSCB-L3-REQ-002` | `build` | `evidence_check` | `linkage` | `waiver_required` | `immediate` |
| `DSCB-L3-REQ-003` | `build` | `evidence_check` | `configuration` | `waiver_required` | `tool_integration_required` |
| `DSCB-L3-REQ-004` | `build` | `evidence_check` | `configuration` | `waiver_required` | `tool_integration_required` |
| `DSCB-L3-REQ-005` | `package` | `evidence_check` | `provenance` | `waiver_required` | `future` |
| `DSCB-L3-REQ-006` | `build` | `evidence_check` | `provenance` | `waiver_required` | `future` |
| `DSCB-L3-REQ-007` | `package` | `blocking_gate` | `integrity` | `fail` | `tool_integration_required` |
| `DSCB-L3-REQ-008` | `package` | `evidence_check` | `configuration` | `waiver_required` | `tool_integration_required` |
| `DSCB-L3-REQ-009` | `release` | `evidence_check` | `linkage` | `waiver_required` | `future` |
| `DSCB-L3-REQ-010` | `operate` | `evidence_check` | `integrity` | `waiver_required` | `future` |
| `DSCB-L3-REQ-011` | `release` | `evidence_check` | `linkage` | `waiver_required` | `tool_integration_required` |
