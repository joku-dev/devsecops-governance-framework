# Control Evaluation Report

Input File: `demo/inputs/release-candidate-red.json`
Required Platform Level: `PRA-Level 2`
Release Candidate: `true`
Run Context: `release`

## Summary

- Total controls: `46`
- Applicable controls: `30`
- Tested controls: `30`
- Passed: `2`
- Failed: `28`
- Not tested: `0`
- Not applicable: `16`

## Control Decisions

| Control | Level | Method | Status | Message |
| --- | --- | --- | --- | --- |
| `DSCB-GOV-REQ-001` | `GOV` | `hybrid` | `not_applicable` | Governance-board-level controls are not directly evaluated by this repository pipeline run. |
| `DSCB-GOV-REQ-002` | `GOV` | `hybrid` | `not_applicable` | Governance-board-level controls are not directly evaluated by this repository pipeline run. |
| `DSCB-GOV-REQ-003` | `GOV` | `hybrid` | `not_applicable` | Governance-board-level controls are not directly evaluated by this repository pipeline run. |
| `DSCB-GOV-REQ-004` | `GOV` | `hybrid` | `not_applicable` | Governance-board-level controls are not directly evaluated by this repository pipeline run. |
| `DSCB-GOV-REQ-005` | `GOV` | `hybrid` | `not_applicable` | Governance-board-level controls are not directly evaluated by this repository pipeline run. |
| `DSCB-L1-REQ-001` | `L1` | `hybrid` | `fail` | Traceability is evaluated from explicit structured linkage fields for requirements, testcases, and reports. |
| `DSCB-L1-REQ-002` | `L1` | `automated` | `fail` | Source control governance is evaluated from explicit version-control, author-traceability, and review-record fields. |
| `DSCB-L1-REQ-003` | `L1` | `automated` | `fail` | Mapped policy `branch_protection` returned 2 deny messages. |
| `DSCB-L1-REQ-004` | `L1` | `hybrid` | `fail` | Secure coding evidence is evaluated from structured static-analysis execution and review fields. |
| `DSCB-L1-REQ-005` | `L1` | `automated` | `fail` | Dependencies are treated as documented when the input includes a dependency list and an SBOM. |
| `DSCB-L1-REQ-006` | `L1` | `automated` | `fail` | Mapped policy `sbom` returned 1 deny messages. |
| `DSCB-L1-REQ-007` | `L1` | `automated` | `pass` | The run is treated as pipeline-executed when structured pipeline metadata is present. |
| `DSCB-L1-REQ-008` | `L1` | `automated` | `fail` | Artifact uniqueness is inferred from digest presence or explicit artifact version metadata. |
| `DSCB-L1-REQ-009` | `L1` | `automated` | `fail` | Mapped policy `vulnerability_gate` returned 2 deny messages. |
| `DSCB-L1-REQ-010` | `L1` | `automated` | `fail` | Mapped policy `vulnerability_gate` returned 2 deny messages. |
| `DSCB-L1-REQ-011` | `L1` | `automated` | `fail` | Mapped policy `artifact_integrity` returned 1 deny messages. |
| `DSCB-L1-REQ-012` | `L1` | `automated` | `fail` | Artifact identity is inferred from digest linkage to the evaluated artifact. |
| `DSCB-L1-REQ-013` | `L1` | `hybrid` | `fail` | Release authorization is evaluated from explicit structured approval metadata. |
| `DSCB-L1-REQ-014` | `L1` | `hybrid` | `fail` | Approved-artifact deployment is evaluated from explicit release approval metadata plus artifact identity evidence. |
| `DSCB-L1-REQ-015` | `L1` | `automated` | `pass` | Machine-readable evidence generation is inferred from structured pipeline execution data. |
| `DSCB-L1-REQ-016` | `L1` | `hybrid` | `fail` | Operational traceability is evaluated from explicit deployed-version and security-event recording fields. |
| `DSCB-L2-REQ-001` | `L2` | `hybrid` | `fail` | Development environment central management is evaluated from explicit environment management fields. |
| `DSCB-L2-REQ-002` | `L2` | `hybrid` | `fail` | Environment configuration compliance is evaluated from explicit baseline and compliance fields. |
| `DSCB-L2-REQ-003` | `L2` | `automated` | `fail` | Central identity management is taken directly from the evaluated platform metadata. |
| `DSCB-L2-REQ-004` | `L2` | `automated` | `fail` | Mapped policy `access_control` returned 2 deny messages. |
| `DSCB-L2-REQ-005` | `L2` | `automated` | `fail` | Dependency repository approval is inferred from the source_approved flag on all declared dependencies. |
| `DSCB-L2-REQ-006` | `L2` | `automated` | `fail` | Mapped policy `dependency_source_control` returned 2 deny messages. |
| `DSCB-L2-REQ-007` | `L2` | `automated` | `fail` | Mapped policy `artifact_signing` returned 1 deny messages. |
| `DSCB-L2-REQ-008` | `L2` | `automated` | `fail` | Signing key protection is taken from the signing metadata in the run input. |
| `DSCB-L2-REQ-009` | `L2` | `hybrid` | `fail` | Mapped policy `iac` returned 1 deny messages. |
| `DSCB-L2-REQ-010` | `L2` | `hybrid` | `fail` | Infrastructure version control is inferred from the IaC repository metadata. |
| `DSCB-L2-REQ-011` | `L2` | `automated` | `fail` | Mapped policy `pipeline_security_gates` returned 2 deny messages. |
| `DSCB-L2-REQ-012` | `L2` | `automated` | `fail` | Mapped policy `pipeline_security_gates` returned 2 deny messages. |
| `DSCB-L2-REQ-013` | `L2` | `automated` | `fail` | Security monitoring generation is evaluated from explicit monitoring event generation and integration fields. |
| `DSCB-L2-REQ-014` | `L2` | `automated` | `fail` | Security event forwarding is evaluated from explicit forwarding metadata. |
| `DSCB-L3-REQ-001` | `L3` | `hybrid` | `not_applicable` | Control requires PRA-Level 3, but the evaluated run declares PRA-Level 2. |
| `DSCB-L3-REQ-002` | `L3` | `hybrid` | `not_applicable` | Control requires PRA-Level 3, but the evaluated run declares PRA-Level 2. |
| `DSCB-L3-REQ-003` | `L3` | `automated` | `not_applicable` | Control requires PRA-Level 3, but the evaluated run declares PRA-Level 2. |
| `DSCB-L3-REQ-004` | `L3` | `automated` | `not_applicable` | Control requires PRA-Level 3, but the evaluated run declares PRA-Level 2. |
| `DSCB-L3-REQ-005` | `L3` | `hybrid` | `not_applicable` | Control requires PRA-Level 3, but the evaluated run declares PRA-Level 2. |
| `DSCB-L3-REQ-006` | `L3` | `hybrid` | `not_applicable` | Control requires PRA-Level 3, but the evaluated run declares PRA-Level 2. |
| `DSCB-L3-REQ-007` | `L3` | `automated` | `not_applicable` | Control requires PRA-Level 3, but the evaluated run declares PRA-Level 2. |
| `DSCB-L3-REQ-008` | `L3` | `automated` | `not_applicable` | Control requires PRA-Level 3, but the evaluated run declares PRA-Level 2. |
| `DSCB-L3-REQ-009` | `L3` | `hybrid` | `not_applicable` | Control requires PRA-Level 3, but the evaluated run declares PRA-Level 2. |
| `DSCB-L3-REQ-010` | `L3` | `automated` | `not_applicable` | Control requires PRA-Level 3, but the evaluated run declares PRA-Level 2. |
| `DSCB-L3-REQ-011` | `L3` | `automated` | `not_applicable` | Control requires PRA-Level 3, but the evaluated run declares PRA-Level 2. |
