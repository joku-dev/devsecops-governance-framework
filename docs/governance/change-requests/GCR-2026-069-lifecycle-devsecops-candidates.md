# GCR-2026-069: CLG-06.3a DevSecOps Input Candidate Adapter

The maintainer authorized continued implementation and merge with scoped review
exceptions until an accountable decision is indispensable. Base after #82:
`549ad5cac26d9c43a15089ba154e3d51159b87bb`.

| Field | Classification |
|---|---|
| Artifact types | Additive diagnostic input/output contracts, adapter/CLI, synthetic examples, tests and guidance |
| Target paths | `schemas/governance-lifecycle-*`, lifecycle library/CLI, `docs/examples/lifecycle-candidates/`, tests and lifecycle guides |
| Owner/review lenses | Governance analysis, DevSecOps baseline, evidence/intake and repository stewardship |
| Source Document Intake | Not required; existing producer results are represented without new normative requirements |
| Evidence contract impact | Additive candidate contract; no change to accepted lifecycle observations or released consumer contracts |
| Runtime governance impact | Read-only diagnostic preparation, report-only, never official or accepted lifecycle state |
| Release impact | None; no released baseline, control model, OPA behavior or consumer workflow change |
| Validation | Pinned full suite, strict MkDocs, producer/summary/context/digest/time/duplicate tests and rejection by accepted-observation contracts |

The DevSecOps adapter reads declared control results from the existing 1.0.0
control evaluation report. Policy summaries and free-text messages cannot create
additional control outcomes. `not_tested` and `not_applicable` remain distinct.
The adapter checks declared context and content binding but does not authenticate
a producer, resolve a baseline, establish freshness policy or approve intake.

Architecture gate adaptation follows in a separate PR. Live observation,
consent and role adapters still depend on LD-01–05 and LD-07; test approvals and
technical PR review exceptions do not resolve those decisions.
