# Source of Truth Decision Record

## Current State

The public repository contains only source-document placeholders:

- `docs/governance/source-documents/DEVSECOPS-POL-SRC-001.public.md`
- `docs/governance/source-documents/DEVSECOPS-DIR-SRC-001.public.md`
- `docs/governance/source-documents/DSCB-STD-SRC-001.public.md`
- `docs/governance/source-documents/PRA-STD-SRC-001.public.md`
- `docs/governance/source-documents/ARCH-SDD-SRC-001.public.md`

The original source documents are withheld from the public repository. The repository contains working draft representations for:

- `docs/governance/devsecops-policy.md`
- `docs/governance/devsecops-directive.md`
- `architecture/*.yaml`
- `model/**/*.yaml`

These are not yet the formal master documents, but they allow the repository to model governance intent and execution semantics above the standards layer.

## Pilot Decision

For the pilot, the structured YAML files should become the working governance data model. Original source documents remain private comparison and review inputs.

## Target Decision

After the pilot, the organization should decide whether:

1. Private source documents remain the formal master and YAML is generated or manually synchronized.
2. YAML becomes the formal master and DOCX/PDF are generated outputs.
3. A BMS system remains the formal master and YAML is synchronized through a controlled export/import process.

## Recommendation

For DevSecOps and Software Defined Defence, option 2 is the strongest long-term model:

> Structured governance data is the master source. Documents, traceability matrices, policy rules, and evidence dashboards are generated views.

This enables stronger consistency between standards, platform capabilities, pipeline enforcement, and audit evidence.
