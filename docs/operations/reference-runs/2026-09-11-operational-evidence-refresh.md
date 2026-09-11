# Operational evidence refresh — 11 September 2026

This is a dated maintenance record under
[GCR-2026-057](../../governance/change-requests/GCR-2026-057-september-operational-evidence-refresh.md).
Snapshots and projections become accepted repository state only when their PR
is merged. Workflow success, governance outcome and Evidence Trust remain
separate signals.

## Producer evaluations

| Consumer / domain | Real producer run | Context | Observed outcome |
| --- | --- | --- | --- |
| Factory / DevSecOps | [34503074356, attempt 2](https://github.com/joku-dev/ai-native-engineering-factory/actions/runs/34503074356/attempts/2) | Re-execution of the `main` push for `371251fe17c6923a810ab437a6c27fc7bfb624ed` | Workflow success; baseline gate fail in report-only mode |
| ha-CPsWMS / DevSecOps | [34601508976](https://github.com/joku-dev/ha-CPsWMS/actions/runs/34601508976) | Manual diagnostic on `716c3cda4fa5cef7504ca7b3263f0cd1697b6e6c` | 14 applicable controls passed; 32 not applicable in this diagnostic context |
| ha-CPsWMS / architecture | [34601511855](https://github.com/joku-dev/ha-CPsWMS/actions/runs/34601511855) | Manual diagnostic on the same revision | Pass |
| Demo consumer / DevSecOps | [34601516334](https://github.com/joku-dev/governance-framework-demo-consumer/actions/runs/34601516334) | Manual diagnostic on `bec6504cac36f1f93f5e6a0ecafb4cc84802ed9c` | Released baseline gate passed; this fallback result is not a full control-catalog evaluation |
| Demo consumer / architecture | [34601519946](https://github.com/joku-dev/governance-framework-demo-consumer/actions/runs/34601519946) | Manual diagnostic on the same revision | Findings retained in the architecture snapshot |
| Demo consumer / typed vulnerability evidence | [34601516334](https://github.com/joku-dev/governance-framework-demo-consumer/actions/runs/34601516334) | Separate `application-evidence` intake from the diagnostic run | Centrally re-verified Trust record; no separate governance pass is inferred |
| ha-CPsWMS / DevSecOps | [34602002201](https://github.com/joku-dev/ha-CPsWMS/actions/runs/34602002201) | New `main` push at `6976bb2af2b9d47d2934273c444b6c9b62a81ea2` | 16 applicable controls passed, 30 not applicable; separate replay Trust finding |
| ha-CPsWMS / architecture | [34602001140](https://github.com/joku-dev/ha-CPsWMS/actions/runs/34602001140) | New `main` push at the same revision | 4/4 gates passed, zero findings |

The Factory gate reported
`expected repository.direct_push_allowed=False, got True`. Its workflow is
configured as report-only, so the workflow completed successfully while the
gate result failed. The central snapshot preserves that failure. GitHub reports
that rulesets for this private repository require a plan upgrade; changing its
visibility is not an acceptable evidence-refresh operation.

`ha-CPsWMS` [maintenance PR #15](https://github.com/joku-dev/ha-CPsWMS/pull/15)
was merged under its existing rules as
`6976bb2af2b9d47d2934273c444b6c9b62a81ea2`, after all applicable checks passed.
It documents the refresh procedure and triggers fresh mainline evaluations.
Demo consumer [maintenance PR #4](https://github.com/joku-dev/governance-framework-demo-consumer/pull/4)
provides the corresponding documentation; its required review is still pending
at this observation. Manual runs do not clear the official stale-evidence warning.

## Collection and evidence limits

The central repository has no configured Actions secrets at this observation.
The maintainer's local authenticated CLI can read the private Factory run; the
central `GITHUB_TOKEN` cannot read arbitrary private producer artifacts. Local
intake used the existing collectors without persisting or publishing credentials.

The Factory and demo DevSecOps workflows publish `devsecops-pipeline-evidence`,
which contains `baseline-gate-result.json`. The existing collector supports that
fallback and records a one-gate summary. Missing full governance-run-input or
control-report flags must not be interpreted as proof that no SBOM or scan was
produced: those files exist in producer artifacts, but the fallback result does
not establish full control coverage. The ha-CPsWMS run also publishes the complete
`governance-control-evaluation` artifact, which is collected instead.

Historical snapshots remain unchanged. Local intake does not manufacture central
workflow telemetry; the health report's small central-run sample remains a limit.

The producer's own dispatch credential did trigger central intake for the new
ha-CPsWMS mainline runs. Architecture intake produced bot PR #66. DevSecOps intake
[34602095451](https://github.com/joku-dev/devsecops-governance-framework/actions/runs/34602095451)
collected its result but failed repository validation: the existing replay
finding also fails `trust_checks_clean`, which was missing from the legacy risk
record. GCR-2026-057 explicitly records that sixth criterion ID while retaining
the failed Trust result, pending accountable review and the existing deadline.
A retry after acceptance is needed to prove the complete automated DevSecOps path.

## Repository security observations

The local administrative API assessment gives **12 passed and 4 failed criteria**.
The versioned JSON and Markdown
[self-security reports](https://github.com/joku-dev/devsecops-governance-framework/blob/main/generated/reports/governance-repository-security.md)
record the observation time and evidence. They are dated assessments.

Verified enabled: secret scanning, secret push protection, automated Dependabot
security updates, private vulnerability reporting, and read-only default workflow
permissions. Main has PR review, required checks, and deletion/force-push protection
through an active ruleset. All 18 workflows declare permissions explicitly.

| Open criterion | Verified observation | Follow-up |
| --- | --- | --- |
| GRS-005 | Signed commits are not required on main | Establish accountable human and bot signing/recovery before a separate rule change |
| GRS-010 | No unpinned third-party workflow references; repository `sha_pinning_required=false` | Validate reusable workflows and enable repository-level pinning in a scoped hardening change |
| GRS-014 | `git verify-tag` reports no signature on all three existing released baseline/adoption tags | Introduce verified future release signing; preserve the existing released tags |
| GRS-016 | Repository `allowed_actions=all` | Define and test approved publishers/action references before restricting Actions |

The scheduled report uses a limited `GITHUB_TOKEN`. Settings it cannot read remain
unknown in that report even when the local administrative observation resolves
them. The standard workflow permissions have not been expanded and no broad
personal credential was installed in Actions. This assessment clarifies those
observations; it does not claim the four hardening items have been implemented.

## Branch cleanup

Three fully merged topic branches were deleted remotely and locally:
`docs/consistent-pilot-and-operations`, `docs/detailed-function-catalog`, and
`docs/executive-whitepaper-and-presentation`. Each remote deletion was conditional
on its verified merged commit. Five other stale remote-tracking references were
pruned; their server branches had already been deleted. The presentation branch
and open work were preserved.

## Acceptance boundary

The remaining consumer findings and incomplete blocking-readiness evidence remain
visible. This maintenance operation grants no production approval and no new
blocking readiness. The legacy ha-CPsWMS review deadline is unchanged.
