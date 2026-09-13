# CLG-04 Read-Only Live Observation — 13 September 2026

Captured at `2026-09-13T08:51:05Z` from `joku-dev/devsecops-governance-framework`.
Local main was `75a983194576287dc6017d347630f1bad91d2457`, the merge of PR #78.
The explicitly authorized one-time review exception had been restored before
collection; the ruleset requires one approving review again.

The existing `scripts/assess_governance_repository_security.py` collected this
[schema 0.2.0 JSON report](2026-09-13-clg04-live-observation.json) read-only from
main, with output redirected to separate files. Raw report SHA-256:
`9ae28048e881a04fdcc6ad50570a61fce0fae04452d0b4224c8514bb74407e82`.

**GRS-002:** `pass`; `required_approving_reviews=1`. The overall assessment is
`findings` (12 pass, 4 fail): GRS-005, GRS-010, GRS-014 and GRS-016 remain separate
observed findings. The report retains the classic branch-protection API's 404
responses and the ruleset-based assessment; this is not a claim that every API
endpoint succeeded or every repository control passed.

This historical capture is neither synthetic evidence nor accepted live
lifecycle evidence. It has no lifecycle acceptance proof or human consent.
GRS-002 is already passing, so no real open finding or remediation was invented.
The [synthetic pilot](../../demos/demo-governance-lifecycle-pilot.md) demonstrates
the failure sequence separately. LD-01–05 and LD-07 remain open.
