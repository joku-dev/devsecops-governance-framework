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
4. Keep pull requests and manual runs in `report-only`.
5. Switch protected `main` runs to `block-on-error` only after evidence is stable.
6. Add `workflows/architecture-governance.yml` when architecture runtime evidence should be evaluated.
7. Use the checklist before making the workflow a required branch-protection check.
8. Record the pilot outcome with `templates/adoption-decision-record.md`.

## Expected First Result

The first successful wiring run should produce these GitHub Actions artifacts:

- `application-evidence`
- `devsecops-pipeline-evidence`
- `governance-run-input`
- optionally `architecture-governance-evidence`

The first run is allowed to be diagnostic. A green report-only run means the wiring works; it does not automatically mean the repository is ready for blocking release governance.

## Known Limitations

- Placeholder SBOM and vulnerability files are only for first wiring tests.
- Architecture evidence files with `status: draft` are not approved evidence.
- Branch protection and review enforcement must be configured in the application repository.
- Application teams remain responsible for their own evidence quality and release decisions.
