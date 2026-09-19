# Replay Triage Report

Generated from latest stored snapshot time: `2026-09-19T07:21:51Z`

## Summary

- Assessments: 56
- Stored replay failures: 8
- Failures under current report-only interpretation: 11
- Superseded legacy assessments: 2
- Official latest findings: 2

No historical snapshot, latest-result pointer, Trust level, or enforcement behavior is changed.

## Official Latest Assessments

| Domain | Repository | Run | Recorded | Current interpretation | Classification | Action |
|---|---|---:|---|---|---|---|
| `devsecops` | `joku-dev/ai-native-engineering-factory` | `34503074356` | `pass` | `pass` | `cross_repository_reuse` | `investigate_cross_repository_provenance` |
| `architecture` | `joku-dev/governance-framework-demo-consumer` | `34778861076` | `pass` | `pass` | `new_evidence` | `none` |
| `devsecops` | `joku-dev/governance-framework-demo-consumer` | `34778861276` | `pass` | `pass` | `deterministic_report_reuse` | `none` |
| `typed_evidence` | `joku-dev/governance-framework-demo-consumer` | `34778861276` | `pass` | `pass` | `new_evidence` | `none` |
| `architecture` | `joku-dev/ha-CPsWMS` | `35371297967` | `pass` | `pass` | `new_evidence` | `none` |
| `devsecops` | `joku-dev/ha-CPsWMS` | `35371298636` | `fail` | `fail` | `cross_commit_reuse` | `reverify_with_artifact_digest` |
| `typed_evidence` | `joku-dev/ha-CPsWMS` | `35428987714` | `pass` | `fail` | `same_context_content_conflict` | `investigate_same_context_mutation` |

## Classification Counts

| Classification | Count |
|---|---:|
| `compatible_reuse` | 5 |
| `cross_commit_reuse` | 6 |
| `cross_repository_reuse` | 2 |
| `deterministic_report_reuse` | 6 |
| `legacy_assessment_superseded` | 2 |
| `new_evidence` | 30 |
| `same_context_content_conflict` | 5 |
