# Portfolio Adoption Reporting

## Purpose

Portfolio-level adoption reporting shows how multiple consuming repositories are adopting the central DevSecOps and architecture governance baselines.

It answers four management questions:

- Which repositories are in scope?
- Which repositories have adopted the approved baselines?
- Which repositories have current accepted passing results?
- Which repositories need governance-owner attention?

The machine-readable reporting model lives in:

```text
governance/portfolio-adoption-reporting.yaml
```

## Reporting Sources

Portfolio reporting uses normalized result indexes:

```text
status/repository-results-index.json
status/architecture-results-index.json
```

Repository-specific snapshots remain under:

```text
status/results/
status/architecture-results/
```

The report must distinguish accepted portfolio evidence from operational noise. Pull-request, branch, diagnostic, and experimental runs can help explain adoption progress, but they must not change portfolio status unless a governance owner explicitly accepts them.

## Adoption States

| State | Meaning |
|---|---|
| `not_onboarded` | Repository is known but has no approved governance integration. |
| `onboarded` | Repository has an owner, target baseline, and onboarding record. |
| `pilot` | Repository runs governance checks in report-only or pilot mode. |
| `adopting` | Repository has accepted governance checks and is closing gaps. |
| `active` | Repository has current accepted passing results for applicable baselines. |
| `exception` | Repository operates under an approved waiver or temporary exception. |
| `retired` | Repository is no longer in active governance scope. |

## Portfolio Metrics

| Metric | Definition |
|---|---|
| Repository coverage | In-scope repositories with an onboarding state. |
| Baseline adoption rate | In-scope repositories pinned to an approved baseline. |
| Current pass rate | Active repositories with latest accepted passing results. |
| Stale result rate | Active repositories whose accepted result is older than the freshness threshold. |
| Exception rate | In-scope repositories operating under approved waiver or exception. |
| Architecture governance coverage | Architecture-in-scope repositories with accepted architecture governance results. |

Default freshness threshold:

```text
30 days for ordinary portfolio reporting
14 days for release-relevant reporting
```

## Repository Matrix

Each portfolio report should include a repository adoption matrix with:

- repository id
- owner
- business or product area
- adoption state
- target DevSecOps baseline
- latest DevSecOps result status and date
- architecture governance scope
- target architecture baseline
- latest architecture result status and date
- open waiver count
- stale or missing result flag
- next action
- action owner

## Reporting Cadence

| Review | Cadence | Audience |
|---|---|---|
| Operational review | Biweekly | Platform and repository owners |
| Governance board review | Monthly | DevSecOps Governance Board and related governance bodies |
| Executive summary | Quarterly | CDO and executive stakeholders |

## Quality Rules

1. Portfolio status must be based on accepted mainline, release, or explicitly accepted manual results.
2. Pull-request and branch results must not be promoted to portfolio adoption status without explicit acceptance.
3. Every in-scope repository must have an owner.
4. Every open adoption gap must have a next action and action owner.
5. Every onboarded repository must declare its target baseline.
6. Missing or stale results must remain visible.
7. Exceptions must include a waiver or review date.

## Operating Flow

1. Maintain the repository inventory and integration state.
2. Intake accepted downstream governance results.
3. Regenerate central result indexes.
4. Apply the portfolio reporting model.
5. Review stale, missing, failing, or exception-based adoption states.
6. Record next actions and owners.
7. Present summary metrics to the required governance forum.

Use:

```bash
python3 scripts/generate_portfolio_onboarding_status.py
python3 scripts/generate_repository_results_index.py
python3 scripts/generate_architecture_results_index.py
python3 scripts/generate_status_viewer.py
```

The portfolio generator writes `generated/reports/portfolio-onboarding-status.json`
and `.md`. It uses only registry entries and accepted latest index projections;
it does not approve waivers or change enforcement modes.

## Decision Boundaries

Portfolio adoption reporting is evidence for governance decisions. It does not approve waivers, change baselines, or promote a repository to active status by itself.

The DevSecOps Governance Board remains accountable for adoption interpretation. Repository owners remain accountable for repository-specific remediation and evidence freshness.
