# ADR-PORT-001 — Shared portable pipeline runtime

- Status: implemented candidate; live acceptance and M2 pending
- Date: 2026-11-15
- Change request: [GCR-2026-173](../../governance/change-requests/GCR-2026-173-portable-runtime-m1.md)

## Decision

Add `scripts/governance_runtime.py` with `context`, `evaluate`, `gate` and `run`.
Keep provider environment/API access in adapters, and normalized contracts,
evaluation and gate mapping in provider-independent modules. Reuse the existing
control evaluator and checksum-verified L1 baseline's Rego. No control meaning,
released package or existing acceptance is changed by extraction.

The initial executable scope is the existing pipeline-L1 gate surface, with
explicit checks for missing native identity, unknown direct push, actual artifact
bytes, SBOM/scan binding and severity. Five mapped pipeline controls are assessed;
other L1 controls remain unevaluated, not automatically passed. Findings are
independent from execution and enforcement. Unknown required facts are incomplete;
OPA failures are technical errors. No provider gets a separate gate implementation.

Profile, context and result have versioned contracts. Baseline/package digest,
runtime digest and adapter version are separate. New identities bind canonical
provider instance and opaque native IDs; existing result-ledger keys are untouched.
The new schema does not upgrade historical evidence or authenticate consumer JSON.

## Compatibility and consequences

The candidate defaults to report-only and exposes no verified external merge
blocking. Existing released wrappers/generators and the 24 pilot fingerprints
stay intact. Unreleased GitLab echo/Bamboo placeholder templates are replaced by
calls to the shared runtime; adopting those new templates requires reviewed
profiles, real scanner output and prepared runtime tools.

The pure evaluator can run on Mac and Linux. The VM currently continues its
existing GitHub-only intake. Common verification, state migration, publishing,
VM rollout and large-repository capacity remain M2 work. No live system change
or release follows from this candidate PR. Operator-provided profiles/endpoints
must be trusted; missing platform/edition capabilities stay explicit.

## Addendum — integrated candidate

[GCR-2026-180](../../governance/change-requests/GCR-2026-180-portability-acceptance-and-recovery.md) records the subsequent shared verifier, durable provider-bound store, guarded proposal coordinator, VM compatibility/recovery, exact-source package, capacity evidence and additive issuer/subject/read-model contracts. The [integrated matrix](platform-portability-acceptance.md) supersedes the implementation-progress statements above; it does not replace historical source/release/acceptance records. Candidate indexes and private default-branch proof are separate from official latest results. Existing accepted GitHub ledger/publishers remain unchanged, and real operating authority is separately accepted.
