# joku-dev/ai-native-engineering-factory Governance Onboarding Readiness

- Status: `ready`
- Generated: `2026-06-28T08:02:51Z`
- Target path: `/workspace/ai-native-engineering-factory`
- Recommended next step: Continue report-only central L1 runs and prepare branch protection before block-on-error enforcement.

## Summary

| Checks | Pass | Warn | Fail |
| --- | ---: | ---: | ---: |
| 5 | 5 | 0 | 0 |

## Checks

| Check | Status | Evidence | Recommendation |
| --- | --- | --- | --- |
| `repository_shape` Repository has discoverable project structure | `pass` | README.md<br>pyproject.toml<br>153 source/script files<br>137 test files | Keep README, setup instructions, source layout, and test entrypoints stable before wiring central governance. |
| `local_quality_gates` Local CI already covers tests, lint, typing, and governance freshness | `pass` | .github/workflows/devsecops-governance-l1.yml<br>.github/workflows/quality-gates.yml<br>.gitlab-ci.yml<br>pytest=True<br>ruff=True<br>mypy=True<br>governance_evidence_check=True<br>agent_execution_gate=True | Preserve existing local quality gates and add the central L1 baseline as a separate report-only job first. |
| `governance_evidence_surface` Repository already contains governance and execution evidence | `pass` | 51 governance docs<br>137 agent execution records<br>127 slice candidate records<br>17 generated governance examples | Map this repository-native evidence into the central L1 evidence contract instead of duplicating it manually. |
| `supply_chain_and_security_evidence` Security and supply-chain evidence is present or planned | `pass` | .factory/security/90-day-pilot-readiness.example.json<br>.factory/security/assurance-runtime-policy.json<br>.factory/security/authorization-dry-run-observations.example.json<br>.factory/security/authorized_keys.example<br>.factory/security/factory-execution-authorization.json<br>security_docs=True<br>ci_supply_chain_script=True<br>secrets_scan_support=True<br>sbom_or_vulnerability_artifact=True | Before mainline enforcement, provide concrete SBOM and vulnerability scan artifacts for central intake. |
| `central_baseline_integration` Central governance baseline workflow is wired | `pass` | scanner_status=pass<br>governance_ci_file_present: pass<br>governance_reference_present: pass<br>governance_commands_present: pass | Continue report-only L1 branch runs, publish a released baseline pin before production use, and move to block-on-error only after branch protection is ready. |
