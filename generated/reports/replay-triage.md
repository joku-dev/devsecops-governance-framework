# Replay Triage Report

Generated from latest stored snapshot time: `2026-07-17T18:43:35Z`

## Summary

- Assessments: 18
- Stored replay failures: 3
- Failures under current report-only interpretation: 1
- Superseded legacy assessments: 2
- Official latest findings: 1

No historical snapshot, latest-result pointer, Trust level, or enforcement behavior is changed.

## Official Latest Assessments

| Domain | Repository | Run | Recorded | Current interpretation | Classification | Action |
|---|---|---:|---|---|---|---|
| `architecture` | `joku-dev/ha-CPsWMS` | `29415015294` | `not_evaluated` | `pass` | `new_evidence` | `none` |
| `devsecops` | `joku-dev/ha-CPsWMS` | `29415015878` | `not_evaluated` | `pass` | `new_evidence` | `none` |
| `architecture` | `joku-dev/governance-framework-demo-consumer` | `29603835105` | `pass` | `pass` | `new_evidence` | `none` |
| `devsecops` | `joku-dev/governance-framework-demo-consumer` | `29603835297` | `fail` | `fail` | `cross_commit_reuse` | `reverify_with_artifact_digest` |
| `typed_evidence` | `joku-dev/governance-framework-demo-consumer` | `29603835297` | `pass` | `pass` | `new_evidence` | `none` |

## Classification Counts

| Classification | Count |
|---|---:|
| `compatible_reuse` | 2 |
| `cross_commit_reuse` | 1 |
| `deterministic_report_reuse` | 1 |
| `legacy_assessment_superseded` | 2 |
| `new_evidence` | 12 |
