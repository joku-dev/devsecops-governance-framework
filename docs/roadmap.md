# Roadmap

Reviewed against `614380fe98b41a29aab2154f09fb4431f63b350a` and the
consumer-scale assessment on 19 September 2026.
This roadmap distinguishes implemented capabilities from remaining decisions.
The [current platform state](operations/status/current-governance-platform-state.md)
contains the dated evidence, and the [operations handbook](operations/guides/governance-repository-operations-handbook.md)
defines the controlled pilot procedure.

## Completed Technical Foundation

- 46 DevSecOps controls and their control-to-platform mappings are represented.
- DevSecOps L1 `l1-baseline-v1.1.3` and Architecture L1
  `architecture-baseline-l1-v0.1.0` are released.
- Three consumers have accepted mainline results. Architecture is present for
  two; typed vulnerability evidence exists for the neutral consumer and
  ha-CPsWMS, and typed SBOM evidence exists for ha-CPsWMS.
- Result snapshots, digests, manifests, append-only intake, conflict retention,
  replay triage, Trust verification and a signed-attestation pilot are implemented.
- ha-CPsWMS produces 54 real source tests and eight runtime tests, SAST, five container builds,
  CycloneDX SBOMs and Trivy scans. Central intake recomputes all 16 L1 evidence
  assessments and records per-control coverage, Trust and Freshness.
- Operational updates use reviewed bot PRs. Intake telemetry, controlled retry,
  portfolio, graph, the integrated Governance Workspace and readiness projections
  are available.
- Pinned validation, daily operations, self-security, documentation publication,
  backup/recovery procedures and management communication artifacts are available.
- A separate staging VM supplies deployment and runtime evidence for
  L1-013/014/016. The latest staging execution passed all 19 checks; the
  consolidated L1 result records 11 measured controls, four partial controls,
  one control with findings and no evidence gap.

Implementation does not prove operating acceptance, enterprise compliance,
production Trust promotion or released L2/L3 readiness.

## Accepted bounded lifecycle pilot

CLG-01–06.3 provides synthetic contracts, finding/action/closure/exception histories,
scenario reporting/viewer and diagnostic additional adapters. The real GitHub
GRS-002 pilot has personal LD-07 acceptance and successful manual publication
runs (#92/#93), with two PASS receipts and no actual finding or remediation.
See the [current lifecycle state](operations/status/governance-lifecycle-current-state.md).
The separate consumer operation-readiness pilot is implemented for the neutral
demo consumer with its own personal acceptance and action boundary. Live waivers,
other lifecycle consumers, a defined portfolio denominator, optional AI assistance
and a runtime release remain separate decisions.
Bitbucket Data Center/Bamboo implementation waits for actual company versions.

## Next Operating Work

1. Record pilot ownership, scope, dates and acceptance tests; keep consumer evidence
   fresh and review the daily report, including observation gaps.
2. Resolve the Factory direct-push finding, the neutral demo's 25 architecture
   findings and the two official-latest ha-CPsWMS replay findings through new
   evidence or a corrected typed-subject replay model.
3. Verify credential recovery, backups and agreed recovery scope. Introduce
   independent missing-report alerting only through a separately scoped change.
4. Collect representative intake samples. The second consumer already produces
   telemetry; broader samples and platform validation remain useful.
5. Re-run the consumer-scale diagnostic on the intended runner class and design
   the first production-scale evidence-plane increment: batched intake,
   partitioned viewer data and external immutable evidence storage. Use the
   [Consumer Scale Capacity Assessment](operations/planning/consumer-scale-capacity-assessment.md)
   as the canonical sizing and architecture record.

## Governance And Release Decisions

- Review candidate source replacement and verification requirements with the
  accountable source owners before deriving or replacing approved artifacts.
- Complete the ha-CPsWMS legacy-blocking risk review by 12 December 2026,
  23:59:59 Europe/Berlin. New pilots remain report-only. New blocking needs
  technical readiness, accountable approval and a separate consumer migration;
  currently none of the three consumers meets the readiness bar.
- Establish production issuer/key lifecycle and producer emission before
  promoting the signed-attestation pilot into operational Trust.
- Establish signed-change enforcement on `main` and test signer recovery.
  Release-tag integrity, repository-wide SHA pinning and approved Action sources
  are implemented; every future release tag must remain directly signed.
- Validate additional CI/CD platforms and decide future L2/L3 release scope.
- Decide long-term source-master and archival arrangements from actual operating
  needs. The current pilot does not require a database; a 300-to-1,500-consumer
  operating model requires an external evidence store and bounded read models.
