# GCR-2026-088: Make repository Evidence Trust discoverable

The maintainer could not find Evidence Trust on the ha-CPsWMS repository page.
Existing values were only small summary fields and a portfolio-wide technical
view; the repository Evidence tab did not show them.

Add an explicit repository Evidence Trust tab and direct links from summary,
L1 evidence and evidence history. Present the existing indexed level, verification
time, check counts and Replay independently, with source snapshots. Missing Trust
must remain missing. Do not propagate governance Trust to measured L1 or container
evidence, change any status, infer freshness today or clear historical findings.

| Classification | Decision |
|---|---|
| Artifacts | Frontend, generated application, browser checks, guide |
| Source Document Intake | Not required; existing indexed evidence only |
| Contract / baseline / release impact | None |
| Governance impact | Read-only presentation; report-only Trust unchanged |
| Validation | Pinned full validation, strict docs, desktop/mobile browser acceptance |

Use the standing maintainer technical review exception for merge after checks;
restore the original review requirement. No independent human review is claimed.
