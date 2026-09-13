# Consumer revalidation — 13 September 2026

## Scope and execution

Revalidate the three existing GitHub consumers using their actual main commits,
then prepare one real architecture gate case for a future consumer lifecycle.
The initial five runs were manually dispatched; all completed successfully at
the workflow level. Governance findings remain visible separately.

| Consumer / domain | Fresh diagnostic run | Result |
|---|---|---|
| Demo / DevSecOps | [34778460821](https://github.com/joku-dev/governance-framework-demo-consumer/actions/runs/34778460821) | PASS, one released baseline gate; no full catalog claim |
| Demo / architecture | [34778462308](https://github.com/joku-dev/governance-framework-demo-consumer/actions/runs/34778462308) | 4 gates with 25 messages; operation readiness has 2 |
| ha-CPsWMS / DevSecOps | [34778464587](https://github.com/joku-dev/ha-CPsWMS/actions/runs/34778464587) | PASS, 14 applicable controls, 32 not applicable in diagnostic context; replay finding retained |
| ha-CPsWMS / architecture | [34778466282](https://github.com/joku-dev/ha-CPsWMS/actions/runs/34778466282) | PASS, 4/4 gates, zero findings |
| Factory / DevSecOps | [34778483411](https://github.com/joku-dev/ai-native-engineering-factory/actions/runs/34778483411) | FAIL, single baseline gate: direct pushes allowed on main; report-only workflow succeeds |

All are attempt 1, `workflow_dispatch`, branch `main`. Commits respectively:
`7d6a4f67c5e8441e1067405cc2da17218dc256fd`,
`6976bb2af2b9d47d2934273c444b6c9b62a81ea2`,
`371251fe17c6923a810ab437a6c27fc7bfb624ed`.
Baseline refs remain L1 `l1-baseline-v1.1.3` and architecture
`architecture-baseline-l1-v0.1.0`. The Factory uses wrapper commit
`31914e88b0669e0f6caed5bb9d0db71f762c2126`, internally bound to L1 v1.1.3.

## Central intake and interpretation

Existing intake CLIs ran locally using authenticated GitHub access. Two
architecture snapshots, three DevSecOps snapshots and one typed vulnerability
snapshot were appended. No GitHub-hosted intake operation event was fabricated
for these local invocations. The initial default artifact lookup for demo and
Factory was corrected to their documented `devsecops-pipeline-evidence` fallback;
no result was emitted by either failed lookup.

Each captured result reaches `integrity_verified`. Freshness passes at its recorded
verification time. Demo typed vulnerability evidence was independently verified
against the actual normalized report and application artifact. This does not
establish lifecycle acceptance or a general security PASS. ha-CPsWMS retains its
separate replay finding. The raw architecture baseline-resolution Trust check
remains `not_evaluated`; the diagnostic bundle separately retains the annotated
tag-to-commit resolution without modifying the recorded Trust assessment.

The manual runs remain history and do not replace official main-push results.
ha-CPsWMS official runs remain DevSecOps `34602002201` (16 applicable / 30 NA)
and architecture `34602001140`; the diagnostic run has 14/32 because release
controls are not applicable. Factory official evidence remains run `34503074356`,
attempt 2. The demo's initial official runs were `34606820493` and `34606820390`;
its meaningful remediation preparation creates subsequent mainline evidence.

## Mainline verification after the concrete preparation

Consumer PR #5 merged as `915aeed2507ba3cc60fad5cd6a7b2415505a1ac9`
(source commit `c21c6ee6c7ebb085901639c71feceff41ba45010`). All four PR
checks passed; branch review requirement was temporarily 1→0 and then restored
and compared with its previous configuration.

| Main-push workflow | Run | Result |
|---|---|---|
| CI | [34778860861](https://github.com/joku-dev/governance-framework-demo-consumer/actions/runs/34778860861) | Nine tests; three real function diagnostics pass; retained artifact `demo-runtime-diagnostics` |
| Architecture Governance | [34778861076](https://github.com/joku-dev/governance-framework-demo-consumer/actions/runs/34778861076) | Still 25 messages across four gates; operation readiness remains open with two messages |
| DevSecOps Baseline | [34778861276](https://github.com/joku-dev/governance-framework-demo-consumer/actions/runs/34778861276) | Released single baseline gate and separate typed vulnerability Trust revalidated |

The three corresponding central snapshots (architecture, DevSecOps, typed Trust)
replace only the demo consumer's official latest entries. Together with the six
initial diagnostic snapshots this change retains nine new evidence snapshots.
The manual history, other consumers' official state and historical results remain.
The exact CI artifact, provider metadata and a second reproducible gate-candidate
bundle are retained under the diagnostic bundle's `remediation-main/` directory.
These artifacts prove technical execution; none constitutes a personal approval
or accepted lifecycle receipt.

## Bounded remediation preparation

[Consumer PR #5](https://github.com/joku-dev/governance-framework-demo-consumer/pull/5)
adds the open action and actual CI-local function diagnostics. Nine unit tests
pass locally, including failure visibility and input rejection. Architecture
feedback/observability declarations remain `reviewed`, pending accountable
approval. This is non-deployed demo evidence; it does not assert production
observability or close the architecture finding.

The [decision brief](../evidence/consumer-lifecycle-operation-readiness.md)
selects exactly `operation_readiness` and defines the proposed roles, evidence
boundary, versioned admission work and eventual closure conditions. The existing
candidate CLI produces four diagnostic gate candidates from the actual source
report. None is promoted into the accepted lifecycle ledger. The accepted GRS-002
pilot, its two observations and every implementation fingerprint remain intact.

## Validation and publication

Required checks: pinned bootstrap/full validation, strict MkDocs, demo smoke,
exact candidate reproduction, source digest/context binding, official-latest
selection, retained history and accepted implementation fingerprints. Consumer
and central technical PRs use the maintainer's standing review exception while
retaining CI checks and restoring review protection immediately after merge.

Local verification completed: 470 tests pass (247.405 seconds); final-state
repository validation, strict MkDocs and end-to-end demo smoke pass. Both
candidate bundles reproduce exactly and match the intaken raw-report digests.
All 55 preexisting consumer snapshots, 29 lifecycle files and 143 release files
remain byte-identical. All accepted LD-07 implementation hashes match; a fresh
GitHub provider check confirms the personal operating acceptance remains effective.
Required central PR CI validates the final publication commit independently.
