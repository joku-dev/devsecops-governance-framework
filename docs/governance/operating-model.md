# Operating Model

## Source-of-Truth Strategy

During the pilot, the structured YAML files in this repository should be treated as the working source for governance-as-code. The DOCX files in `docs/governance/source-documents` remain the authoritative baseline for comparison until the organization formally decides to make the structured model the master source.

The working source includes not only structured controls and platform mappings, but also the governance document catalog in `model/documents/governance-documents.yaml`. This makes the relationship between Policy, Directive, and Standards explicit and reviewable.

## Roles

| Role | Responsibility |
|---|---|
| DevSecOps Governance Owner | Owns the control model and approves changes to control semantics. |
| Platform Owner | Owns Platform Reference Architecture levels and platform capability definitions. |
| Security Specialist | Reviews security controls, evidence expectations, and policy-as-code logic. |
| Quality / Process Owner | Ensures generated documents remain compatible with BMS expectations. |
| Program Representative | Validates applicability and operational feasibility for real projects. |

## Change Flow

1. A change request proposes a new or modified control, platform capability, evidence type, or policy rule.
2. The structured YAML is updated.
3. Schema validation and policy tests are executed.
4. Traceability outputs are regenerated.
5. Generated documents are reviewed.
6. The change is approved through the defined governance workflow.

## Release Flow

Each released baseline should include:

- structured YAML source
- generated DOCX/PDF documents
- generated traceability matrix
- policy-as-code rule set
- schema validation result
- policy test result
- change log

## Pilot Success Criteria

The pilot is successful when one selected project or demo repository can demonstrate:

- required control baseline level
- required platform level
- available evidence per requirement
- automated gate results for selected policy candidates
- open gaps or approved waivers
