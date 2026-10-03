# GCR-2026-111: Intuitive Viewer Reading And Verified Case History

The maintainer requests a more intuitive, professional Viewer: decision-oriented
entry points, understandable Trust labels, repository reading guidance and an
evidence-linked Closed-Loop case history.

| Classification | Decision |
|---|---|
| New artifacts | Read-only presentation helper, focused projection and browser tests; this change record |
| Source-document intake | Not required: no authoritative policy, directive, standard or role is introduced |
| Owner and path | Repository presentation layer: `apps/governance-viewer/`, `scripts/lib/viewer_experience.py`, Viewer guide and tests |
| Contracts | Additive optional `consumer_case` field in build output; no downstream evidence schema change |
| Acceptance | Published consumer state is compared with the existing validated ledger projection before presentation |
| Failure behavior | Missing or invalid case data displays unavailable; no invented zero or closure |
| Enforcement | Read-only; provenance filter is a reading aid, not a new mandatory Trust threshold |
| Release impact | No baseline, release package, accepted implementation fingerprint, history or personal consent changes |
| Existing PRs | Independent of #200's next-step guidance and #201's documentation refresh; shared files require normal merge/rebase review |

The case timeline is a display ordered by retained recording timestamps, not a
new lifecycle transition evaluator. Existing validators remain authoritative.
Age is shown as information, not recomputed policy freshness. Governance
results, scan findings, provenance and replay remain separate signals.

Validation includes the pinned full repository suite, strict MkDocs build,
JavaScript syntax, browser interaction at 390/720/1440 pixels, missing-data and
hostile-text cases, and source/generated asset parity. Optional local browser
acceptance runs use Playwright and a repository-root HTTP server.
