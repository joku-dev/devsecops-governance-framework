# Durable CLG Pilot Intake Validation

Current operating context: the separate [GitHub GRS-002 pilot](../status/governance-lifecycle-current-state.md)
is accepted after PRs #92/#93. This guide describes the scope of its own
contract or adapter; synthetic, diagnostic and preparation records retain their
original labels and do not independently authorize operation.

The maintainer confirmed the proposed operating profile with `ja` on
13 September 2026. [GCR-2026-073](../../governance/change-requests/GCR-2026-073-lifecycle-durable-pilot-intake.md)
records this decision. The immutable model is
`model/governance/lifecycle/live-operating/00000001.json`; it references the
previously confirmed role binding and the unchanged producer preparation.

## Confirmed policy

The first source remains a successful GitHub mainline push, first attempt, for
the pinned Self-Security producer. Evidence may be at most 86,400 seconds old
when newly admitted for pilot validation; future observations are rejected.
Complete raw evidence and references are retained during the pilot without
automatic deletion. Retention is reviewed at pilot completion. Identical
redelivery has no new effect; same-origin conflicting content is quarantined.
These are limited pilot operating values, not an enterprise SLA or retention rule.

## Durable receipt and projection

```bash
./scripts/bootstrap_validation_env.sh
.venv-validation/bin/python scripts/intake_lifecycle_pilot_run.py \
  --run-id 34759063986 --expected-sequence 0
.venv-validation/bin/python scripts/generate_lifecycle_pilot_validation.py
```

The example above is the initial intake. If that run already exists, re-intake
is an idempotent no-op. A different new run must use the current receipt count
as its expected sequence. The CLI retrieves provider evidence itself; it does
not import arbitrary local claims as authenticated observations.

`governance/lifecycle/live-validation/transactions/` stores complete capture
packages embedded as base64 in content-addressed JSON receipts. The original
archive, report, API responses, pinned source files, profile and manifest remain
available after the source artifact expires. Local append uses the existing
POSIX lock, fsync and exclusive hard-link publication primitive. A stale expected
sequence cannot advance the chain, including competing writers. Committed
receipts must preserve the full accepted Git prefix; there is no deletion command.

The generated `status/governance-lifecycle-live-validation.json` and
`generated/reports/governance-lifecycle-live-validation.md` are a separate
projection. Full replay regenerates each receipt from its exact captured bytes,
operating profile and predecessor, including quarantined data. A duplicate does
not add a receipt or renew freshness. A conflicting result with the same observed
time is quarantined as ambiguous even if it came from a different run.

PASS creates no artificial Finding. A later PASS does not close a previously
opened pilot Finding. Conflict state remains visible. This projection describes
pilot validation, with `official_state: false` and `live_activation_approved: false`.
It does not replace consumer indexes or the official viewer.

## Independent provider check before merge

Offline replay establishes consistency of retained bytes, not provider identity.
For each new receipt, required PR CI independently retrieves the selected GitHub
run/artifact/source again, compares origin and producer fingerprints, and applies
the confirmed age limit at PR acceptance. Existing accepted receipts are protected
by the immutable prefix and replayed offline; they are not refreshed or deleted
when their source artifact expires.

```bash
.venv-validation/bin/python scripts/validate_governance_lifecycle_ledger.py \
  --base-ref 81727b42ab60d2827865c234bac5ed929a9cb5fa --verify-new-provider
```

Governance CI adds read-only Actions permission and passes its token only to the
provider verification step. Technical review exceptions do not bypass the
required check. A stale unmerged proposal needs a new source run; changing its
claimed receipt time cannot make stale source evidence acceptable.

## Remaining boundary

The operating values and roles are confirmed. Receipts use `eligible_for_pilot`,
not operationally accepted lifecycle state. Personal consent verification and the
accountable live operating acceptance (LD-07) remain separate prerequisites.
The old synthetic profiles, transaction histories and disabled preparation are
preserved unchanged. Any live activation requires an explicit new runtime flow;
a preparation boolean cannot be toggled to bypass the remaining checks.
