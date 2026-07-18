# Management Readout

## Summary

The central repository `devsecops-governance-framework` is now operationally usable as an executable DevSecOps governance baseline.

The application repository `ha-CPsWMS` has been successfully integrated with this central baseline.

The governance check runs automatically through GitHub Actions and produces machine-readable compliance evidence.

An end-to-end proof has been successfully completed: artifact evidence, SBOM evidence, vulnerability evidence, and pipeline evidence were generated and evaluated by the central governance baseline.

This establishes a credible L1 minimum operational state for Governance as Code.

The current `main` line is green and includes the governance intelligence graph,
append-only evidence intake protection, persisted failed collection attempts,
controlled manual retry and lifecycle projection for those attempts, explicit
agent-to-evidence provenance, and a pinned validation toolchain.

The current demo consumer `joku-dev/governance-framework-demo-consumer` is also
clean on `main` at commit `60ff24cd94a010feb468aab9a48ac8ead4bf96ad`. Its CI,
DevSecOps Baseline, and Architecture Governance workflows completed
successfully in the latest push (`29603209364`, `29603210148`, and
`29603209915`). The `main` branch now requires pull-request review and rejects
direct pushes.

## Business Meaning

Governance is no longer present only as a document set. It is now implemented as a reusable and centrally managed control mechanism.

This means:

- governance requirements can be executed, not only described
- repository onboarding can follow a repeatable model
- evidence is produced in a machine-readable format
- compliance checks are easier to track and audit
- control logic can be improved centrally and reused across repositories

## Current Maturity

- L1 operational: achieved
- Pilot operation: possible
- Broader rollout: ready for preparation
- L2 and L3 maturity: not yet achieved

## Operational Outcome

The successful integration with `ha-CPsWMS` demonstrates that:

- an application repository can generate required evidence
- a central governance repository can evaluate that evidence
- a GitHub Actions workflow can enforce the baseline
- a machine-readable governance result can be stored as audit-relevant evidence

The central viewer now also provides separate report-only views for typed
Evidence Trust, Intake Health, the governance relationship graph, intake
conflicts, failed or
partial collection attempts, their derived `open`, `resolved`, or `permanent`
lifecycle, and explicit agent participation in Evidence reviews.

These views are projections of versioned JSON and do not replace the underlying
Evidence source, digest, custody, or attestation data.

Operators can retry an attempt only through the explicit `Retry Collection
Attempt` workflow and only when every recorded error is retryable. The original
append-only failure remains available for audit. A matching successful snapshot
resolves the operational collection failure without implying that the collected
governance outcome passed or changing the official `latest_result`.

Central intake workflows now also record a report-only operation event for
every successful or failed execution. This creates the measurement foundation
for future intake success-rate and latency reporting without changing results,
Trust, or enforcement. Historical runs are not inferred or backfilled.

The telemetry integration was smoke-tested across all three central paths on
2026-07-17. DevSecOps, Architecture, and Typed Evidence intake completed
successfully in runs `29613365725`, `29613411052`, and `29613460601`, recording
collection durations of 2, 3, and 2 seconds. No Collection Attempt was created
and the semantic latest-state projections remained unchanged. The test exposed
one legacy snapshot without an artifact digest; compatibility hardening now
accepts the otherwise identical enriched identity without weakening conflict
detection when two present artifact digests differ. The historical report-only
conflict remains available for audit.

Those events now feed a versioned, report-only Intake Health projection. Its
current 30-day observation contains three successful executions, no partial or
failed execution, p50 collection duration of 2 seconds, p95 of 3 seconds, no
Collection Attempts, and two retained append-only conflicts. These figures are
an operational observation rather than an approved SLO; they do not alter
Trust, governance outcomes, latest-state selection, or enforcement.
The viewer exposes the same committed projection with dimensional event counts
and latest-result age; it does not independently recalculate or reinterpret the
metrics.

For the consumer demo, the latest successful workflows use released baseline
references `l1-baseline-v1.1.3` and `architecture-baseline-l1-v0.1.0`. The
DevSecOps workflow produces the application, pipeline, and governance input
evidence; the Architecture workflow validates and uploads its release input and
governance evidence. Both remain report-only for the demo.

The earlier centrally re-verified Typed Evidence reference was run
`29432884108` from consumer commit `4ec2b2bd53560e010ebb1c078c4d3bd41b0bfcc6`:
Trivy `v0.70.0`, collector status `collected`, content integrity `pass`,
Freshness `pass`, and effective Trust `integrity_verified`. This is a separate
central intake projection and remains useful as the previous clean reference.

The latest consumer push is now centrally intaken. Its normalized DevSecOps
snapshot is `pass` with the branch-protection control satisfied, and its
Architecture snapshot is `findings` with 25 report-only findings after adding
reviewed compatibility, resilience, observability, and feedback evidence. The
latest Typed Evidence projection has zero scanner findings, passing content
integrity and Freshness, and effective Trust `integrity_verified`. The
DevSecOps governance projection also records a report-only replay finding
because the normalized control report digest was reused across runs; this does
not affect the Typed Evidence projection. These results are intentionally
visible in the central indexes and viewer; Architecture findings and replay
findings do not block delivery while the demo remains report-only.

This is the key proof point that the Governance-as-Code approach is operationally viable.

The central platform is also structurally ready for multiple consumers. A
deterministic readiness report validates three registered repositories, exact
DevSecOps registry coverage, consumer-specific result paths, portfolio
membership, scoped intake concurrency, telemetry identity, and Intake Health
dimensions. All nine checks pass. Architecture is currently present for two
consumers and Typed Evidence for one; optional evidence domains are not
fabricated for consumers that do not produce them.

The next Trust step is now proven as a report-only technical pilot. A signed
Ed25519 statement binds the demo issuer to the repository, commit, workflow run
and attempt, artifact, and exact evidence digest. All four pilot checks pass.
The result is intentionally only an `attested` candidate: operational Trust
remains `integrity_verified`, no consumer workflow or released baseline was
changed, and production issuer and key lifecycle approval remains open.

A versioned Blocking Readiness assessment now makes the enforcement gap
explicit without changing any repository mode. None of the three consumers
currently satisfies the stronger technical bar. The existing
`block-on-error` registration for `ha-CPsWMS` is flagged for review because it
predates the new Trust, Typed Evidence, replay, and operational-sample criteria;
the report does not weaken that existing gate. The demo consumer remains
correctly report-only due to `integrity_verified` Trust, one replay failure, 25
Architecture findings, only three intake events, and two retained conflicts.

The preexisting `ha-CPsWMS` Blocking mode is now governed by a separate
Alignment projection. Git history proves that the mode predates the stronger
readiness model. It is retained unchanged under an acknowledged, time-bounded
risk review until 18 August 2026; this is neither a new approval nor proof that
the activation satisfies today's criteria. Repository validation now rejects a
new Blocking registration without technical readiness and accountable approval,
as well as incomplete, orphaned, or expired legacy records.

## Current Constraints

The current state is intentionally limited to an initial L1 baseline.

The following items are still open:

- the demo now uses a real Trivy scan; a broader production scanner-adapter
  strategy and signed scanner attestations remain open
- branch protection evidence must be made fully reliable for L2 usage
- artifact signing must be introduced for L3 usage
- additional repositories and a second live telemetry-producing consumer
  should be onboarded to extend the current three-repository structural proof
  with a broader operational sample
- signed attestations, trust roots, and subject binding are technically proven
  in a report-only demo; production issuer approval, key lifecycle, producer
  emission, and operational Trust promotion remain open
- agent-to-Evidence provenance is available, but associations are currently
  recorded explicitly rather than inferred automatically
- the newest consumer workflow results and the centrally re-verified Typed
  Evidence snapshots are intentionally tracked by event type; manual reruns
  are recorded in history while the latest `push` remains the mainline pointer
- successful workflow completion currently coexists with report-only governance
  findings; this is expected while the consumer remains in report-only mode
- collection retries are deliberately manual; operation telemetry is now
  captured, while automated retry policies, health thresholds, retry budgets,
  and alerts are not yet enabled

## Recommended Next Priorities

1. Close the measured Blocking Readiness gaps, beginning with provenance Trust,
   replay resolution, Architecture findings, and a representative intake sample.
2. Complete the accountable `ha-CPsWMS` mode review before 18 August 2026 and
   record remediation, transition, or a formally approved exception.
3. Use Collection Attempt lifecycle, controlled retry, and provenance records
   in regular operational review and audit preparation.
4. Validate and operationalize branch-protection-based controls for L2.
5. Introduce artifact signing, trust roots, and related release controls for L3.
6. Onboard additional repositories using the same integration pattern.

## Executive Statement

Governance as Code is no longer only a concept in this environment. It is now operationally usable, centrally reusable, and technically demonstrable through a successful application repository integration.
