# CLG Live Pilot Preparation

The maintainer confirmed the three-role proposal on 13 September 2026 with
`ja ich bestätige`. [GCR-2026-071](../../governance/change-requests/GCR-2026-071-lifecycle-live-pilot-roles.md)
records the decision and classification. GitHub's public account lookup supplied
display name `joku`, login `joku-dev` and stable user ID `81616324`. The display
name is provider metadata, not a newly supplied legal name or authentication of
the conversation.

## Confirmed appointment

| Role | Appointed subject | Scope |
|---|---|---|
| Remediation decision and withdrawal | `github-user:81616324` (`joku-dev`) | GRS-002, this repository's `refs/heads/main`, pilot-only, report-only |
| Evidence-bound closure approval | Same person, separately recorded role | Same limited pilot |
| Role-binding administration and withdrawal | Same person, separately recorded role | Same limited pilot |

The maintainer explicitly confirmed the role combination. This is not independent
two-person approval and does not extend waiver authority or roles in other teams.
Codex prepares implementation and proposed records; personal lifecycle decisions
must be issued by the appointed person through the verified channel.

## Versioned preparation

`model/governance/lifecycle/live-pilot/role-bindings/00000001.json` records the
appointment, scope, conversation decision source and identity metadata separately.
`runtime_consent_proof: false` distinguishes appointment documentation from a
live approval of a remediation or closure.

Role changes and withdrawals append a new numbered revision with the complete
predecessor digest. A withdrawal removes all effective assignments in this
single-person pilot; the previous record remains intact. A later replacement
can restore or change assignments only with a new explicit appointment decision.
The validator checks references, scope, identity consistency and confirmed role
combination. It does not authenticate a human merely because a record is valid.
Live administration therefore still needs the personal-consent verifier.

`profiles/00000001.json` binds the exact role revision to a new **disabled live
preparation**. It pins the proposed Self-Security workflow, assessor, model,
report schema and dependency declaration to exact bytes at repository commit
`026e437fe2bab471e4c2c1eb3b01ad8105de4b1b`. These pins are technical verification
inputs, subject to the separate trust-root acceptance in LD-04.

All three activation flags are fixed false by the preparation schema. Freshness,
future skew and retention are explicitly unset. The synthetic profile and
accepted synthetic histories are unchanged. This preparation cannot be passed
to the synthetic runtime or activated by toggling a boolean.

`validate_governance_lifecycle_ledger.py` validates the current preparation during
full repository validation. Its accepted-prefix check additionally preserves
all already merged role/profile bytes. New revisions must form a complete
chain; the current profile must reference the latest role revision, including
withdrawal. No publisher path is added.

## Next implementation and acceptance

The [read-only evidence preflight](governance-lifecycle-live-evidence-preflight.md)
reads GitHub run/artifact metadata and exact report bytes, checks their binding
to the selected producer and source revision, and reports what was verified. It cannot accept live lifecycle observations while the
operating profile and acceptance decisions remain incomplete.

The selected personal GitHub statement channel still needs a verifier binding
identity, complete decision digest, expected Finding revision, disposition and
withdrawal. A merge, a bot action or a tool using the person's credentials cannot
stand in for a personal decision. The technical review exception continues to
apply to implementation PRs only.

The [decision sheet](governance-lifecycle-pilot-decisions.md) and
[live decision brief](governance-lifecycle-live-decision-brief.md) distinguish
confirmed appointments from the remaining trust, operating-policy and live
acceptance decisions. LD-05 values are not inherited from synthetic test constants.
