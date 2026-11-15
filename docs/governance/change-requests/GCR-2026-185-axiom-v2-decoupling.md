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

## Product architecture documentation follow-up

On 15 November 2026 the maintainer designated V2 as the foundation for product
development and requested a complete architecture reconciliation in PR #395.
The central arc42 description now owns all twelve views, including actual module
locations, finite entrypoints, static provider composition, exact-source sparse
installation, fresh node/state boundaries and retained V1 operation. Context,
building-block and deployment SVG/Mermaid views describe the same implemented
structure. Future product work has explicit decision/exit-evidence boundaries;
it is not presented as delivered capability or production acceptance.

| Artifact classification | Effect |
|---|---|
| Explanatory system architecture and technical diagrams under `docs/governance/architecture/` | Documentation; product-development orientation, no normative source derivation |
| README, V2 implementation guide and technical Goal record | Navigation, architecture ownership and recorded delivery state |
| Evidence/schema/runtime/policy/baseline/authority impact | None; existing host/packages stay bound to their original implementation commits |
| Validation | Pinned bootstrap/full suite, strict docs, preserved section anchors/local links, rendered diagram review, protected fingerprint comparison and revision-bound coordinator review |

The technical architecture of the governance product is distinct from deriving
new Enterprise/Solution/Platform Architecture requirements. Those source/model
changes are not authorized or implied by this documentation follow-up.
