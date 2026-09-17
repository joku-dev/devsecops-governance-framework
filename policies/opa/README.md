# Policy-as-Code Modules

The 15 Rego modules in this folder implement executable policy candidates for
DevSecOps and architecture runtime governance. They are derived from the
structured control, platform and architecture models and are validated by
`opa check policies/opa`, repository validation and unit tests.

They are intentionally generic. In a real pilot, the input model must be adapted to the selected platform, for example GitLab, GitHub Enterprise, Jenkins, Azure DevOps, Artifactory, Nexus, SonarQube, Dependency-Track, or DefectDojo.

## DevSecOps Rule Set

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
| `devsecops_release_readiness.rego` | Aggregated L1 release-readiness checks for branch protection, SBOM, vulnerability evidence and artifact integrity |

## Architecture Runtime Rule Set

| Rule | Main purpose |
|---|---|
| `architecture_readiness.rego` | Checks architecture-readiness markers and valid exceptions. |
| `architecture_integration_readiness.rego` | Checks integration-readiness markers and valid exceptions. |
| `architecture_operation_readiness.rego` | Checks operation-readiness markers and valid exceptions. |
| `architecture_release_readiness.rego` | Checks release-critical markers and valid exceptions. |

## Important

Policy-as-code should only enforce objectively checkable conditions. Requirements
that depend on expert judgment should produce evidence and review tasks rather
than hard automated denials. Whether findings fail a consumer workflow depends
on the released wrapper and the consumer's explicit mode; new pilots start in
report-only. The separate measured L1 and Evidence Trust projections do not
change these Rego decisions.
