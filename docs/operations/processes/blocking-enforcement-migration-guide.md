# Blocking Enforcement Migration Guide

## Purpose

This runbook describes how a single consumer can move from observation to a
blocking governance gate after the report-only readiness projection passes.
It does not authorize any current repository to change mode.

Before activation, confirm that the Blocking Mode Alignment report contains no
`unapproved_blocking`, `legacy_risk_incomplete`, or `legacy_risk_expired`
state. A preexisting `legacy_risk_active` record is migration debt, not an
activation precedent.

## Preconditions

1. Generate `generated/reports/blocking-readiness.json` from current mainline
   evidence.
2. Require `technical_ready: true` for the exact consumer.
3. Review every evidence reference and confirm the result is current.
4. Obtain named approval from Repository Owner, Governance Platform Lead,
   Security, and Release Manager; record the approved decision through a new
   GCR and reviewed model update, including the decision ID, approval time,
   approving roles, and evidence references.
5. Decide whether the target is `block-on-error` or `waiver-required`.
6. Verify the structured waiver path, expiry, authority, compensating controls,
   and emergency handling with representative passing and failing inputs.

## Staged Activation

1. Keep the existing workflow in `report-only` while collecting the configured
   stability and intake samples.
2. Introduce the prospective blocking configuration on a test branch or
   disposable consumer fixture.
3. Prove four cases: clean pass, genuine finding, valid waiver, and invalid or
   expired waiver.
4. Confirm the required check name is stable and cannot be bypassed by a renamed
   or skipped job.
5. Update the consumer workflow, branch rule, integration registry, GCR,
   release or migration notes, and demo documentation in one reviewed change.
6. Observe the first protected mainline runs and retain their evidence.

## Rollback

Rollback is consumer-scoped and requires an incident or change record:

1. capture the failing run, commit, policy version, baseline, and Trust state
2. preserve all failed evidence and collection history
3. temporarily restore the previous documented mode or remove only the newly
   introduced required-check binding
4. record owner, reason, expiry, compensating review, and restoration target
5. fix or revert the governance change through a PR
6. rerun all representative pass, fail, waiver, and bypass-resistance cases
7. reactivate blocking only with renewed accountable approval

Never delete historical evidence, silently weaken OPA rules, mutate a released
baseline package, or treat rollback as a permanent waiver.

## Release And Migration Boundary

A central report or internal readiness threshold needs no baseline release.
Changing a reusable consumer workflow, required input, evidence schema, or
released policy package requires versioning and migration review. Enabling a
required check also needs an explicit consumer change even when no baseline
artifact changes.
