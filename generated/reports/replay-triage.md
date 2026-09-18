# Replay Triage Report

Generated from latest stored snapshot time: `2026-09-18T16:17:08Z`

## Summary

- Assessments: 50
- Stored replay failures: 7
- Failures under current report-only interpretation: 8
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
| `architecture` | `joku-dev/ha-CPsWMS` | `35351493524` | `pass` | `pass` | `new_evidence` | `none` |
| `devsecops` | `joku-dev/ha-CPsWMS` | `35351494433` | `fail` | `fail` | `cross_commit_reuse` | `reverify_with_artifact_digest` |
| `typed_evidence` | `joku-dev/ha-CPsWMS` | `35367212768` | `pass` | `fail` | `same_context_content_conflict` | `investigate_same_context_mutation` |

## Classification Counts

| Classification | Count |
|---|---:|
| `compatible_reuse` | 5 |
| `cross_commit_reuse` | 5 |
| `cross_repository_reuse` | 2 |
| `deterministic_report_reuse` | 6 |
| `legacy_assessment_superseded` | 2 |
| `new_evidence` | 27 |
| `same_context_content_conflict` | 3 |
