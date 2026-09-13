# GCR-2026-067: CLG-06.1 Synthetic Lifecycle Reporting

The maintainer authorized merging #80 with a one-time review exception and
starting the next CLG package. Base: `edf123add3720a4e5078982e31223aee40d81e89`.
This first bounded CLG-06 step makes the existing synthetic pilot histories
inspectable together at one explicit evaluation instant.

| Field | Classification |
|---|---|
| Artifact types | Additive reporting schema, deterministic generator, generated JSON/Markdown, tests and guidance |
| Target paths | `schemas/`, `scripts/`, `status/governance-lifecycle-overview.json`, `generated/reports/governance-lifecycle-overview.md`, `tests/`, lifecycle documentation |
| Owner/review lenses | Governance analysis, evidence/intake, release management and repository stewardship |
| Source Document Intake | Not required; derived reporting of accepted synthetic records, no new normative source |
| Evidence contract impact | Additive synthetic overview; existing intake and immutable record contracts unchanged |
| Runtime governance impact | Report-only, read-only replay; no new decision or finding transitions |
| Release impact | None; no released baseline, consumer migration or enforcement change |
| Validation | Pinned full validation, schema and replay checks, explicit-time boundary and tamper tests, strict MkDocs, accepted-prefix check |

The three histories reuse the same synthetic finding identity. Each is a
separate scenario, never a portfolio repository or an additional production
finding. Metrics distinguish accepted observations, quarantine, historical
closure/reopening events and current state. Exception coverage and work progress
remain separate. The generator uses no mutable source indexes, wall clock,
network or LLM. The normal repository validation rejects stale or altered
checked-in overview output.

The CLG-06 backlog is split in the implementation plan before implementation:
reporting first, then a separate read-only viewer, individually scoped adapters,
portfolio metrics after compatible live profiles, and optional AI assistance.
The existing synthetic closure publisher additionally carries only the two
new overview outputs and verifies their replay before publication. New ledger
domains, profiles, exceptions and consumer paths are not added to its scope. LD-01–05 and LD-07 remain open;
fixture roles and consent are not live authority or accountable acceptance.
