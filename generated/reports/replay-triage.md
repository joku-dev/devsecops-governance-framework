# Replay Triage Report

Generated from latest stored snapshot time: `2026-09-11T13:02:37Z`

## Summary

- Assessments: 27
- Stored replay failures: 4
- Failures under current report-only interpretation: 2
- Superseded legacy assessments: 2
- Official latest findings: 1

No historical snapshot, latest-result pointer, Trust level, or enforcement behavior is changed.

## Official Latest Assessments

| Domain | Repository | Run | Recorded | Current interpretation | Classification | Action |
|---|---|---:|---|---|---|---|
| `architecture` | `joku-dev/governance-framework-demo-consumer` | `29603835105` | `pass` | `pass` | `new_evidence` | `none` |
| `typed_evidence` | `joku-dev/governance-framework-demo-consumer` | `29603835297` | `pass` | `pass` | `new_evidence` | `none` |
| `devsecops` | `joku-dev/governance-framework-demo-consumer` | `29636320472` | `pass` | `pass` | `deterministic_report_reuse` | `none` |
| `devsecops` | `joku-dev/ai-native-engineering-factory` | `34503074356` | `pass` | `pass` | `cross_repository_reuse` | `investigate_cross_repository_provenance` |
| `architecture` | `joku-dev/ha-CPsWMS` | `34602001140` | `pass` | `pass` | `new_evidence` | `none` |
| `devsecops` | `joku-dev/ha-CPsWMS` | `34602002201` | `fail` | `fail` | `cross_commit_reuse` | `reverify_with_artifact_digest` |

## Classification Counts

| Classification | Count |
|---|---:|
| `compatible_reuse` | 3 |
| `cross_commit_reuse` | 2 |
| `cross_repository_reuse` | 1 |
| `deterministic_report_reuse` | 3 |
| `legacy_assessment_superseded` | 2 |
| `new_evidence` | 16 |
