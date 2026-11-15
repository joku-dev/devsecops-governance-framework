# GCR-2026-185: AXIOM V2 provider decoupling

## Intent and classification

The maintainer requested autonomous implementation of the explicitly proposed
V2 version break on 15 November 2026. The root
`AXIOM_V2_Decoupling_Codex_Goal.md` records its scope and acceptance criteria.
This is an executable product architecture/operations change, not new normative
source material. No source-document registration or new control derivation is
implied. Existing policies, released baselines and accepted pilot fingerprints
remain protected.

## Implementation boundaries

Extract provider APIs/context/transport/proposal behavior into explicit adapter
modules. Route Workbench publication and portable services through the same
contracts. Separate neutral transport failures from GitHub authentication.
Inventory active V2 entrypoints and exclude V1-only execution paths from V2
distribution and import closure. Retain the prior installation for rollback;
use fresh private state, independent configuration and distinct service ports.

Runtime and verifier digests must include the actual adapter implementation.
Module movement alone must not weaken native identity, repository origin,
file/OPA recomputation, freshness, replay, shadow or publication safeguards.
Old accepted states are not silently rebound to the changed implementation.

## Validation and delivery

Require deterministic provider contract/architecture tests, unchanged-policy
regressions, the full pinned suite, strict docs and isolated Mac/Linux execution
with explicit source and dependency pins. Complete a revision-bound role review
packet before PR delivery. Missing provider editions/credentials remain specific
live boundaries. Report-only execution is the default; no productive publisher,
blocking gate, operating acceptance or source/baseline authority is activated.
