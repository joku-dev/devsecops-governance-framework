# Policy-as-Code Starters

The Rego rules in this folder are initial executable policy candidates derived from the DevSecOps Control Baseline and Platform Reference Architecture.

They are intentionally generic. In a real pilot, the input model must be adapted to the selected platform, for example GitLab, GitHub Enterprise, Jenkins, Azure DevOps, Artifactory, Nexus, SonarQube, Dependency-Track, or DefectDojo.

## Initial Rule Set

| Rule | Main Requirement |
|---|---|
| `branch_protection.rego` | `DSCB-L1-REQ-003` |
| `sbom_required.rego` | `DSCB-L1-REQ-006` |
| `vulnerability_gate.rego` | `DSCB-L1-REQ-009`, `DSCB-L1-REQ-010` |
| `artifact_integrity.rego` | `DSCB-L1-REQ-011` |
| `dependency_source_control.rego` | `DSCB-L2-REQ-006` |
| `iac_required.rego` | `DSCB-L2-REQ-009`, `DSCB-L2-REQ-010` |
| `access_control.rego` | `DSCB-L2-REQ-003`, `DSCB-L2-REQ-004` |
| `artifact_signing.rego` | `DSCB-L2-REQ-007`, `DSCB-L2-REQ-008` |
| `pipeline_security_gates.rego` | `DSCB-L2-REQ-011`, `DSCB-L2-REQ-012` |
| `waiver_validity.rego` | `DSCB-GOV-REQ-005` |

## Important

Policy-as-code should only enforce objectively checkable conditions. Requirements that depend on expert judgment should produce evidence and review tasks rather than hard automated denials.
