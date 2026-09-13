# GCR-2026-072: Read-Only Live Evidence Preflight

Continues the confirmed pilot implementation after the role/profile preparation.
The maintainer authorized the limited role arrangement, personal GitHub decision
channel direction, Self-Security source implementation and technical PR review
exceptions. This change makes source verification concrete before operating
policy and live acceptance are decided.

| Field | Classification |
|---|---|
| Artifact types | Read-only GitHub collector, captured-evidence consistency verifier, diagnostic CLI, tests, operating guide and dated run reference |
| Target paths | Lifecycle library/CLI, tests, lifecycle evidence guide and operations reference runs |
| Owner/review lenses | Evidence/intake, governance analysis, release management and repository stewardship |
| Source Document Intake | Not required; no new normative source or mandatory policy |
| Evidence contract impact | Separate diagnostic capture contract; no accepted lifecycle observation |
| Runtime impact | Read-only API requests and local diagnostic snapshots; no state, settings, publisher or workflow writes |
| Release impact | None; producer/OPA/baselines/enforcement unchanged |
| Validation | Pinned full suite, strict MkDocs, offline negative tests, actual API/artifact capture, replay and accepted-prefix check |

The verifier binds the exact repository, successful mainline push, selected
workflow and artifact to captured GitHub metadata. Raw archive integrity and
pinned source files are checked. GRS-002 is taken from one explicit criterion,
checked against the recorded review count and original source model. Mainline
run attempt 1 is the initial supported scope; reruns are rejected because the
available artifact metadata does not independently identify their attempt.

Outputs remain diagnostic and not evaluated for lifecycle acceptance. Offline
replay establishes captured-data consistency, not independent provider
authentication. The report retains source API errors and does not infer that
branch protection held at every instant of a commit. Operational freshness,
retention, durable live replay, personal consent and live acceptance remain open.
