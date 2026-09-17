# GCR-2026-089: Explain and expose global Evidence Trust coverage

The maintainer clarified that the missing ha-CPsWMS entry concerns the global
Evidence Trust view and its Latest Typed Evidence table, rather than the
repository detail page. That global section previously showed only the typed
index, which currently contains the demo consumer.

Show official latest DevSecOps and architecture Trust in a separate table in
the same global view. Preserve the typed-only table and label its counters by
scope. Explicitly list governance repositories without a latest typed entry.
Do not manufacture typed records for measured L1 or container-security evidence.
Keep recorded Trust, Replay, latest selection and all historical data unchanged.

| Classification | Decision |
|---|---|
| Artifacts | Viewer generator/output, guide, evidence documentation, regression checks |
| Source intake | Not applicable: existing indexed evidence only |
| Contracts / policies / baselines | Unchanged |
| Governance effect | Read-only presentation, existing report-only Trust |
| Validation | Pinned full validation, strict docs, browser checks including global Trust |

Use the standing technical review exception after successful CI and restore the
original requirement. No independent human approval is claimed.
