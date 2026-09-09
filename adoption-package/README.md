# DevSecOps Governance Framework Adoption Package

## Purpose

This package gives application teams a minimal, copyable starting point for consuming the public DevSecOps Governance Framework.

Central baseline repository:

```text
joku-dev/devsecops-governance-framework
```

## Contents

| Path | Copy target in application repository | Purpose |
| --- | --- | --- |
| `workflows/devsecops-baseline.yml` | `.github/workflows/devsecops-baseline.yml` | Runs the public DevSecOps L1 baseline against uploaded application evidence. |
| `workflows/architecture-governance.yml` | `.github/workflows/architecture-governance.yml` | Runs the public Architecture L1 baseline. |
| `evidence/governance/governance-run-input.json` | `governance/governance-run-input.json` | Minimal structured DevSecOps evidence example. |
| `evidence/security/sbom.cyclonedx.json` | `security/sbom.cyclonedx.json` | Minimal SBOM placeholder for first wiring tests. |
| `evidence/security/vulnerability-scan.json` | `security/vulnerability-scan.json` | Minimal vulnerability scan placeholder for first wiring tests. |
| `evidence/.governance/architecture/*.json` | `.governance/architecture/*.json` | Optional architecture evidence placeholders. |
| `checklists/first-adoption-checklist.md` | Optional project checklist | Review checklist for first onboarding. |
| `templates/adoption-decision-record.md` | Optional project decision record | Documents whether a pilot stays in `report-only`, starts controlled blocking, or stops. |

## Recommended Rollout

1. Copy `workflows/devsecops-baseline.yml` into the application repository.
2. Replace the placeholder artifact build with the real build output.
3. Replace placeholder SBOM and vulnerability scan data with real tool output.
4. Record the reviewed template commit separately from the released baseline pins.
5. Keep PR, main-branch push and manual runs explicitly `report-only`. Any later blocking activation requires the [readiness assessment](../docs/operations/status/blocking-readiness.md), accountable approval and a separate consumer PR.
6. Add `workflows/architecture-governance.yml` when architecture runtime evidence should be evaluated.
7. Complete the first-adoption checklist; it supplements the readiness assessment and does not itself authorize a required-check change.
8. Record the pilot outcome with `templates/adoption-decision-record.md`.

## Expected First Result

The first successful wiring run should produce these GitHub Actions artifacts:

- `application-evidence`
- `devsecops-pipeline-evidence`
- `devsecops-governance-run-input`
- optionally `architecture-governance-evidence`

The first run is allowed to be diagnostic. A green report-only run means the wiring works; it does not automatically mean the repository is ready for blocking release governance.

## Known Limitations

- Placeholder SBOM and vulnerability files are only for first wiring tests.
- Architecture evidence files with `status: draft` are not approved evidence.
- Branch protection and review enforcement must be configured in the application repository.
- Application teams remain responsible for their own evidence quality and release decisions.
