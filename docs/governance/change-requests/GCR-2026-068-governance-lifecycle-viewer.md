# GCR-2026-068: CLG-06.2 Read-Only Synthetic Scenario Viewer

The maintainer authorized merging #81 with a one-time review exception and
starting the next CLG step. Base: `7f6c08540ff9e1f0dc39f98b59488344e07b06e4`.
CLG-06.2 implements the separately planned viewer over the CLG-06.1 overview.

| Field | Classification |
|---|---|
| Artifact types | Reporting generator/template, generated HTML, tests and operational documentation |
| Target paths | `scripts/generate_governance_lifecycle_viewer.py`, `scripts/templates/`, `generated/viewer/governance-lifecycle-viewer.html`, lifecycle validation/publisher, tests and docs |
| Owner/review lenses | Evidence/intake, demo readiness and repository stewardship |
| Source Document Intake | Not required; presentation of already accepted synthetic records, no normative source |
| Evidence contract impact | None; embeds the existing validated overview and its unchanged projection contracts |
| Runtime governance impact | Read-only, synthetic, report-only; no browser intake, approval or state transition |
| Release impact | None; consumer contracts and released baselines unchanged |
| Validation | Pinned full suite, strict MkDocs, deterministic HTML/payload and escaping tests, stale/forged publication tests, browser interaction and layout checks, accepted-prefix preservation |

The viewer presents one selected scenario at a time. Current finding state,
latest evidence, historical closure/reopening, work authorization and observation
coverage remain separate. Native selection/filter controls only affect what is
shown. No cross-scenario totals, production claims, live appointments or
accountable approvals are added; LD-01–05 and LD-07 remain open.

A standalone generated file embeds verified data and local CSS/JavaScript.
It needs no network, CDN, browser storage or LLM. Data is encoded safely and
rendered as text; an explicit Content Security Policy confines the page to its
own script and styles. The official consumer status viewer stays separate.

The synthetic closure publisher adds exactly this derived HTML path and checks
its equality to the verified overview before publication. It still cannot
publish exception history, profiles or consumer results. Documentation explains
regeneration order so an appended pilot event cannot leave the viewer stale.
