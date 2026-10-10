# Golden Path PRA Capability Workpackage

Status: **planning baseline; implementation and compliance not asserted**
Basis: approved [PRA source](../../governance/source-documents/PRA-STD-SRC-001.requirements.md)
and [decision GCR-2026-147](../../governance/change-requests/GCR-2026-147-pra-first-wave-decision.md); Golden Path direction
confirmed by the maintainer on 10 October 2026.
Change classification: [GCR-2026-148](../../governance/change-requests/GCR-2026-148-golden-path-pra-capability-workpackage.md).

The approved recommendation is maintained in
[`PRA-2026-001`](../../governance/review-packets/PRA-2026-001/recommendation.md).

## Purpose

Use the developing Golden Path as the common platform target for capabilities
that help programs implement and evidence their applicable DSCB requirements.
The Golden Path is intended to support the approved DSCB scope. This plan does
not claim that the planned or current platform already provides those
capabilities, or that a program using it is automatically compliant.

Programs select and configure platform capabilities for their applicable
baseline, use them in delivery, and retain evidence. Other platforms may remain
in use during transition; they need their own evidence of equivalent support or
a separately approved exception.

## Guardrails

- Use only the approved PRA requirements and GCR-2026-147 as the authority for
  this gap analysis. The registered `TOOLCHAIN-ARCH-CAND-001` remains a source
  candidate; this workpackage does not derive requirements from it.
- Keep the 18 deferred PRA proposals open until implementation and evidence are
  reviewed and a versioned governance decision authorizes a status change.
- Derive required platform levels from the applicable approved DSCB baseline.
  Do not invent retention periods, exception authorities, or production policy.
- Do not change OPA behavior, enforcement mode, evidence contracts, released
  baselines, or consumer workflows under this workpackage.

## Capability and evidence backlog

The closure evidence below is a proposed acceptance basis for Golden Path
design and implementation review. It is not an effective platform mapping.

### Partial coverage: 12 requirements

| PRA source | Golden Path capability to design or complete | Evidence for closure review |
|---|---|---|
| REQ-007 | Identify approved developer environments and govern their use. | Approved environment catalog, provisioning/configuration controls, and a representative program use. |
| REQ-014 | Control and audit pipeline execution contexts. | Runner image/configuration and isolation settings bound to run identity, revision, and retained logs. |
| REQ-016 | Integrate required security scans into delivery pipelines. | Versioned workflow configuration plus successful run artifacts showing scanner, target revision, and results. |
| REQ-017 | Make supply-chain integrity controls composable across artifacts. | One artifact-bound chain covering dependency/SBOM data, provenance, signing or verification, and integrity results. |
| REQ-018 | Automate security and compliance checks where technically feasible. | Check catalog, automated execution evidence, and reviewed rationale for any feasibility exception. |
| REQ-019 | Route releasable artifacts only to approved repositories. | Approved repository inventory and release records binding artifact identity to repository and version. |
| REQ-021 | Control and monitor dependency repositories. | Approved source/proxy configuration, monitoring coverage, and alert or audit evidence for a representative dependency flow. |
| REQ-027 | Produce evidence usable by internal and external audits. | A traceable sample audit package with source, control, run, artifact, retention, and retrieval references. |
| REQ-038 | Prevent a platform from declaring a level below its programs' requirement. | Required-level derivation, platform declaration check, and a negative test that rejects a lower level. |
| REQ-049 | Preserve mandatory capabilities when a variant adds restrictions. | Variant-to-capability comparison and tested waiver linkage for any proposed removal. |
| REQ-053 | Require governance-board approval for baseline-affecting platform changes. | Change impact trigger, authorized approver/decision record, and a test showing an unapproved change cannot be promoted. |
| REQ-055 | Prevent production approval for non-compliant platforms unless formally waived. | Production readiness decision path, linked compliance results, formal waiver handling, and negative/positive decision tests. |

### No confirmed implementation: 6 requirements

| PRA source | Golden Path capability or clarification needed | Evidence for closure review |
|---|---|---|
| REQ-001 | Define measurable properties for controlled, repeatable delivery across programs. | Repeatable onboarding and release evidence from representative programs using the same declared platform contract. |
| REQ-002 | Clarify which quoted version is authoritative and how consumers must use it. | Approved version source, version pinning/update process, and a conformance check for a representative program. |
| REQ-003 | Define domain-specific platform variants and their conformance boundary. | Variant inventory, common architecture profile, and conformance results for each supported variant class. |
| REQ-030 | Establish applicable retention obligations before selecting technical retention behavior. | Owner-approved retention schedule, configured storage/lifecycle controls, and retrieval/deletion evidence. No duration is assumed here. |
| REQ-048 | Derive minimum PRA level for classified, air-gapped, and restricted variants. | Program-to-variant level assignment and tests that reject a variant below the required level. |
| REQ-051 | Define and test logical architecture equivalence across variants. | Versioned architecture profiles for variants and an automated or reviewed equivalence assessment with deviations recorded. |

## Delivery sequence

1. **Scope:** Platform Owner names Golden Path owner, supported DSCB levels,
   program classes, platform variants, and the authoritative design inputs.
2. **Design:** Platform Engineering and DevSecOps Baseline owners map each PRA
   requirement to a platform service, implementation owner, and acceptance
   evidence. Security, Governance, and Records owners resolve requirements
   needing authority or retention decisions.
3. **Build and test:** Implement the capabilities and representative positive
   and negative conformance tests. Keep test results bound to platform version
   and source revision.
4. **Review and authorize:** Review real implementation evidence against the
   approved PRA. Propose any requirement or platform mapping change through a
   separate versioned governance decision. Keep report-only behavior unless a
   separate scoped decision authorizes blocking.
5. **Adoption:** Programs declare the platform version and applicable level,
   enable the required services, and submit program-bound evidence. Existing
   non-Golden-Path platforms follow an explicit equivalence or migration path.

## Open decisions

- Which DSCB levels and program classes must the initial Golden Path release
  support?
- Which platform variants are in scope, and who owns each variant?
- Which approved source will define version authority, exception authority,
  production approval, and retention obligations?
- Which evidence can be generated centrally by the platform, and which remains
  the responsibility of each program?
- What transition date or migration criteria apply to existing platforms?

## Completion condition

This workpackage is ready for implementation planning when the open decisions
above have owners and the 18 rows have assigned capability owners, target
levels, and reviewable acceptance tests. No row is considered implemented until
the relevant platform version has passed its tests and the evidence has been
reviewed under an authorized governance decision.
