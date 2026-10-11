# Current Governance Platform State

## Observation Scope

Documentation observation: **9 October 2026**, source commit
`cf3c0344f65d4946fc5a205a6235edc1917b437e`. This is a dated read-only status
update, not a new compliance evaluation. Older sections retain their source
dates and are reference observations, not claims that every source is current.

## Live Readback, 9 October 2026

Read-only GitHub observation at `2026-10-09T07:41Z`; mainline source commit
`cf3c0344f65d4946fc5a205a6235edc1917b437e` (PR #246 merge).

| Area | Current observation | Interpretation |
|---|---|---|
| Main workflows | On `cf3c034`, Governance CI [37899276112](https://github.com/joku-dev/devsecops-governance-framework/actions/runs/37899276112), CodeQL [37899276000](https://github.com/joku-dev/devsecops-governance-framework/actions/runs/37899276000), Self-Security [37899276169](https://github.com/joku-dev/devsecops-governance-framework/actions/runs/37899276169), Consumer Lifecycle Guard [37899276129](https://github.com/joku-dev/devsecops-governance-framework/actions/runs/37899276129), Repository SBOM [37899276078](https://github.com/joku-dev/devsecops-governance-framework/actions/runs/37899276078) and Docs publication [37899276011](https://github.com/joku-dev/devsecops-governance-framework/actions/runs/37899276011) succeeded. | These runs validate repository workflows and publish the current docs. Self-Security job success means the assessment ran; it does not mean every criterion passed. A separate `workflow_run` Consumer Lifecycle Guard event [37899621930](https://github.com/joku-dev/devsecops-governance-framework/actions/runs/37899621930) was skipped by its event filter and is not a failed main push check. |
| Accepted ha-CPsWMS results | The latest accepted DevSecOps result is run [36997125273](https://github.com/joku-dev/ha-CPsWMS/actions/runs/36997125273), `pass` (16/16 applicable controls) on commit `5c3b5cb`; architecture is run [36997124090](https://github.com/joku-dev/ha-CPsWMS/actions/runs/36997124090), `PASS` (4/4 gates, zero findings) on the same commit. | The domain indexes were generated on 2 October. GitHub Actions lookup found no newer ha-CPsWMS `main` producer runs through this observation. These are the latest accepted results, not fresh 9 October evaluations. |
| ha-CPsWMS typed evidence | Latest accepted vulnerability evidence is run [36997124065](https://github.com/joku-dev/ha-CPsWMS/actions/runs/36997124065), captured 2 October; trust is `provenance_verified`, enforcement `report_only`, with 3,269 observations and maximum severity `critical`. | This is a historical scan snapshot. It does not establish current image contents, accepted risk, or production approval. No newer producer run was found. |
| Separate demo-consumer pilot | Its lifecycle projection remains `finding_state: closed`, 3 receipts and 4 actions, as of `2026-10-03T10:58:04Z`. The latest observed consumer main CI is [37119254018](https://github.com/joku-dev/governance-framework-demo-consumer/actions/runs/37119254018), 3 October. | Successful CI is not a new accepted lifecycle receipt or a new current governance result. The projection remains limited to `governance-framework-demo-consumer` / `operation_readiness`, manual and report-only. |
| GRS-002 lifecycle pilot | The accepted repository pilot projection remains as of `2026-09-13T16:50:22Z`, with two receipts, no finding, no actions, and report-only enforcement. | This scope is separate from the demo-consumer lifecycle projection. Documentation readback does not refresh the pilot evidence. |
| Main protection | Live Ruleset `22622881` is active on `main`, requires one approval, CODEOWNER and last-push approval, resolved review threads and five required checks; force-push and deletion are blocked; `bypass_actors` is empty. | The live GitHub ruleset was read back on 9 October. No temporary bypass is active. |
| Open PRs | #244 is open against `main`, head `e57f67e`, base recorded as `411c038`, two commits ahead and six commits behind current main. #248 is an open draft documentation PR; #243 is a draft; #238 and #211 are also open. | PR #244 has passing reported checks on its existing head but needs synchronization and fresh checks; it still requires review. The current open-PR list is not approval to merge any PR. |

This readback updates the older pending-work summary below. It does not refresh
consumer evidence or lifecycle projections. Read the accepted indexes and
producer workflow records together; successful repository CI does not substitute
for a new consumer evaluation or intake.

## Historical 3 October Source Observation And Authoritative Sources

| Area | Observation at the source revision | Authoritative source for later checks |
|---|---|---|
| Separate consumer lifecycle | Operating acceptance confirmed/effective; `finding_state: closed`; 3 receipts and 4 action records; projection/evidence time `2026-10-03T10:58:04Z` | `status/governance-consumer-lifecycle.json` and `generated/reports/governance-consumer-lifecycle.md` |
| ha-CPsWMS container SBOM Trust | Run `36997124065`, attempt 2, accepted snapshot `2026-10-02T19-56-16Z-run-36997124065-sbom.json`: `provenance_verified`; same-commit paired baseline and custody checks pass; attestation remains unevaluated | `status/typed-evidence-results/`, the typed-evidence index and [Evidence Trust](../evidence/evidence-trust-model.md#ha-cpswms-container-evidence) |
| Main CI | Governance CI, CodeQL, Self-Security, Consumer Lifecycle Guard, latest Pages publication and Daily Operations succeeded | Latest GitHub Actions runs for the actual remote main commit |
| Main protection | Active ruleset, one required approval, CODEOWNER/last-push review, five required checks, no configured bypass; force-push/deletion blocked; signed commits not required | Live GitHub ruleset `22622881`, not only the desired configuration file |
| Self-security | [Run `37118684212`](https://github.com/joku-dev/devsecops-governance-framework/actions/runs/37118684212), observed `2026-10-03T11:08:18Z`: 8 pass / 8 fail (not evidenced). Two approvals and required signatures remain absent; other findings include unavailable settings/API access | Latest assessment artifact and its `observation.api_errors`; the versioned report still observes 19 September |
| Releases and pending work | Published adoption release remains `v0.2.0-public-adoption`; v0.3.0, repository SBOM export (#178) and Lifecycle Next Step (#200) remain open PRs | Published releases and reviewed merges; an open PR is not delivered capability |

## Changes After The 3 October Observation

The source-bound table above retains the 3 October observations at commit
`46b33429`; it is not a live claim about later merges. PR #200 subsequently
delivered the read-only Lifecycle Next Step viewer, and PR #178 delivered the
commit-bound repository SBOM export. PRs #96, #177 and #194 also merged after
that observation. Since then, PR #175 merged its v0.3.0 preparation assets, PR
#176 merged the private research prototype, and PRs #206–#208 completed and
verified the repository SBOM export fix. The published adoption release remains
`v0.2.0-public-adoption`; the v0.3.0 preparation has not been published as a
release.

The successful Self-Security job proves that the assessment ran, not that all
criteria passed. `None`/unavailable security settings are not proof of disabled
features. Do not substitute the older 14/16 versioned report for the fresh
artifact or manually rewrite generated reports to hide missing observations.
The two pilots remain manual and report-only. A closed demo finding and
`provenance_verified` evidence do not accept scanner risks or approve production.
For future observations, read the accepted indexes and live workflow artifacts
first; old source dates are not refreshed by rebuilding documentation.

## Historical September Reference

This page describes the implemented operating model as checked on 18 September
2026, including the live settings recorded by GCR-2026-094. The ha-CPsWMS
governance observations, measured/typed evidence and real staging evidence were
updated for its 18 September runs; other consumer observations retain their
individual dates. For
daily operation use the [operations handbook](../guides/governance-repository-operations-handbook.md).
For live observations use the latest main workflow artifacts and
[daily operations report](daily-governance-operations.md). A dated document or
successful workflow is not a current compliance attestation.

## Implemented Capabilities

| Layer | Implementation and responsibility |
|---|---|
| Governance sources | Approved sources and lineage in `docs/governance/`, `model/` and `architecture/`; candidates require recorded review before derivation |
| Executable governance | OPA policies, schemas, collectors and validators translate the approved model into evaluated evidence |
| Released baselines | DevSecOps `l1-baseline-v1.1.3`; architecture `architecture-baseline-l1-v0.1.0`; frozen packages under `releases/` |
| Accepted results | Append-only snapshots and digests, manifests, domain indexes and collection-attempt records under `status/` |
| Typed and measured evidence | Centrally verified vulnerability/SBOM snapshots, measured L1 assessments and conservative per-control assurance for ha-CPsWMS |
| Staging deployment evidence | Centrally verified approval, subject binding, image identity, runtime checks, security boundaries and recovery evidence for the isolated ha-CPsWMS staging VM |
| Intake telemetry | Append-only `status/intake-events/` feeds Intake Health, readiness and daily operating observations |
| Operational publication | Intake, portfolio and the manual lifecycle workflow propose scoped bot PRs; six publisher scopes; accepted state changes on protected main after checked merge |
| Closed-loop lifecycle | Personally accepted manual GRS-002 pilot; two real PASS receipts, no finding/actions; separate synthetic exception/scenario support |
| Status viewer and graph | Primary application under `generated/viewer/app/`, technical fallback at `generated/viewer/status-viewer.html` and governance graph; read-only projections |
| Documentation publication | `.github/workflows/publish-docs.yml` builds MkDocs strictly and deploys Pages, including generated assets |
| Self-security | Report-only assessment of this repository, independently of consumer governance results |
| Daily operations | `.github/workflows/governance-operations.yml`, daily 06:43 UTC and manual runs; summary and retained artifacts, no automatic alert delivery |

Normalized evidence is held in Git; original producer artifacts remain subject
to their retention settings and selected archival. The current pilot requires no
database. See the [storage model](../evidence/governance-results-storage-model.md)
and [backup procedure](../processes/governance-repository-backup-and-recovery.md).
This storage statement applies to the current low-volume pilot. The
[consumer-scale capacity assessment](../planning/consumer-scale-capacity-assessment.md)
shows that production operation with 300 to 1,500 consumers requires batched
intake, bounded read models and external immutable evidence storage.

## GitHub lifecycle update, 13 September 2026

The [current lifecycle state](governance-lifecycle-current-state.md) records personal
LD-07 acceptance on #91, activation via #92 and fresh evidence publication via #93.
The pilot is manual/report-only and limited to this repository's GRS-002/main.
It does not update consumer results, authorize live waivers or create a release.
Its accepted source profile remains pinned to Self-Security `0.2.0`; retained
receipts remain valid, while new `0.3.0` observations await a separately accepted
profile revision.
The [21-area function catalog](../guides/repository-function-catalog.md) and
[technical inventory](../guides/repository-technical-function-inventory.md) cover
both established capabilities and this addition.

## Protection And Enforcement

The live main ruleset was read back during GCR-2026-094 on 17 September 2026:
active, no bypass, one approving review, required CODEOWNER and last-push
approval, stale approval dismissal, resolved conversations, strict required
checks, and prohibited force pushes/deletion. The required GitHub Actions checks
are `validate-and-report`, `Analyze Python`, `Governance Repository Security`,
`Consumer Lifecycle Guard`, and `Dependency Review`. Configuration is versioned in
`.github/main-ruleset.json`; changing that file alone does not change GitHub.

The earlier #64/#67 exceptions and the maintainer-authorized technical CLG
merge exceptions, including #92/#93, restore the original ruleset after each
merge. The standing conversation authorization covers technical implementation
merges, not personal lifecycle decisions, live waivers or general operating authority.
Maintainer-authored PRs need another authorized reviewer under the normal rules.
See [self-security](../security/governance-repository-self-security.md).

New consumer pilots explicitly select `governance_mode: report-only` for all
triggers and architecture `fail_on_findings: false`. The released DevSecOps
wrapper still defaults to blocking if the mode is omitted. Copy the current
reviewed [adoption guidance](../../onboarding/public-repo-quickstart.md) and record
its revision separately from the frozen baseline pin.

The preexisting `ha-CPsWMS` blocking integration remains a recorded legacy risk,
with review due 12 December 2026, 23:59:59 Europe/Berlin. It does not authorize
new blocking. [Blocking alignment](blocking-mode-alignment.md) and the
[readiness assessment](blocking-readiness.md) explain the decision boundary.

## Accepted Mainline Results After Consumer Revalidation

The [13 September revalidation](../reference-runs/2026-09-13-consumer-revalidation.md)
refreshes diagnostic history for all three consumers and official mainline evidence
for the demo consumer after its operation-readiness preparation. The ha-CPsWMS
rows additionally show the accepted 19 September mainline runs:

| Consumer | Domain | Producer run | Recorded outcome |
|---|---|---|---|
| `ha-CPsWMS` | DevSecOps L1 | `35428988040` | `pass`; 16/16 applicable controls, 30 not applicable |
| `ha-CPsWMS` | Architecture L1 | `35428987695` | `pass`; 4/4 gates, zero findings |
| `ai-native-engineering-factory` | DevSecOps | `34503074356`, attempt 2 | `fail`; baseline gate reports direct pushes allowed |
| `governance-framework-demo-consumer` | DevSecOps L1 | `34778861276` | `pass`; one-gate fallback summary |
| `governance-framework-demo-consumer` | Architecture L1 | `34778861076` | `findings`; 25 findings across four gates |
| `governance-framework-demo-consumer` | Typed vulnerability evidence | `34778861276` | integrity and Freshness pass at verification; `integrity_verified` |

The Factory and demo-consumer DevSecOps snapshots summarize a baseline gate,
not a full control-catalog evaluation. Factory pins implementation commit
`31914e88b0669e0f6caed5bb9d0db71f762c2126`; the other two consumers use
`l1-baseline-v1.1.3`. Both architecture integrations use
`architecture-baseline-l1-v0.1.0`.

The accepted consumer commits are `dc303dcdabb36d4218b68dee5d1bbaf5eb3bc09c`
for ha-CPsWMS, `371251fe17c6923a810ab437a6c27fc7bfb624ed` for Factory, and
`915aeed2507ba3cc60fad5cd6a7b2415505a1ac9` for the neutral demo consumer.

Sources are the committed `status/repository-results-index.json`,
`status/architecture-results-index.json`, `status/typed-evidence-results-index.json`
and their immutable snapshots. The separately retained portfolio report at
14:37:35 UTC on 11 September contains three consumers and zero stale or missing
results at that assessment time; it was not refreshed by these individual intakes.
These timestamps describe observations, not a permanent freshness guarantee.

Trust remains separate from outcome: ha-CPsWMS DevSecOps has an open replay
finding despite its passing controls. All three consumers remain below the
Blocking Readiness bar. The neutral consumer now has current Typed Evidence
for its accepted mainline commit; that previously open gap is closed.

## Measured ha-CPsWMS Evidence And Staging, 19 September 2026

The separate successful mainline run
[`35428987714`](https://github.com/joku-dev/ha-CPsWMS/actions/runs/35428987714)
at commit `dc303dcdabb36d4218b68dee5d1bbaf5eb3bc09c` produced 54 passing source
tests, eight passing runtime integration tests, Bandit/Ruff results, five
container images, CycloneDX 1.6 SBOMs and Trivy 0.70.0 scan evidence.

Central intake verified the five complete image artifacts, image identities and
layers, SBOM and scan hashes, producer manifests, repository/run/attempt/commit
context and Freshness. The typed index records `integrity_verified` for both
vulnerability and SBOM evidence. It contains 749 SBOM components and 2,467
vulnerability observations across the five images, including one critical and
328 high image/package occurrences. These are findings for assessment, not an
automatic risk decision.

The measured L1 projection reports 9 controls as `measured`, 4 as `partial`, one
with `findings` and 2 as `gap`. The linked assurance snapshot covers all 16:
10 have complete coverage, passing Freshness and `integrity_verified`; 4 are
partial and 2 missing, leaving 6 `unverified`. Provenance, custody and attestation
are not promoted without their own proof.

The separately authorized deployment of the same application commit and measured
run to `ha-cpswms-stg-01` passed all 19 health, function, persistence,
controlled-outage, recovery, restart, image-identity and runtime-hardening checks.
Central intake verified the complete bundle hashes, approval, successful source
run and subject binding. Its Trust level is `integrity_verified`; L1-013 and
L1-014 are measured, while L1-016 is partial until durable event retention,
backup/restore, monitoring and incident ownership are implemented. The
consolidated result therefore has 11 measured, 4 partial, one findings and zero
gap controls. The API stayed bound to VM loopback and Neo4j had no host-published
port. This is staging-only, report-only evidence and does not grant production
approval or accept the scanner findings. See
[measured L1 evidence](../evidence/l1-measured-evidence-ha-cpswms.md),
[staging deployment evidence](../evidence/staging-deployment-evidence.md) and the
[Governance Workspace](../guides/governance-viewer-app.md).

## Central Operations And Remaining Findings

The current Intake Health projection at 19 September records 21 successful
events in its 30-day window, no failed or partial event, no open collection
attempt and two quarantined conflicts. This is intake telemetry, not proof that
all evidence is current or that every consumer is compliant.

Governance CI [35430841107](https://github.com/joku-dev/devsecops-governance-framework/actions/runs/35430841107),
CodeQL [35430841133](https://github.com/joku-dev/devsecops-governance-framework/actions/runs/35430841133),
self-security [35430841091](https://github.com/joku-dev/devsecops-governance-framework/actions/runs/35430841091)
and Pages [35430841090](https://github.com/joku-dev/devsecops-governance-framework/actions/runs/35430841090)
succeeded for the preceding viewer commit. The retained September Self-Security `0.4.0`
assessment records 14 passing and 2 failing criteria (one critical, one high).
Success means report generation and release-integrity verification worked; it
does not resolve the independent reviewer or signed-main-change findings.

The 17 September hardening closed the repository-level SHA-pinning and unrestricted
Action-source gaps and made Dependency Review mandatory. The corrected evaluator
also recognizes all reviewed PR publishers. GCR-2026-102 directly verifies the
signed operational-pilot tag and binds the three immutable historical tags to a
signed retrospective integrity manifest. Remaining findings are the second
independent reviewer and signed changes. Secret scanning, push protection,
Dependabot security updates, private vulnerability reporting and read-only
default workflow permissions remain enabled. Enhanced non-provider patterns and
validity checks remained disabled after an API enablement request and therefore
are not claimed as active. See the
[hardening record](../security/repository-security-hardening-2026-09-17.md) and
[self-security procedure](../security/governance-repository-self-security.md).

No permanent review bypass remains. Intake PRs #68–71 and portfolio PR #72 were
reviewed and merged normally after the explicitly scoped exceptions were restored.
Historical producer results, failed collection records and released packages remain
available. Regenerating a report cannot turn those records into a new evaluation.

## Remaining Pilot Work

The [handbook](../guides/governance-repository-operations-handbook.md) provides
concrete setup, daily triage and acceptance tests. Before accepting a test
operation, record named owners and reviewers, maintain fresh real consumer
results, verify credential recovery, and rehearse the selected backup scope.
The September evidence refresh completed collection and acceptance for the
existing three consumers; it does not by itself complete the organisational
pilot acceptance tests.

Procedures now exist for token maintenance and recovery. Their existence does
not mean an off-site backup, individual assignments or recovery targets have
already been commissioned. Independent missing-heartbeat alerting, stronger
release signing, broader platform validation and new L2/L3 releases remain
separate changes. Source replacement candidates still require recorded review.
