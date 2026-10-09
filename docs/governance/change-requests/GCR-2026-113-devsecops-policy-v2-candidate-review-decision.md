# GCR-2026-113: DevSecOps Policy v2 Candidate Review Decision

## Decision Status

**Human intake decision recorded on 8 October 2026: keep the Policy v2 document
as a candidate.** This does not confirm it as a replacement, promote it to an
approved source, or authorize derivation.

## Summary

- Retain `DEVSECOPS-POL-CAND-002` with `status: candidate`.
- Keep the tracked `DEVSECOPS-POL-SRC-001.requirements.md` version as the
  authorized current policy source.
- Defer the replacement decision until the candidate's provenance, owner,
  approval status and claimed change marking are confirmed.
- Make no changes to controls, policies, runtime governance, schemas, or
  released baselines from the candidate.

## Source Document Intake

| Field | Value |
|---|---|
| Candidate | `DEVSECOPS-POL-CAND-002` |
| Candidate path | `docs/governance/source-documents/DevSecOps_Policy_Review_Integrated_v2_CHANGE_MARKED.md` |
| Existing source | `DEVSECOPS-POL-REQ-001` |
| Existing source path | `docs/governance/source-documents/DEVSECOPS-POL-SRC-001.requirements.md` |
| Existing source authority | Maintainer-confirmed authorized version tracked in Git; unchanged at review snapshot `a8fc36f3de7f33cd2a26dff94f9a28985e78d64f` |
| Decision owner | Human reviewer; governance role not asserted by this record |
| Decision date | 2026-10-08 |
| Similarity assessment | `replacement_candidate` |
| Decision | Keep candidate; replacement review remains open |
| Derived artifacts allowed | No |

This change request records an intake decision. It does not change the source
text or register status, and does not authorize a full-source replacement.

## Review Findings And Open Conditions

- The current requirements extract is the authorized comparator. The candidate
  is a full policy document while the comparator is a sanitized
  requirements-only extract, so automated delta counts are discovery aids and
  do not by themselves establish semantic equivalence or replacement.
- The candidate filename says `CHANGE_MARKED`, but the reviewed Markdown does
  not identify the changed passages or provide a change-marking legend.
- Applicable document references include `NA` and `TBD`; referenced standards
  are described as “to be established” or “in progress”.
- The text makes formal authorization the condition for entry into force, but
  this intake packet does not contain that approval record.
- The existing extract includes a test-automation coverage KPI requirement
  that was not found in the candidate during the initial review. Other
  normative statements also change strength or scope and need owner review.
- The candidate introduces or expands waiver, evidence, control-stage,
  responsibility, and compliance provisions. Their authority and impacts must
  be resolved before any derivation.

## Requirement-by-Requirement Comparison

The table compares the 33 IDs in the authorized tracked extract with the full
candidate text. Candidate line numbers refer to
`docs/governance/source-documents/DevSecOps_Policy_Review_Integrated_v2_CHANGE_MARKED.md`.
“Preserved” means a plausible textual counterpart was found; it does not
confirm approval, precise equivalence, or correct implementation.

| Authorized requirement | Candidate counterpart | Initial semantic assessment |
|---|---|---|
| REQ-001 — Principles and normative minimums | §§ “Fundamental Principles” and “Mandatory Minimum Requirements”, lines 198–240 | Structural counterpart. The authorized extract's heading text is malformed; confirm source meaning from the controlled requirement record. |
| REQ-002 — CDO integrates safety requirements | Responsibilities and Safety Interface, lines 67–87, 206–208 | Preserved and expanded with safety verification, evidence, and conflict handling. |
| REQ-003 — Safety Authority defines lifecycle requirements | Safety Authority, lines 79–87 | Preserved and expanded. |
| REQ-004 — Governance Board responsibilities | Governance Board, lines 89–99 | Preserved and made explicit: baselines, maturity/applicability, waivers, compliance monitoring. Confirm delegated authority against the Directive. |
| REQ-005 — Divisions/programs implement requirements | Responsibilities and Scope, lines 101–113, 168–196 | Preserved; adds platform use/equivalence and maturity duties. |
| REQ-006 — Report compliance status | Lines 111 and 319–338 | Preserved and expanded to maturity, waiver, evidence reporting, and audit support. |
| REQ-007 — Use quoted document versions | Applicable and Referenced Documents, lines 115–131 | Preserved as a general version-selection rule; the candidate's own references are incomplete (`NA`, `TBD`, “to be established”, “in progress”). |
| REQ-008 — Formally justify and approve exemptions | Scope, lines 186–196 | Changed: the candidate specifies reduced-control cases and permits pre-approved applicability rules. Confirm who can define those rules and whether they may substitute for a waiver. |
| REQ-009 — Follow binding principles | Principles, lines 198–240 | Preserved as an umbrella requirement. |
| REQ-010 — Integrate controls and enforce before deployment | Security by Design, line 204 | Partial/changed: lifecycle coverage is explicit, but “enforced prior to deployment” is not stated here; automated enforcement is required only “where appropriate”. Confirm whether release gates elsewhere fully preserve the authorized obligation. |
| REQ-011 — Safety requirements and auditable evidence | Safety Interface, lines 206–208 | Preserved and expanded with authority boundaries and conflict resolution. |
| REQ-012 — Automate controls where technically feasible | Automation First, lines 210–216 | Changed: adds economic proportionality and risk/repetition criteria and expressly supports manual execution. This can reduce mandatory automation; approve the additional qualification explicitly. |
| REQ-013 — Test coverage over all requirements measured as KPI | No equivalent KPI requirement found; test automation appears at line 253 without coverage/KPI criteria | Missing from the candidate text reviewed. Material omission requiring an owner decision. |
| REQ-014 — Lifecycle ownership | Lifecycle Ownership, lines 222–224 | Preserved and expanded from code/deployment to design, implementation, monitoring, and controlled evolution. |
| REQ-015 — Federated execution under central governance | Lines 226–228 | Preserved and expanded to engineering organizations, rules, and control baselines. |
| REQ-016 — Generate compliance evidence automatically | Evidence-Based Compliance, line 232 | Weakened: authorized `shall` becomes candidate `should`, further qualified by “where feasible”. |
| REQ-017 — Apply domain, criticality, and operational context | Domain-Aware Application, lines 234–236 | Preserved and expanded to customer and regulatory constraints. |
| REQ-018 — Normative minimum-requirement section | Heading and opening scope, lines 238–240 | Structural counterpart. |
| REQ-019 — Minimum requirements for SDD-relevant components | Scope and opening requirement, lines 168–196, 238–240 | Scope changed: the candidate covers in-scope DevSecOps implementations for SDD capabilities, external software and all security domains, and introduces exclusions/reduced-control cases. Confirm applicability boundaries. |
| REQ-020 — Objectives, controls, evidence per lifecycle phase | Control Stages, lines 242–256 | Changed: the candidate substitutes technical control stages and expressly distinguishes them from lifecycle phases and phase gates. Confirm that no lifecycle obligation is lost. |
| REQ-021 — Plan security/safety requirements and traceability | Design & Plan objective, line 250 | Preserved. |
| REQ-022 — Trace requirements, code, builds, deployed artifacts | Outcome-Based Controls, lines 268–270 | Preserved but qualified: traceability is “to the extent required” by project, product, and regulatory context. Confirm this does not narrow the current mandatory scope. |
| REQ-023 — Machine-generated evidence available and retained | Evidence, lines 276–290 | Evidence retention is preserved; machine-generated evidence is weakened from `shall` to “preferred” where technically and economically feasible. |
| REQ-024 — Manual evidence only if automation technically/regulatorily infeasible and justified | Manual execution, line 292 | Changed: adds economic disproportionality and one-off activities as grounds. Requires controlled, repeatable execution and formal justification. Confirm the broader exception. |
| REQ-025 — Achieve maturity or obtain waivers | Maturity & Applicability, lines 294–315 | Preserved with broader subject wording (“responsible organizations” rather than “programs”). |
| REQ-026 — Approval-required waivers | Board responsibilities and Governance & Responsibilities, lines 91–99, 317–328 | Preserved; approval depends on delegated authority. Confirm the role and delegation boundary. |
| REQ-027 — Waiver conditions | Deviations (Waivers), lines 340–360 | Preserved and expanded into explicit conditions. |
| REQ-028 — Risk classification and compensating controls | Line 348 | Preserved and expanded with impact assessment and accountable owner. |
| REQ-029 — Central waiver registry | Line 352 | Preserved. |
| REQ-030 — Re-evaluate before expiry | Line 354 | Preserved. |
| REQ-031 — Cybersecurity and safety approval authorities | Line 356 | Preserved in concept; “CSCSO” is replaced with “competent Cyber Security Function”. Confirm the authorized role mapping and delegated authority. |
| REQ-032 — Readiness may require compensating measures or waivers | Policy Gate definition, line 145; waiver rules, lines 342–360 | Partial/unclear: an approved waiver is recognized at a policy gate, but no direct counterpart states the readiness/compensating-measures rule. |
| REQ-033 — Mandatory use in documentation | Documentation as an Engineering Artifact, lines 218–220 | Cannot conclude from the authorized extract: its requirement ends after “All corporate documents, standards, and project artifacts shall:” and contains no extracted sub-items. Candidate wording is only “should” and conditional. The authorized record needs a complete requirement before this comparison can close. |

### Candidate-Only Requirement Areas

The candidate adds detailed scope and exclusions, seven control stages, outcome
controls for credentials/dependencies/vulnerabilities/artifact integrity,
evidence categories, a three-level maturity model, expanded waiver controls,
compliance checks, audits and escalation. These areas are not fully represented
in the 33-row authorized extract. Before any adoption, owners must decide which
are policy requirements and which belong in the Directive, DSCB, PRA, process,
or implementation guidance.

### Review Conclusion

This comparison supports the recorded decision to keep the candidate. It shows
materially weakened or missing requirements (REQ-010, REQ-012, REQ-013,
REQ-016, REQ-023 and the unresolved REQ-033), plus scope/exception changes.
It does not establish a replacement decision. The candidate remains
non-deriving until an authorized owner resolves these deltas and records a
separate decision.

The generated requirement delta is discovery support only. Its counts are not
semantic conclusions because the compared artifacts have different scope and
structure.

## Artifact Intake Classification

| Field | Value |
|---|---|
| Artifact | Human source-document intake decision record |
| Artifact type | Governance documentation |
| Target path | `docs/governance/change-requests/GCR-2026-113-devsecops-policy-v2-candidate-review-decision.md` |
| Owner | Governance owners |
| Full source-document intake required? | No source content or status is changed by this record |
| Evidence contract impact | None |
| Runtime governance impact | None; report-only intake decision |
| Release impact | None |
| Validation required | Repository validation and source-register consistency |

## Governance Behavior And Release

- [x] Documentation-only decision record
- [ ] Report-only governance behavior change
- [ ] Blocking governance behavior change
- [ ] Release packaging change

No release is required. Candidate-derived behavior remains prohibited until a
separate human decision and change request authorize it.

## Next Review Inputs

1. Policy v2 owner, provenance, version, and approval status.
2. A reliable identification of v2 changes against the authorized tracked
   requirements source; the current `CHANGE_MARKED` file has no visible change
   markings or legend.
3. Disposition of differences in automation, test-coverage measurement,
   evidence, waivers, scope, and responsibility.
4. Review by the governance, cybersecurity, safety, and DevSecOps baseline
   owners for provisions in their authority.
5. Explicit decision whether v2 replaces, supplements, or remains separate
   from the existing source.
