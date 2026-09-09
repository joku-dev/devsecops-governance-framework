# Public Repository Quickstart

## Goal And Safe Defaults

Start a consumer pilot with the released DevSecOps L1 baseline
`l1-baseline-v1.1.3` and, if in scope, Architecture L1
`architecture-baseline-l1-v0.1.0`.

All new pilot runs use `report-only`, including pushes to `main`. The released
DevSecOps wrapper still defaults to `block-on-error`, so explicitly supply
`governance_mode: report-only`. Architecture uses `fail_on_findings: false`.
A successful job proves execution; inspect the findings and source evidence.

Use the [pilot runbook](pilot-runbook.md) for roles, scope and exit decisions,
and the [central operations handbook](../operations/guides/governance-repository-operations-handbook.md)
for intake, reviews, daily reporting and recovery.

## 1. Select A Reviewed Adoption Template

The complete copyable workflows are maintained in `adoption-package/workflows/`.
Use that package from the current reviewed repository revision and record its
commit SHA. Copies in old release tags describe their historical defaults and
must be reviewed before use; copying an old template does not apply later fixes.
The reusable workflows called by the template remain pinned to released baselines.

From a local checkout of the governance repository:

```bash
git rev-parse HEAD
```

In the application repository, create a feature branch and copy:

| Source | Application destination |
|---|---|
| `adoption-package/workflows/devsecops-baseline.yml` | `.github/workflows/devsecops-baseline.yml` |
| `adoption-package/workflows/architecture-governance.yml` (optional) | `.github/workflows/architecture-governance.yml` |

The DevSecOps call must retain this explicit input for every pilot trigger:

```yaml
governance_mode: report-only
```

Do not add an event-based expression that enables blocking on the first main
push. Use the adoption package's complete workflow rather than combining partial
JSON or YAML snippets from historical examples.

## 2. Produce Evidence

Replace the package's first-run placeholders with application-owned outputs:

| File in `application-evidence` | Purpose |
|---|---|
| `dist/application-source.tar.gz` or adjusted artifact path | Actual application build/source artifact |
| `security/sbom.cyclonedx.json` | Generated SBOM |
| `security/vulnerability-scan.json` | Real scan data matching the consumed contract |
| `governance/governance-run-input.json` | Structured input based on actual repository/pipeline context |

Keep uploaded paths and workflow inputs aligned. Placeholder records may prove
wiring only and must be labelled in the pilot decision. They are not accepted
compliance evidence. See the [evidence contract](../operations/evidence/governance-evidence-contract.md).

## 3. Run And Inspect

1. Open the application PR and run the workflow in report-only mode.
2. Inspect job summaries and download the artifacts.
3. After review, merge through the application's normal protections and inspect
   its mainline run. The governance mode remains report-only.
4. Record run URL, source commit, baseline pin, real versus placeholder evidence
   and findings in the adoption decision record.

Expected artifact names from the released DevSecOps workflow include
`application-evidence` and `devsecops-pipeline-evidence`, plus
`devsecops-governance-run-input` when structured governance input is supplied.
Central intake derives control-evaluation reports from the collected input;
these are not an additional producer artifact promised by this wrapper.

Technical exceptions can still fail a report-only workflow. Report-only changes
how governance findings affect exit status; it does not guarantee every job succeeds.

## 4. Review Central Intake

The central [intake guide](../operations/evidence/governance-result-intake-and-viewer-usage.md)
explains manual or producer-triggered intake. The central collector creates a
bot PR. Official indexes and the viewer update after that PR is reviewed and
merged, not merely after collection succeeds. Token setup is documented in
[GitHub access maintenance](../operations/security/github-access-and-token-maintenance.md).

## 5. Record The Pilot Decision

Complete `adoption-package/checklists/first-adoption-checklist.md` and
`adoption-package/templates/adoption-decision-record.md`. Assign owners to gaps.

Continue report-only until the separate
[blocking migration procedure](../operations/processes/blocking-enforcement-migration-guide.md)
is satisfied. It requires current readiness evidence and accountable approval;
several green jobs alone are insufficient. Verify actual GitHub check names
before introducing any required-check binding.

The existing `ha-CPsWMS` blocking mode is a documented legacy exception, not the
new-pilot default. See [blocking alignment](../operations/status/blocking-mode-alignment.md).
