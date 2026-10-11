# ADR-WB-001 — Protected source-review operational surface

- Status: implemented for local maintainer review; enterprise hosting deferred
- Date: 2026-10-11
- Change request: [GCR-2026-148](../../governance/change-requests/GCR-2026-148-governance-review-workbench.md)

## Problem

Source intake spans a register, source extraction, requirement deltas, owner
review, DCR and baseline readiness. The public static viewer explains the
result but cannot safely accept private documents or record operational drafts.

## Decision

Add a separate authenticated loopback web application in this same repository.
Reuse the source register, extractors and readiness projection; do not create
another authoritative register or reimplement normative governance logic.
Use standard-library HTTP and the existing pinned validation dependencies.
Keep source uploads, review packages and proposals under an ignored private
local directory. Version the local draft schema, not private runtime drafts.

Publish source candidates only through an explicitly invoked platform adapter
or inspectable ZIP package. GitHub CLI is an optional adapter, not a core
architecture dependency. Candidate PRs preserve historical sources and keep
`status: candidate`, `supersedes: null`, and empty derived artifact areas.
Report-only decisions, semantic-run authorization and normative approval stay
outside the application. Notes are proposals and cannot establish authority.

## Consequences

The application is immediately usable against a checkout without an external
server account, cloud storage, browser Git token or additional database.
An isolated publication worktree preserves the maintainer's working checkout.
Hash binding rejects stale proposals and exports.

This first implementation serves one local maintainer. It is not enterprise
SSO/RBAC or a publicly hosted multi-user app. Enterprise deployment, individual
reviewer identity, durable shared storage, job orchestration, provider-run
contracts and formal decision admission need separate implementation and
operational decisions. No public source upload endpoint is added to Pages.
Existing redacted DCR findings remain redacted; no unseen evidence is fabricated.
