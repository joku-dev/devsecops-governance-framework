# Private state-bound authorization experiment — contract 1

Status: executable research design, authorized by the maintainer on 2026-09-20.
This is a non-normative prototype contract, not a released baseline or a patent
claim. Its classification and boundaries are recorded in GCR-2026-105.

## Scope and hypothesis

One synthetic consumer, one finding, one local POSIX filesystem, cooperating
writers, one controlled publication operation. A publication is an immutable
transaction containing the published artifact bytes/content; there is no
second external write that could escape the atomic transaction. The hypothesis
is that binding the complete request to independently specified history, state
and implementation commitments prevents use after a bound context changes.

All fixture evidence and fixture authorizations are labelled `test_fixture`.
The local fixture provider is an injectable test double, not identity proof.
No production action, repository protection change or accepted-pilot activation
is performed. A genuine personal statement is a separate, explicit demo step.

## Exact commitments

All roots use SHA-256 of the repository's canonical JSON: sorted string keys,
ASCII escapes, separators comma/colon, UTF-8, no newline. Only null, boolean,
integer, string, list and string-keyed object are admitted. Floating point,
NaN, duplicate JSON keys and unsupported values are rejected. Ordered ledger
entries retain order; revoked request IDs are sorted. Domain/version envelopes
are mandatory. Unicode is escaped, not normalized; integer and boolean differ.

* History: `{commitment_type: "prototype-history", version: "1", scope,
  transaction_count, head_ref}`. `head_ref` is null for an empty ledger,
  otherwise `{id, digest}` of the entire last transaction. All retained entries,
  including audit-only notes and revocations, are included. Replay validates
  every predecessor, sequence, ID, field and transition before computing it.
* State: `{commitment_type: "prototype-state", version: "1", scope, state}`.
  State contains exactly `revision`, `latest_evidence`, `publication`,
  `role_binding`, `profile`, and sorted `revoked_requests`. Evidence content,
  active artifact and subject/profile identity affect state. Audit-only notes
  do not increment the semantic revision. Report timestamps and formatting do
  not enter this projection. Thus two histories differing only in an audit note
  can yield equal state roots and different history roots.
* Implementation: `{commitment_type: "prototype-implementation", version: "1",
  files}`. `files` binds relative repository paths to raw-byte SHA-256 for the
  prototype Python files, the imported lifecycle library and result ledger,
  dependency locks/toolchain declarations, and the sandbox's implementation
  configuration. Its complete inventory is re-enumerated on every calculation.
  Added, removed and changed files alter the root. Symlinks are rejected.
* Request: exact version 1 and experimental scope, action body, H/S/I roots,
  full implementation manifest, subject, profile, role, expected sequence and
  history head. Its canonical digest binds every field. The action is exactly
  `publish_test_artifact` with a UTF-8 content string (bounded to 4096 bytes).

The sole supported write format is version 1; there is no old-format fallback
or change to historical production contracts. Roots are recomputed from the
ledger, never accepted from a viewer or cached projection.

## Execution and revocation

Preparation takes a coherent snapshot under the ledger lock. Publication takes
the same exclusive lock, rereads/replays the ledger, recomputes commitments,
checks subject/profile/provider status and the complete request, then publishes
one immutable transaction using the existing exclusive hard-link/fsync writer.
The artifact is embedded in that transaction. A retry must not produce another
artifact. Concurrent callers are serialized; a losing caller sees a stale root.

Publication bodies include a `human_capture` field. Automated trials store null.
The separate personal-demo command captures the existing GitHub statement
protocol twice under the lock, binds it to the entire prototype grant, and
retains the raw responses inside the transaction. A second complete context
read immediately before append rejects changes during provider verification.
The offline validator only establishes capture consistency; it cannot replace
a new provider fetch or certify physical human presence.

Only the test runner may select explicit ablations. Every ablated transaction
records the omitted checks and remains labelled experimental. No such switch
is connected to a production writer or consumer workflow.

Revocation appends an independent correction referencing the original request
digest and the designated subject. It does not require the original history
root to remain current. Previously published bytes remain retained; their
effective publication is cleared. Replay of an old grant cannot restore it.
Changing roles or profile also clears effective publication.

## Trust and technical limits

The lock protects cooperating local writers only. Code, OS, lock implementation,
provider identity verification and the verifier are trusted. Root equality does
not attest the loaded runtime, defend against a malicious administrator, prove
physical human presence or establish freshness. No distributed consensus,
hardware attestation, cloud deployment, arbitrary subprocess execution or
continuous provider monitoring is claimed. SHA-256 commitments alone cannot
detect a completely rewritten or truncated self-consistent ledger; a retained
trusted head/prefix is necessary. Evidence bundles include such reference data,
and verification can require an independently retained bundle digest.

No invented expiry or single-use capability-token contract is introduced.
The demonstrated duplicate-effect protection follows from atomic append and
the changed history precondition within this single ledger.

## Comparison and interpretation

Run the existing pilot's genuine context validator and operating-manifest check
on controlled inputs as comparison evidence. Do not portray its existing
head/revision/manifest safeguards as missing. Ablations isolate which checks
detect a perturbation and which are redundant. Equal rejection behaviour is
a valid result, not a novelty claim. Patentability and prior-art assessment are
outside this experiment's conclusions.

## Confidentiality and acceptance

Implementation, fixtures and dossiers live outside `docs/`, `generated/` and
`status/`; no automatic public-site integration. The branch stays private.
The original work package remains an unchanged working input. Existing
fingerprinted code, baselines and retained accepted history are read-only.

Completion requires real positive/negative filesystem experiments, two-process
contention, independent replay/checksum verification, ablation/comparison
results and full repository validation. Human provider verification, novelty,
inventorship and completeness of historical-disclosure inventory are separately
identified open items, never fabricated by the agent.
