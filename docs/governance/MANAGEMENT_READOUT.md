# Management Readout

## Assessment

The framework supports a controlled test operation with reviewed evidence intake,
versioned DevSecOps and architecture baselines, and a published status viewer.
Three consumers have accepted results from 11 September 2026. These demonstrate
the integration and expose remaining findings; they are not a production or
enterprise-wide compliance approval.

Observation baseline: `4abe88294f299d7f801c74ff0161df234960c092`, 11 September
2026. The [current platform state](../operations/status/current-governance-platform-state.md)
records producer runs, consumer commits, operating observations and their limits.
The [operations handbook](../operations/guides/governance-repository-operations-handbook.md)
is the entry point for day-to-day work.

## Business Meaning

The framework connects approved requirements to repeatable technical checks and
traceable evidence. Teams can reuse the baseline and investigate why a finding
exists. Management can review evidence coverage, age and unresolved decisions
across consumers. Reduced review effort and shorter decision times are expected
benefits to measure in the pilot, not proven savings.

Human owners remain accountable for source approval, evidence quality, exceptions,
risk acceptance and enforcement. Neither a green workflow nor a generated report
makes those decisions automatically.

## Accepted Consumer Evidence

| Consumer | Evidence accepted on 11 September | Remaining interpretation |
|---|---|---|
| `ha-CPsWMS` | DevSecOps: 16/16 applicable controls pass; architecture: 4/4 gates pass, zero findings | Separate DevSecOps replay finding remains open; legacy blocking risk retained |
| `ai-native-engineering-factory` | Fresh mainline rerun, baseline gate `fail` | Direct-push allowance reported; report-only, one-gate summary |
| `governance-framework-demo-consumer` | DevSecOps gate `pass`; architecture has 25 findings; current typed vulnerability evidence is `integrity_verified` | Report-only; successful workflow execution does not clear architecture findings |

The portfolio reports **three consumers, zero stale or missing results** at its
11 September observation time. Coverage and freshness must be checked again when
making a later decision. **Zero of three consumers meet Blocking Readiness.**
A baseline-gate summary must not be presented as evaluation of all controls.

## Implemented Capabilities

- Source registration, candidate review briefs, lineage, impact and requirement deltas.
- Structured control and architecture models, schemas, OPA policies and released L1 baselines.
- Separate DevSecOps, architecture and typed-evidence intake with central Trust verification.
- Immutable snapshots, idempotent repeated intake, retained conflicts and replay triage.
- Failed-collection records, controlled manual retries and intake operation telemetry.
- Reviewed bot PRs for operational updates, portfolio reports, readiness projections,
  a read-only governance graph and static viewer.
- Model-neutral agent roles, adapters, deterministic routing checks and explicit
  agent-to-evidence provenance.
- Pinned validation, strict documentation publishing, repository self-security
  assessment and a daily report at 06:43 UTC.
- A signed-attestation technical pilot; operational Trust promotion and production
  issuer/key lifecycle approval remain separate work.

The data remains versioned in Git. A database or application server is not
required for the present pilot. Original producer artifacts need appropriate
retention and backup outside the normalized result history.

## Operating Conditions And Limits

New pilots explicitly use report-only for every trigger. Released DevSecOps
wrappers default to `block-on-error` if the mode is omitted. Architecture uses
`fail_on_findings: false` for the pilot. A Required Check alone does not enforce
absence of findings when its workflow remains report-only.

The preexisting ha-CPsWMS blocking registration is an acknowledged risk awaiting
review by **12 December 2026, 23:59:59 Europe/Berlin**. It is not an approval for
new blocking. New activation needs the readiness criteria, accountable approval
and a separate consumer change.

The central repository requires one approving review and strict checks on main.
The authorized one-off exceptions were restored. The bot cannot approve its own
proposals; maintainer-authored changes require another authorized reviewer under
the normal rule.

The latest recorded daily report is `attention`: consumer findings, the earlier
failed intake in the observation window, administrative observation limits and
self-security gaps remain visible. Four administrative hardening gaps were
confirmed: signed-change enforcement, repository-wide SHA-pinning enforcement,
signed release tags and restriction of Actions sources. Historical tags are not
rewritten as a documentation maintenance action.

## Next Decisions

1. Name the operating owner, deputy, reviewers and owners of open findings; record
   the pilot scope, duration, decision date and acceptance evidence.
2. Investigate Factory branch-protection evidence, the demo consumer's architecture
   findings and ha-CPsWMS replay provenance. Produce new evidence for remediation.
3. Exercise access recovery and the selected backup scope; maintain daily triage.
   Independent alerting for a missing report is still open.
4. Collect representative operating samples and close the remaining Trust and
   readiness gaps before proposing new blocking.
5. Complete the ha-CPsWMS risk review before its December deadline. Plan signing,
   approved Actions sources and production attestation as separately reviewed changes.

Broader platform validation and released L2/L3 adoption remain future work.
The [executive briefing](../publishing/executive-briefing/README.md) explains the
proposed introduction and how to evaluate its benefit.
