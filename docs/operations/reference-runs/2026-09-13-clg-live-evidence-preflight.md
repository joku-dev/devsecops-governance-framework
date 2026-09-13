# CLG live evidence preflight — 13 September 2026

This is a dated diagnostic validation record, not live lifecycle admission or a
claim about current repository state. The confirmed pilot is GRS-002 on `main`
of `joku-dev/devsecops-governance-framework`, report-only.

| Field | Captured value |
|---|---|
| Source run | [34757612640](https://github.com/joku-dev/devsecops-governance-framework/actions/runs/34757612640), attempt 1, mainline push, successful |
| Source commit | `026e437fe2bab471e4c2c1eb3b01ad8105de4b1b` |
| Workflow | `governance-repository-security.yml`, ID `315792416` |
| Artifact | `governance-repository-security`, ID `10317798913` |
| Source profile | `governance-repository-self-security` version `0.2.0` |
| Observed at | `2026-09-13T12:37:58Z` |
| Captured at | `2026-09-13T12:57:39Z` |
| GRS-002 | `pass`, one required approving review in the captured observation |
| Archive SHA-256 | `ae4935b3b1169f401a222a06ff3ead6745a4a2e6d1505cbd727966a50484d108` |
| Report SHA-256 | `a67359232b130ccd0cc72f24ce0be7e0b4beaf5df800d9cc2a68a9f3f207b471` |
| Diagnostic checks | 10 passed; source digests, identities, context, archive and report consistency checked |
| Offline replay | Passed against the saved capture |
| Lifecycle acceptance | Not evaluated; no observation or Finding created |

The local capture was written outside repository status/history. This document
records its identity and validation result; it is not a durable custody store.
A later download depends on GitHub artifact availability, while the original
saved capture can be replayed without a network call. Provider metadata reported
artifact expiry on 12 December 2026; that is not an approved lifecycle retention
policy. Capture age was 1,181 seconds, with no approved freshness verdict.

The live integration test exposed and fixed an incorrect GitHub CLI hostname
argument: `gh --hostname` selects `github.com`, which resolves the official
`api.github.com` API endpoint. The successful capture and replay above used the
corrected adapter.

See the [operating guide](../evidence/governance-lifecycle-live-evidence-preflight.md)
for reproduction, scope and remaining acceptance decisions. Synthetic scenarios,
official consumer results and published baselines were not changed by this test.
