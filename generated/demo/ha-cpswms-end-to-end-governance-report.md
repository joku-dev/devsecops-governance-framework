# End-to-End Governance Report

## Target

- Repository: `/workspace/ha-CPsWMS`
- Commit: `77e8fcd`
- Release ID: `ha-CPsWMS-demo`

## Overall Result

| Domain | Status | Findings | Detail report |
|---|---:|---:|---|
| Architecture Runtime Governance | PASS | 0 | `ha-cpswms-architecture-governance-report.md` |
| DevSecOps Governance | PASS | 0 | `ha-cpswms-devsecops-governance-report.md` |
| **Overall** | **PASS** | **0** | |

## Interpretation

The target repository currently satisfies the governance gates for both architecture runtime governance and DevSecOps release governance.

This does not mean the system is production-certified. It means that the required evidence is present, machine-readable, and accepted by the current governance policies.

## Architecture Findings

No architecture findings.

## DevSecOps Findings

No DevSecOps findings.

## Evidence Model

The report uses two evidence layers:

- `.governance/architecture/*.json` for architecture baseline, compatibility, security, resilience, operation and feedback evidence.
- `.governance/devsecops/release-evidence.json` for DevSecOps release evidence such as SBOM, vulnerability scan, artifact integrity, dependency source approval and pipeline security gate evidence.

The governance repository turns those files into policy inputs, evaluates OPA policies and produces human-readable reports.
