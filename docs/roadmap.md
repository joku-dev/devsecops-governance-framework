# Roadmap

Reviewed against `4abe88294f299d7f801c74ff0161df234960c092` on 11 September 2026.
This roadmap distinguishes implemented capabilities from remaining decisions.
The [current platform state](operations/status/current-governance-platform-state.md)
contains the dated evidence, and the [operations handbook](operations/guides/governance-repository-operations-handbook.md)
defines the controlled pilot procedure.

## Completed Technical Foundation

- 46 DevSecOps controls and their control-to-platform mappings are represented.
- DevSecOps L1 `l1-baseline-v1.1.3` and Architecture L1
  `architecture-baseline-l1-v0.1.0` are released.
- Three consumers have accepted mainline results from 11 September. Architecture
  is present for two and typed vulnerability evidence for one.
- Result snapshots, digests, manifests, append-only intake, conflict retention,
  replay triage, Trust verification and a signed-attestation pilot are implemented.
- Operational updates use reviewed bot PRs. Intake telemetry, controlled retry,
  portfolio, graph, viewer and readiness projections are available.
- Pinned validation, daily operations, self-security, documentation publication,
  backup/recovery procedures and management communication artifacts are available.

Implementation does not prove operating acceptance, enterprise compliance,
production Trust promotion or released L2/L3 readiness.

## Next Operating Work

1. Record pilot ownership, scope, dates and acceptance tests; keep consumer evidence
   fresh and review the daily report, including observation gaps.
2. Resolve the Factory direct-push finding, the neutral demo's 25 architecture
   findings and the ha-CPsWMS DevSecOps replay finding through new evidence.
3. Verify credential recovery, backups and agreed recovery scope. Introduce
   independent missing-report alerting only through a separately scoped change.
4. Collect representative intake samples. The second consumer already produces
   telemetry; broader samples and platform validation remain useful.

## Governance And Release Decisions

- Review candidate source replacement and verification requirements with the
  accountable source owners before deriving or replacing approved artifacts.
- Complete the ha-CPsWMS legacy-blocking risk review by 12 December 2026,
  23:59:59 Europe/Berlin. New pilots remain report-only. New blocking needs
  technical readiness, accountable approval and a separate consumer migration;
  currently none of the three consumers meets the readiness bar.
- Establish production issuer/key lifecycle and producer emission before
  promoting the signed-attestation pilot into operational Trust.
- Plan signed changes/releases, repository-wide SHA-pinning enforcement and
  approved Actions sources without rewriting historical released tags.
- Validate additional CI/CD platforms and decide future L2/L3 release scope.
- Decide long-term source-master and archival arrangements from actual operating
  needs. The current pilot does not require a database.
