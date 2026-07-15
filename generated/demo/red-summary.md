# Demo Scenario: red

Overall Result: `fail`
Input File: `demo/inputs/release-candidate-red.json`

| Policy | Result | Deny Messages |
| --- | --- | --- |
| `branch_protection` | `fail` | DSCB-L1-REQ-003: Direct modification of protected branches is prohibited.<br>DSCB-L1-REQ-003: Protected branch integration requires review. |
| `sbom` | `fail` | DSCB-L1-REQ-006: Release candidates require an SBOM. |
| `vulnerability_gate` | `fail` | DSCB-L1-REQ-009: Release candidates require vulnerability scan evidence.<br>DSCB-L1-REQ-010: Critical vulnerability CVE-DEMO-0001 requires an approved waiver. |
| `artifact_integrity` | `fail` | DSCB-L1-REQ-011: Releasable artifacts require checksum, digest, or signature evidence. |
| `access_control` | `fail` | DSCB-L2-REQ-003: DevSecOps platform access must be controlled through centralized identity management.<br>DSCB-L2-REQ-004: Multi-factor authentication must be enforced for privileged access. |
| `dependency_source_control` | `fail` | DSCB-L2-REQ-006: Dependency example-library is not retrieved from an approved source.<br>DSCB-L2-REQ-006: Direct downloads from external sources are not permitted. |
| `iac` | `fail` | DSCB-L2-REQ-009: Deployment infrastructure must be defined through Infrastructure as Code. |
| `artifact_signing` | `fail` | DSCB-L2-REQ-007: Software artifacts must be cryptographically signed before release. |
| `pipeline_security_gates` | `fail` | DSCB-L2-REQ-011: DevSecOps pipelines must enforce security gates.<br>DSCB-L2-REQ-012: Releases must not proceed when defined security thresholds are exceeded unless an approved waiver exists. |
| `waiver_validity` | `pass` | - |

## Control Evaluation Summary

- Tested controls: `30`
- Passed controls: `2`
- Failed controls: `28`
- Not tested: `0`
- Not applicable: `16`
