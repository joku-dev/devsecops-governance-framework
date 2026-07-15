# Governance Demo Run

This run validates the repository, regenerates all governance artifacts, and evaluates two demo release candidates.

| Scenario | Result | Failing Policies | Summary |
| --- | --- | --- | --- |
| `green` | `pass` | - | `generated/demo/green-summary.md` |
| `red` | `fail` | branch_protection, sbom, vulnerability_gate, artifact_integrity, access_control, dependency_source_control, iac, artifact_signing, pipeline_security_gates | `generated/demo/red-summary.md` |

## Generated Governance Artifacts

- `generated/viewer/status-viewer.html`
- `generated/control-evaluation-report.json`
- `generated/control-evaluation-report.md`
- `generated/reports/open-gap-report.md`
- `generated/reports/document-control-matrix.md`
- `generated/documents/devsecops-pol-001.html`
- `generated/documents/devsecops-dir-001.html`
