# GCR-2026-175 — Portable operations boundaries

Date: 2026-11-15. Status: implemented candidate for review; no live operations authority.

This increment follows GCR-2026-174 / PR #370. Classification under the [artifact intake process](../../operations/processes/new-artifact-intake-process.md): additive executable provider adapters, private Git workspace support, drift comparison, tests and integration documentation. It is not a normative source and changes no control, baseline or accepted result.

The new `portable_intake.operations` module separates SCM change proposals, CI dispatch and local Git. GitHub, GitLab and Bitbucket Data Center map native request/response shapes to one proposal contract. Existing/closed/merged requests are reconciled before mutation. Local commit bytes and timestamps are reproducible after scratch loss; candidate paths and remote branch scope are restricted. Credentials stay out of argv and URLs, redirects/hooks/ambient tracing are disabled. The new drift comparison includes configuration, IaC, GitHub actions and relevant root metadata without changing the legacy fingerprint function.

This implements provider boundaries for WP6 and part of WP7. It does not yet wire automatic discovery, the portable publisher's serial batch coordinator, systemd selection, state activation or capacity acceptance. Those remain dependent work. CI dispatch is an explicit library boundary and is never called by the existing shadow collector. A configured native plan/branch is required for Bamboo; variable overrides remain unsupported.

The existing CodeQL, Dependency Review and repository Self-Security workflows now run on PRs against dependent branches as well as `main`. Their previous main-only PR filters skipped these checks for the stacked portability increments. Analysis, job/context names, permissions, push/schedule behavior and branch-protection requirements are unchanged. No new required consumer check or blocking integration is introduced. The protected `governance-ci.yml` remains byte-identical.

Architecture governance, protected pilot files, released packages, current indexes and the existing VM installation remain outside this increment. The modules provide technical capability, not source authority, role bindings, human approval or merge/blocking permission. Review uses revision-bound coordinator role lenses and full repository validation; target versions and live provider acceptance remain open.
