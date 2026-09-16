# Replay Triage Report

Generated from latest stored snapshot time: `2026-09-16T17:55:49Z`

## Summary

- Assessments: 40
- Stored replay failures: 5
- Failures under current report-only interpretation: 3
- Superseded legacy assessments: 2
- Official latest findings: 1

No historical snapshot, latest-result pointer, Trust level, or enforcement behavior is changed.

## Official Latest Assessments

| Domain | Repository | Run | Recorded | Current interpretation | Classification | Action |
|---|---|---:|---|---|---|---|
| `devsecops` | `joku-dev/ai-native-engineering-factory` | `34503074356` | `pass` | `pass` | `cross_repository_reuse` | `investigate_cross_repository_provenance` |
| `devsecops` | `joku-dev/ha-CPsWMS` | `34602002201` | `fail` | `fail` | `cross_commit_reuse` | `reverify_with_artifact_digest` |
| `architecture` | `joku-dev/governance-framework-demo-consumer` | `34778861076` | `pass` | `pass` | `new_evidence` | `none` |
| `devsecops` | `joku-dev/governance-framework-demo-consumer` | `34778861276` | `pass` | `pass` | `deterministic_report_reuse` | `none` |
| `typed_evidence` | `joku-dev/governance-framework-demo-consumer` | `34778861276` | `pass` | `pass` | `new_evidence` | `none` |
| `architecture` | `joku-dev/ha-CPsWMS` | `35131185047` | `pass` | `pass` | `new_evidence` | `none` |

## Classification Counts

| Classification | Count |
|---|---:|
| `compatible_reuse` | 5 |
| `cross_commit_reuse` | 3 |
| `cross_repository_reuse` | 2 |
| `deterministic_report_reuse` | 6 |
| `legacy_assessment_superseded` | 2 |
| `new_evidence` | 22 |
