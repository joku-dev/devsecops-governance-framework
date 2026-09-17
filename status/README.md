# Governance Status Stores

This directory contains versioned operational evidence and deterministic
projections. Snapshots are append-only. Generators rebuild indexes and the
read-only viewer from validated records; operators should not edit indexes or
historical snapshots by hand.

| Store | Contents |
|---|---|
| `results/` | Accepted DevSecOps result snapshots. |
| `architecture-results/` | Accepted architecture runtime governance snapshots. |
| `typed-evidence-results/` | Centrally verified evidence by type, currently vulnerability scans and SBOMs. |
| `measured-security-results/` | Report-only normalized container vulnerability observations. |
| `measured-l1-results/` | Report-only, centrally recomputed L1 evidence assessments. |
| `control-evidence-assurance/` | Coverage, Trust, Freshness, replay, custody and attestation for every measured L1 control. |
| `collection-attempts/` | Failed or partial collection attempts and retry state. |
| `intake-events/` | Successful and unsuccessful intake telemetry. |
| `intake-conflicts/` | Quarantined conflicting payloads. |
| `evidence-agent-provenance/` | Explicit links between evidence and agent participation records. |

Top-level `*-index.json` files select official latest results according to their
documented domain rules. A later manual or pull-request run does not automatically
replace a mainline result. Evidence Trust remains separate from compliance
outcome, production approval and risk acceptance.

See `docs/operations/evidence/governance-result-intake-and-viewer-usage.md` and
`docs/operations/guides/governance-viewer-app.md` for intake and display rules.
